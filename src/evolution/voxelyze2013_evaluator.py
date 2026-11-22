"""Evaluate bodies in the ORIGINAL 2013 simulator (Cheney et al., Voxel_Sim_NoGui).

The simulator is the authors' own source, built unmodified by
paper/reference_2013/build_2013_simulator.sh. On Windows it lives inside WSL; elsewhere it is
run directly. Each body is written into the 2013 settings template
(voxelyze2013_template.vxa, identical in all deposited robot files apart from the body), so
gravity, stiffness, damping, friction, actuation and the 0.25 s duration are the 2013 ones by
construction. The score and the optional cost penalty follow the 2013 code (see cheney2013.py).

Same calling interface as MuJoCoTendonEvaluator (evaluate_batch, evaluate_single, close), so the
evolution loop does not care which one it has. The simulator is deterministic, so results are
cached by body, as the 2013 code itself did.
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional

import numpy as np

from src.evolution import cheney2013 as c13

DEFAULT_BINARY = '~/softbots2013_ref/softbots/Voxel_Sim_NoGui/voxelize'
DEFAULT_DISTRO = 'Ubuntu'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voxelyze2013_template.vxa')

# Runs every *.vxa of a folder in the simulator, JOBS at a time, and prints "name,distance" per
# robot (distance = the text of <FinalCOM_Dist>, or NA when the simulator left no result).
# Sent to bash on standard input, so no quoting or line-ending issues on the way.
_BATCH_SH = r'''
set -u
BATCH="$1"; JOBS="$2"; SIM="$3"; TMO="$4"
SIM="${SIM/#\~/$HOME}"
if [ ! -x "$SIM" ]; then echo "NOSIM $SIM"; exit 3; fi
WORK=$(mktemp -d)
one() {
  f="$1"; b=$(basename "$f" .vxa); d="$WORK/$b"
  mkdir -p "$d" && cp "$f" "$d/r.vxa"
  ( cd "$d" && timeout "$TMO" "$SIM" -f r.vxa > /dev/null 2>&1 )
  v=$(grep -h -o '<FinalCOM_Dist>[^<]*' "$d/fitness.xml" 2>/dev/null | head -1 | sed 's/<FinalCOM_Dist>//')
  echo "$b,${v:-NA}"
  rm -rf "$d"
}
export -f one
export WORK SIM TMO
find "$BATCH" -maxdepth 1 -name '*.vxa' | sort | xargs -P "$JOBS" -d '\n' -I{} bash -c 'one "$1"' _ {}
rm -rf "$WORK"
'''


def _long_path(path: str) -> str:
    """Windows temp folders are often given in 8.3 short form (DNASIL~1); WSL needs the long one."""
    if os.name != 'nt':
        return path
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetLongPathNameW(path, buf, 1024)
    return buf.value if 0 < n < 1024 else path


def _for_simulator(path: str) -> str:
    """A path as the simulator's side sees it (/mnt/c/... inside WSL, unchanged elsewhere)."""
    if os.name != 'nt':
        return path
    p = _long_path(os.path.abspath(path))
    return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')


