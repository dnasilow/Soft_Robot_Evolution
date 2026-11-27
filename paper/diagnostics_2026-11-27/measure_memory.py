"""What the memory statement of 27 November 2026 rests on, measured.

1. The most of MuJoCo's working memory a body can use. A beam body's only MuJoCo constraints
   are its floor pairs: one contact per voxel at most, four rows each. So the worst case is
   every voxel in contact with the floor at once, and it is built here for bodies of 1 to 1000
   voxels on each floor of the engine.
2. What MuJoCo does when the stated memory is too small: nothing is assumed, three cases are
   tried and what happens is written down.
3. What a process asks the system for (its private bytes, which is what Windows counts against
   what it can promise): the measurement of 25 November (../diagnostics_2026-11-25/
   check_memory.py: three champions under both presets, with the libraries' default threads and
   with one), repeated with the code in this folder.

usage, from the project folder:
    python paper/diagnostics_2026-11-27/measure_memory.py
Written next to this file: memory_after.json.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'diagnostics_2026-11-25'))

import transfer_scores as ts                                  # noqa: E402  (sets one thread before numpy is loaded)
import analyse_arm as aa                                      # noqa: E402
import check_memory as before                                 # noqa: E402
import mujoco                                                 # noqa: E402
import numpy as np                                            # noqa: E402
import src.physics.mujoco_beam_physics as beam                # noqa: E402
from src.evolution import mujoco_tendon_evaluator as evaluation   # noqa: E402

SHAPES = ((1, 1, 1), (10, 1, 1), (10, 10, 1), (5, 5, 5), (10, 10, 5), (10, 10, 10))
PRESETS = ('cheney2013', 'cheney2013-floor')


def mixed(shape):
    """Every material in one body."""
    grid = np.zeros((10, 10, 10), np.int8)
    for i in range(shape[0]):
        for j in range(shape[1]):
            for k in range(shape[2]):
                grid[i, j, k] = (1, 2, 3, 4)[(i + 2 * j + 3 * k) % 4]
    return grid


def loaded(preset, grid):
    params = ts.worker_parameters(ts.evaluator_arguments(preset=preset))
    engine = evaluation._make_engine(params)
    engine.load_robot(grid, voxel_size=params['voxel_size'], initial_height=0.0, gait_params=None)
    return engine


def press_every_voxel_on_the_floor(engine):
    """Each voxel's sphere into the floor, each layer a little deeper than the one below it so
    that no two voxels sit in the same place, and every voxel moving."""
    model, data, size = engine.model, engine.data, engine.voxel_size
    for k, cell in enumerate(engine.cells):
        data.qpos[model.jnt_qposadr[k] + 2] = size / 2 - (0.05 + 0.03 * cell[2]) * size
    data.qvel[:] = np.random.default_rng(0).normal(0.0, 0.5, model.nv)
    mujoco.mj_forward(model, data)


def worst_case():
    rows = []
    for preset in PRESETS:
        for shape in SHAPES:
            with_estimate = None
            real = beam.arena_bytes
            beam.arena_bytes = lambda n: -1                    # MuJoCo's own estimate, for the comparison
            try:
                with_estimate = int(loaded(preset, mixed(shape)).model.narena)
            finally:
                beam.arena_bytes = real
            engine = loaded(preset, mixed(shape))
            n = len(engine.cells)
            press_every_voxel_on_the_floor(engine)
            contacts, constraint_rows = int(engine.data.ncon), int(engine.data.nefc)
            for _ in range(3):
                engine.step()
            used = int(engine.data.maxuse_arena)
            rows.append({'preset': preset, 'voxels': n, 'contacts': contacts, 'rows': constraint_rows,
                         'used_bytes': used, 'used_per_voxel': round(used / n), 'stated_bytes': int(engine.model.narena),
                         'stated_over_used': round(engine.model.narena / used, 1),
                         'mujoco_estimate_bytes': with_estimate, 'blew_up': bool(engine.diverged())})
            print(f"  {preset:17} {n:5d} voxels  {contacts:5d} contacts  used {used / 2 ** 20:7.3f} MB "
                  f"({used / n:6.0f} bytes per voxel)  stated {engine.model.narena / 2 ** 20:6.1f} MB "
                  f"({engine.model.narena / used:6.1f} times)  MuJoCo's estimate {with_estimate / 2 ** 20:7.0f} MB", flush=True)
    return rows


def too_small():
    """Three cases of too little memory, through the search's own worker function."""
    params = ts.worker_parameters(ts.evaluator_arguments(preset='cheney2013'))
    rows = []
    for stated, shape in ((1024, (1, 1, 1)), (1024, (10, 10, 2)), (300 * 1024, (10, 10, 2))):
        real = beam.arena_bytes
        beam.arena_bytes = lambda n, stated=stated: stated
        row = {'stated_bytes': stated, 'voxels': int(np.prod(shape))}
        try:                                                   # what MuJoCo and the engine do
            engine = evaluation._make_engine(params)
            engine.load_robot(mixed(shape), voxel_size=params['voxel_size'], initial_height=0.0, gait_params=None)
            for _ in range(200):
                engine.step()
            row['engine'] = 'no error'
        except Exception as exc:                               # noqa: BLE001
            row['engine'] = f'{type(exc).__name__}: {str(exc).splitlines()[0][:150]}'
        try:                                                   # and what the search makes of it
            row['search'] = repr(evaluation._eval_worker((mixed(shape), None, None, params)))
        except Exception as exc:                               # noqa: BLE001
            row['search'] = type(exc).__name__
        finally:
            beam.arena_bytes = real
        rows.append(row)
        print(f"  {stated:7d} bytes stated for {row['voxels']:4d} voxels: {row['engine']}  ->  the search: {row['search']}",
              flush=True)
    return rows


