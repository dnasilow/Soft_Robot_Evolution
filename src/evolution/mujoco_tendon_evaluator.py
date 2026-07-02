"""
MuJoCo Tendon Evaluator

Bridges the EvolutionaryAlgorithm (which calls evaluate_batch(robots, controllers))
and MuJoCoTendonPhysics.

API contract
------------
evaluate_batch(genomes, controllers) -> np.ndarray of fitness values

  genomes:     list of voxel grids (each is a 3-D np.ndarray)
  controllers: list of CPGController instances (or None per entry)
               - None  → create a fresh CPGController sized for this robot
               - wrong num_actuators → replace with a fresh one silently

Parallelism
-----------
Pass n_workers > 1 to evaluate_batch to use multiprocessing.Pool.
Each worker spawns its own MuJoCoTendonPhysics instance (MuJoCo is
process-safe but not thread-safe).  The _eval_worker function must
stay at module level for pickling on Windows (spawn mode).
"""
import os
import numpy as np
from multiprocessing import Pool
from typing import List, Optional

from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
from src.physics.mujoco_tendon_converter import count_active_tendons


def _make_engine(params):
    """Construct the physics engine (flex or tendon) with the shared 3-arg signature."""
    if params.get('use_flex', False):
        from src.physics.mujoco_flex_physics import MuJoCoFlexPhysics
        cls = MuJoCoFlexPhysics
    else:
        cls = MuJoCoTendonPhysics
    return cls(
        default_timestep    = params['timestep'],
        actuation_frequency = params['actuation_frequency'],
        actuation_amplitude = params['actuation_amplitude'],
    )


# ------------------------------------------------------------------
# Module-level worker (must be top-level for Windows spawn pickling)
# ------------------------------------------------------------------
def _eval_worker(args):
    """Evaluate one robot in a worker process."""
    genome, controller, params = args
    want_desc = params.get('return_descriptors', False)
    try:
        engine = _make_engine(params)
        engine.load_robot(
            genome,
            voxel_size     = params['voxel_size'],
            initial_height = params['initial_height'],
        )
        # Flex v1 is open-loop only; skip controller attach entirely for flex.
        # When attach_controller is False (A1: Cheney-faithful open-loop), leave the
        # engine controller-free so apply_actuation() drives each active tendon with the
        # material-derived base phase at the global actuation frequency.
        if params.get('attach_controller', True) and not params.get('use_flex', False):
            controller = _reconcile_controller(controller, engine.num_active_tendons)
            if controller is not None:
                engine.set_controller(controller)
        return engine.get_fitness(
            simulation_time    = params['simulation_time'],
            settle_time        = params['settle_time'],
            return_descriptors = want_desc,
        )
    except Exception:
        return (0.0, (0.0, 0.0)) if want_desc else 0.0