class Voxelyze2013Evaluator:
    """Fitness of voxel bodies in the original 2013 simulator.

    n_workers         simulations run at the same time
    workspace_voxels  side of the workspace; the 2013 template is 10
    penalty           'none' | 'voxels' | 'actuated' | 'connections' (the 2013 cost conditions)
    penalty_exp       exponent of the penalty (1 in the main 2013 conditions)
    binary, distro    where the simulator is (defaults: as built by build_2013_simulator.sh)

    After each evaluate_batch call, last_original holds the scores before the penalty.
    """

    def __init__(self, n_workers: int = 24, workspace_voxels: int = c13.WORKSPACE,
                 penalty: str = 'none', penalty_exp: float = 1.0,
                 binary: Optional[str] = None, distro: Optional[str] = None,
                 template: Optional[str] = None, timeout_per_robot: int = 900):
        if workspace_voxels != c13.WORKSPACE:
            raise ValueError(f"the 2013 simulator template is a {c13.WORKSPACE}-voxel workspace; "
                             f"got workspace_voxels={workspace_voxels}")
        if penalty not in c13.PENALTIES:
            raise ValueError(f"penalty must be one of {c13.PENALTIES}, got {penalty!r}")
        self.n_workers = max(1, int(n_workers))
        self.n = int(workspace_voxels)
        self.penalty = penalty
        self.penalty_exp = float(penalty_exp)
        self.binary = binary or os.environ.get('VOXELYZE2013_BIN', DEFAULT_BINARY)
        self.distro = distro or os.environ.get('VOXELYZE2013_WSL_DISTRO', DEFAULT_DISTRO)
        self.timeout_per_robot = int(timeout_per_robot)
        with open(template or TEMPLATE, encoding='iso-8859-1') as fh:
            self.template = fh.read()
        self._prefix = ['wsl', '-d', self.distro, '--'] if os.name == 'nt' else []
        self._cache = {}                  # body -> original fitness
        self.n_simulated = 0              # simulations actually run
        self.n_cached = 0                 # evaluations answered from the cache
        self.n_skipped = 0                # bodies the 2013 rule does not simulate (< 2 voxels)
        self.last_original = np.zeros(0)
        self._check_simulator()

    # ------------------------------------------------------------------
    def _run(self, batch_dir: str, jobs: int) -> dict:
        cmd = self._prefix + ['bash', '-s', '--', _for_simulator(batch_dir), str(jobs), self.binary,
                              str(self.timeout_per_robot)]
        try:
            r = subprocess.run(cmd, input=_BATCH_SH.encode('utf-8'), capture_output=True,
                               timeout=self.timeout_per_robot * 4 + 600)
        except FileNotFoundError as exc:
            raise RuntimeError(f"could not start the 2013 simulator ({cmd[0]} not found)") from exc
        out = r.stdout.decode('utf-8', 'replace')
        if r.returncode == 3 or out.startswith('NOSIM'):
            raise RuntimeError(
                f"the 2013 simulator was not found at {self.binary} "
                f"({'WSL distribution ' + self.distro if self._prefix else 'this machine'}). "
                f"Build it with paper/reference_2013/build_2013_simulator.sh.")
        if r.returncode != 0:
            raise RuntimeError(f"2013 simulator batch failed (exit {r.returncode}): "
                               f"{r.stderr.decode('utf-8', 'replace')[-400:]}")
        res = {}
        for line in out.splitlines():
            name, _, value = line.strip().partition(',')
            if name:
                res[name] = None if value in ('', 'NA') else value
        return res

    def _check_simulator(self) -> None:
        """Fail at construction, with a useful message, if the simulator is not there."""
        d = tempfile.mkdtemp(prefix='vx2013_check_')
        try:
            self._run(d, 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @classmethod
    def available(cls) -> bool:
        """True if the simulator can be started here (used by the tests to skip cleanly)."""
        try:
            cls()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    def evaluate_batch(self, genomes: List[np.ndarray], controllers: Optional[List] = None,
                       with_descriptors: bool = False, gait_params: Optional[List] = None):
        """Adjusted 2013 fitness of each body (1-D array). Controllers and gait parameters do not
        exist in the 2013 experiment: its actuation is fixed by the two muscle materials."""
        if with_descriptors:
            raise NotImplementedError("the 2013 simulator reports only the final distance; gait "
                                      "descriptors (MAP-Elites) are not available with it")
        if gait_params is not None and any(g is not None for g in gait_params):
            raise ValueError("the 2013 simulator has no evolvable gait: actuation is set by material")
        if controllers is not None and any(c is not None for c in controllers):
            raise ValueError("the 2013 simulator has no controllers: actuation is set by material")

        grids = [c13.workspace_grid(g, self.n) for g in genomes]
        original = [None] * len(grids)
        todo = {}                                           # body key -> indices waiting for it
        for i, g in enumerate(grids):
            if c13.penalty_metric(g, self.penalty) < 2:     # "less than 2 voxels filled, skipping"
                original[i] = c13.FLOOR_FITNESS
                self.n_skipped += 1
                continue
            key = '|'.join(c13.layer_rows(g))
            if key in self._cache:
                original[i] = self._cache[key]
                self.n_cached += 1
            else:
                todo.setdefault(key, []).append(i)

        if todo:
            batch = tempfile.mkdtemp(prefix='vx2013_')
            try:
                keys = list(todo)
                for k, key in enumerate(keys):
                    with open(os.path.join(batch, f'r{k:05d}.vxa'), 'w', encoding='iso-8859-1',
                              newline='\n') as fh:
                        fh.write(c13.fill_template(self.template, grids[todo[key][0]]))
                res = self._run(batch, min(self.n_workers, len(keys)))
            finally:
                shutil.rmtree(batch, ignore_errors=True)
            for k, key in enumerate(keys):
                name = f'r{k:05d}'
                if name not in res:
                    raise RuntimeError(f"the 2013 simulator returned no line for {name}")
                fit = c13.fitness_from_result(res[name], self.n)
                self._cache[key] = fit
                self.n_simulated += 1
                for i in todo[key]:
                    original[i] = fit
                self.n_cached += len(todo[key]) - 1

        self.last_original = np.array(original, dtype=float)
        return np.array([c13.penalised(o, g, self.penalty, self.penalty_exp, self.n)
                         for o, g in zip(original, grids)], dtype=float)

    def evaluate_single(self, genome: np.ndarray, controller=None) -> float:
        return float(self.evaluate_batch([genome], [controller])[0])

    def close(self) -> None:
        """Nothing to shut down: each batch is its own process."""
        return None


if __name__ == '__main__':
    ok = Voxelyze2013Evaluator.available()
    print('2013 simulator available' if ok else '2013 simulator NOT available')
    sys.exit(0 if ok else 1)
