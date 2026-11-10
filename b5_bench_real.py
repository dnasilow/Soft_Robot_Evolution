"""Honest tendon-model throughput on REAL evolved champions (throwaway)."""
import pickle, sys, time
import numpy as np, mujoco
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

def bench(grid, reps=2, n=400):
    phys = MuJoCoTendonPhysics()
    phys.load_robot(grid)
    m, d = phys.model, phys.data
    for _ in range(10):
        mujoco.mj_step(m, d)
    ncon, nefc = int(d.ncon), int(d.nefc)
    best = 1e18
    for _ in range(reps):
        mujoco.mj_resetData(m, d)
        t0 = time.perf_counter()
        for _ in range(n):
            mujoco.mj_step(m, d)
        best = min(best, time.perf_counter() - t0)
    sps = n / best
    return dict(vox=int((grid != 0).sum()), nv=m.nv, nu=m.nu,
                ncon=ncon, nefc=nefc, sps=sps, simps=sps * m.opt.timestep)

for name in ['gait_qd3_1000', 'gait_qd2', 'directed_v1']:
    try:
        with open(f'results/{name}/best_robot.pkl', 'rb') as f:
            g = pickle.load(f)['genome']
        r = bench(g)
        print(f"{name:18s} vox={r['vox']:3d} nv={r['nv']:4d} nu={r['nu']:3d} "
              f"ncon={r['ncon']:4d} nefc={r['nefc']:5d} "
              f"steps/s={r['sps']:8,.0f} sim-s/wall-s={r['simps']:.3f}", flush=True)
    except Exception as e:
        print(name, 'ERR', repr(e)[:140], flush=True)