class MuJoCoTendonEvaluator:
    """
    MuJoCo evaluator using the tendon-based physics engine.

    n_workers=1  → sequential (original behaviour, one reused engine)
    n_workers>1  → multiprocessing.Pool with that many worker processes;
                   each worker creates its own engine instance.
    """

    def __init__(
        self,
        simulation_time:     float = 5.0,
        settle_time:         float = 0.5,
        timestep:            float = 0.0005,
        actuation_frequency: float = 10.0,
        actuation_amplitude: float = 0.08,
        voxel_size:          float = 0.01,
        initial_height:      float = 0.0,
        n_workers:           int   = 1,
        attach_controller:   bool  = True,
        use_flex:            bool  = False,
    ):
        self.simulation_time   = simulation_time
        self.settle_time       = settle_time
        self.voxel_size        = voxel_size
        self.initial_height    = initial_height
        self.n_workers         = max(1, n_workers)
        self.attach_controller = attach_controller
        self.use_flex          = use_flex
        self._pool             = None   # persistent worker pool (created lazily)

        # Params dict passed to every worker (plain Python types → picklable)
        self._params = {
            'timestep':            timestep,
            'actuation_frequency': actuation_frequency,
            'actuation_amplitude': actuation_amplitude,
            'voxel_size':          voxel_size,
            'initial_height':      initial_height,
            'simulation_time':     simulation_time,
            'settle_time':         settle_time,
            'attach_controller':   attach_controller,
            'use_flex':            use_flex,
        }

        # Sequential engine — used when n_workers==1 and by evaluate_single
        self.engine = _make_engine(self._params)

    # ------------------------------------------------------------------
    def evaluate_batch(
        self,
        genomes:     List[np.ndarray],
        controllers: Optional[List] = None,
        with_descriptors: bool = False,
    ):
        """
        Evaluate a list of voxel-grid genomes.

        Args:
            genomes:     list of 3-D numpy arrays (voxel material IDs)
            controllers: matching list of CPGController / None.
                         Pass None for the whole list to use open-loop actuation.
            with_descriptors: if True, also return per-robot gait descriptors
                         (mean COM height, bounce) for MAP-Elites.

        Returns:
            1-D numpy array of fitness values (forward body-lengths), or
            (fitnesses, descriptors) when with_descriptors=True.
        """
        if controllers is None:
            controllers = [None] * len(genomes)

        params = dict(self._params)
        params['return_descriptors'] = with_descriptors

        # ── Parallel path (one persistent pool — see _get_pool) ────────────
        if self.n_workers > 1:
            args = [(g, c, params) for g, c in zip(genomes, controllers)]
            pool = self._get_pool()
            results = pool.map(_eval_worker, args, chunksize=1)
            if with_descriptors:
                fits  = np.array([r[0] for r in results], dtype=float)
                descs = [r[1] for r in results]
                return fits, descs
            return np.array(results, dtype=float)

        # ── Sequential path ────────────────────────────────────────────
        fitnesses, descs = [], []
        for i, (genome, controller) in enumerate(zip(genomes, controllers)):
            try:
                self.engine.load_robot(
                    genome,
                    voxel_size     = self.voxel_size,
                    initial_height = self.initial_height,
                )
                if self.attach_controller and not self.use_flex:
                    controller = _reconcile_controller(
                        controller, self.engine.num_active_tendons
                    )
                    if controller is not None:
                        self.engine.set_controller(controller)
                else:
                    self.engine.set_controller(None)
                res = self.engine.get_fitness(
                    simulation_time    = self.simulation_time,
                    settle_time        = self.settle_time,
                    return_descriptors = with_descriptors,
                )
                if with_descriptors:
                    fitnesses.append(res[0]); descs.append(res[1])
                else:
                    fitnesses.append(res)
            except Exception as exc:
                print(f"  [Evaluator] Robot {i} failed: {exc}")
                fitnesses.append(0.0); descs.append((0.0, 0.0))

        if with_descriptors:
            return np.array(fitnesses, dtype=float), descs
        return np.array(fitnesses, dtype=float)

    # ------------------------------------------------------------------
    def evaluate_single(self, genome: np.ndarray, controller=None) -> float:
        """Convenience wrapper for evaluating one robot."""
        return float(self.evaluate_batch([genome], [controller])[0])

    # ------------------------------------------------------------------
    # Persistent pool lifecycle
    # ------------------------------------------------------------------
    def _get_pool(self) -> Pool:
        """Create the worker pool on first use, then reuse it for the whole run."""
        if self._pool is None:
            self._pool = Pool(self.n_workers)
        return self._pool

    def close(self) -> None:
        """Shut the persistent worker pool down. Safe to call multiple times."""
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None

    def __del__(self):
        # Best-effort cleanup if the caller forgets to close().
        try:
            self.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------
def _reconcile_controller(controller, num_active: int):
    """
    Return a controller that matches num_active.
    - None → None if num_active==0, else fresh CPGController
    - wrong size → fresh CPGController
    """
    if num_active == 0:
        return None

    try:
        from src.evolution.controllers import CPGController
    except ImportError:
        return None

    if controller is None:
        return CPGController(num_active)

    if controller.num_actuators != num_active:
        return CPGController(num_active)

    return controller
