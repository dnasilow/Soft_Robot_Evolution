"""Measure champions on Cheney 2013's protocol: COM displacement at the end of 10 actuation cycles.

Two variants (10 Hz -> 10 cycles = 1.0 s):
  after-settle : 0.5 s settle, then 10 cycles     (our convention, minus the extra 15 cycles)
  from-init    : no settle, 10 cycles from t=0    (Cheney-literal: 'between initialization and ...')
Each reports directed +X BL (our metric) and horizontal Euclidean BL (undirected, closer to theirs).
"""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)


def job(args):
    tag, variant, genome = args
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward')
    e.load_robot(genome)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb], copy=True)
    bl = max(float((x0.max(0) - x0.min(0)).max()) + e.voxel_size, e.voxel_size)
    if variant == 'after-settle':
        for _ in range(int(0.5 / e.default_timestep)):
            e.step()
    p0 = np.array(e.get_position(), copy=True)
    for _ in range(int(1.0 / e.default_timestep)):      # 10 cycles at 10 Hz
        e.step()
    d = np.array(e.get_position()) - p0
    return tag, variant, dict(fwd=d[0] / bl, horiz=float(np.hypot(d[0], d[1])) / bl)


if __name__ == '__main__':
    robots = []
    a2 = pickle.load(open('results/cheney_repro_s2/archive.pkl', 'rb'))['archive']
    for i, en in enumerate(sorted(a2.values(), key=lambda en: -en['fitness'])[:3]):
        robots.append((f's2#{i+1}', en['fitness'], en['genome']))
    b1 = pickle.load(open('results/cheney_repro_s1/best_robot.pkl', 'rb'))
    robots.append(('s1#1', b1['fitness'], b1['genome']))
    jobs = [(t, v, g) for t, _, g in robots for v in ('after-settle', 'from-init')]
    t0 = time.time()
    with Pool(len(jobs)) as p:
        res = {(t, v): r for t, v, r in p.imap_unordered(job, jobs)}
    print(f'done in {time.time()-t0:.0f}s\n')
    print(f"{'robot':<6}{'@25cyc':>8} | {'10cyc settle: fwd':>18}{'horiz':>7} | {'10cyc from-init: fwd':>21}{'horiz':>7} | {'BL/cycle':>9}")
    for t, arch, g in robots:
        a, b = res[(t, 'after-settle')], res[(t, 'from-init')]
        print(f"{t:<6}{arch:>8.4f} | {a['fwd']:>18.4f}{a['horiz']:>7.3f} | {b['fwd']:>21.4f}{b['horiz']:>7.3f} | {arch/25:>9.4f}")
    print("\nCheney 2013 (Fig. 8/9, generative encoding): median run-champion 3.5-4.0 BL at 10 cycles = 0.35-0.40 BL/cycle")
