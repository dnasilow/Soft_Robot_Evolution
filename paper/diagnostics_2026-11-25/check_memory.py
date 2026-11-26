"""Exploratory: what a worker process asks the system for, and what an evaluation uses of it.

On 25 November fourteen workers next to arm A used up what the system could promise (README,
"A lesson about memory"). This measures where a worker's memory goes. One process is
started twice, once as the runs start now and once with one linear-algebra thread
(OPENBLAS_NUM_THREADS=1 and its two relatives). Each reports what it has asked the system for
after every import (its private bytes, which is what Windows counts against its limit), then
scores three champions under both presets through the search's own evaluation and reports, for
each, what MuJoCo reserved for the body (its "arena"), the most of it the evaluation used, and
the score.

The three bodies are chosen by size, not by eye: the largest and the median champion of arm R
and the median champion of arm Rc, by number of voxels.

Nothing is changed by this: no setting of the engine, the search or the machine.

usage (Windows):
    python paper/diagnostics_2026-11-25/check_memory.py
        written next to this file: memory_check.json
"""
import ctypes
import gc
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

THREAD_SETTINGS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')
PRESETS = ('cheney2013', 'cheney2013-floor')
BODIES = (('R', ('largest', 'median')), ('Rc', ('median',)))


class _Counters(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
                ('PrivateUsage', ctypes.c_size_t)]


def asked_for_gb():
    """What this process has asked the system to promise it: its private bytes."""
    kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Counters), wintypes.DWORD]
    counters = _Counters()
    counters.cb = ctypes.sizeof(_Counters)
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return counters.PrivateUsage / 2 ** 30


def child():
    """One process: its memory after each import, then the three bodies under both presets."""
    report = {'threads': {v: os.environ.get(v) for v in THREAD_SETTINGS}, 'imports': [], 'rows': []}

    def note(what):
        report['imports'].append([what, round(asked_for_gb(), 3)])

    note('the interpreter')
    import numpy as np
    note('numpy ' + np.__version__)
    import scipy
    import scipy.linalg                                         # noqa: F401  (what loads its library)
    import scipy.sparse                                         # noqa: F401
    note('scipy ' + scipy.__version__)
    import mujoco
    note('mujoco ' + mujoco.__version__)
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
    import transfer_scores as ts
    from src.evolution import mujoco_tendon_evaluator as evaluation
    note("the search's evaluation")

    bodies = []
    for arm, picks in BODIES:
        by_size = sorted(ts.arm_champions(arm), key=lambda c: int((np.asarray(c['grid']) != 0).sum()))
        for pick in picks:
            c = by_size[-1] if pick == 'largest' else by_size[len(by_size) // 2]
            bodies.append((f"arm {arm}, {c['label']} ({pick} body)", np.asarray(c['grid'])))

    for preset in PRESETS:
        params = ts.worker_parameters(ts.evaluator_arguments(preset=preset))
        for name, grid in bodies:
            before = asked_for_gb()
            engine = evaluation._make_engine(params)
            engine.load_robot(grid, voxel_size=params['voxel_size'],
                              initial_height=evaluation._start_height(grid, params), gait_params=None)
            row = {'preset': preset, 'body': name, 'voxels': int((grid != 0).sum()), 'nv': int(engine.model.nv),
                   'reserved_mb': round(engine.model.narena / 2 ** 20, 1),
                   'process_before_gb': round(before, 3), 'process_loaded_gb': round(asked_for_gb(), 3)}
            began = time.time()
            score = engine.get_fitness(simulation_time=params['simulation_time'], settle_time=params['settle_time'],
                                       return_descriptors=False, **evaluation._fitness_kw(params))
            row.update(score=float(score), blew_up=bool(engine.diverged()), seconds=round(time.time() - began, 1),
                       used_mb=round(engine.data.maxuse_arena / 2 ** 20, 3),
                       most_contacts=int(engine.data.maxuse_con), most_constraints=int(engine.data.maxuse_efc),
                       warnings=int(sum(int(w.number) for w in engine.data.warning)))
            del engine
            gc.collect()
            report['rows'].append(row)
    print(json.dumps(report))


def run_child(one_thread):
    env = {k: v for k, v in os.environ.items() if k not in THREAD_SETTINGS}
    if one_thread:
        env.update({v: '1' for v in THREAD_SETTINGS})
    done = subprocess.run([sys.executable, os.path.abspath(__file__), '--child'], env=env, cwd=ROOT,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f'The measuring process failed:\n{done.stderr[-2000:]}')
    return json.loads([line for line in done.stdout.splitlines() if line.strip()][-1])


def main():
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
    import analyse_arm as aa
    import transfer_scores as ts
    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'code': aa.code_version(),
              'logical_processors': os.cpu_count(), 'free_before_gb': round(ts.free_commit_gb(), 1)}
    print('as the runs start now ...', flush=True)
    report['as_now'] = now = run_child(False)
    print('with one linear-algebra thread ...', flush=True)
    report['one_thread'] = one = run_child(True)
    same = sum(a['score'] == b['score'] for a, b in zip(now['rows'], one['rows']))
    report['same_score'] = [same, len(now['rows'])]
    with open(os.path.join(HERE, 'memory_check.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)

    print(f"\nA process, in GB asked of the system, on {report['logical_processors']} logical processors:")
    print(f"  {'after loading':28} {'as now':>8} {'one thread':>11}")
    for (what, a), (_, b) in zip(now['imports'], one['imports']):
        print(f'  {what:28} {a:8.2f} {b:11.2f}')
    print('\nOne evaluation of a champion:')
    print(f"  {'preset':17} {'body':32} {'voxels':>6} {'reserved':>9} {'used':>8} {'process':>8} {'one thr.':>8} "
          f"{'s':>6} {'s':>6}  score")
    for a, b in zip(now['rows'], one['rows']):
        print(f"  {a['preset']:17} {a['body']:32} {a['voxels']:6d} {a['reserved_mb']:6.0f} MB {a['used_mb']:5.2f} MB "
              f"{a['process_loaded_gb']:5.2f} GB {b['process_loaded_gb']:5.2f} GB {a['seconds']:6.1f} {b['seconds']:6.1f}  "
              f"{a['score']:.4f}{'' if a['score'] == b['score'] else '  DIFFERS: ' + repr(b['score'])}")
    print(f'\nThe same score to the last digit with one thread: {same} of {len(now["rows"])}.')
    print(f"Warnings from MuJoCo: {sum(r['warnings'] for r in now['rows'] + one['rows'])}.")


if __name__ == '__main__':
    if '--child' in sys.argv[1:]:
        child()
    else:
        main()