def main():
    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'code': aa.code_version(), 'mujoco': mujoco.__version__,
              'logical_processors': os.cpu_count(), 'free_before_gb': round(ts.free_commit_gb(), 1),
              'stated': {'fixed_bytes': beam.ARENA_BYTES_FIXED, 'per_voxel_bytes': beam.ARENA_BYTES_PER_VOXEL}}
    print('1. Every voxel on the floor:')
    report['every_voxel_on_the_floor'] = worst_case()
    print('2. Too little memory stated:')
    report['too_small'] = too_small()
    print('3. What a process asks the system for, three champions under both presets:')
    report['default_threads'] = now = before.run_child(False)
    report['one_thread'] = one = before.run_child(True)
    with open(os.path.join(HERE, '..', 'diagnostics_2026-11-25', 'memory_check.json'), encoding='utf-8') as f:
        earlier = json.load(f)
    same = [a['score'] == b['score'] == c['score'] == d['score']
            for a, b, c, d in zip(now['rows'], one['rows'], earlier['as_now']['rows'], earlier['one_thread']['rows'])]
    report['same_score_as_on_25_november'] = [int(sum(same)), len(same)]
    print(f"  {'preset':17} {'body':32} {'voxels':>6} {'stated':>8} {'used':>8}   process: 25 Nov  default threads  one thread")
    for old, a, b in zip(earlier['as_now']['rows'], now['rows'], one['rows']):
        print(f"  {a['preset']:17} {a['body']:32} {a['voxels']:6d} {a['reserved_mb']:5.1f} MB {a['used_mb']:5.2f} MB   "
              f"{old['process_loaded_gb']:12.2f} GB {a['process_loaded_gb']:12.2f} GB {b['process_loaded_gb']:8.2f} GB")
    print(f"  The score of 25 November to the last digit, with either number of threads: {sum(same)} of {len(same)}.")
    with open(os.path.join(HERE, 'memory_after.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)


if __name__ == '__main__':
    main()
