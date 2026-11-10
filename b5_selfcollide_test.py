"""Does intra-robot self-collision dominate tendon-model cost? (throwaway)"""
import pickle, time
import numpy as np, mujoco
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

def steps_per_sec(m, d, reps=2, n=400):
    for _ in range(10):
        mujoco.mj_step(m, d)
    ncon = int(d.ncon)
    best = 1e18
    for _ in range(reps):
        mujoco.mj_resetData(m, d)
        t0 = time.perf_counter()
        for _ in range(n):
            mujoco.mj_step(m, d)
        best = min(best, time.perf_counter() - t0)
    return n / best, ncon

with open('results/gait_qd2/best_robot.pkl', 'rb') as f:
    g = pickle.load(f)['genome']

# baseline
phys = MuJoCoTendonPhysics(); phys.load_robot(g)
m, d = phys.model, phys.data
sps0, ncon0 = steps_per_sec(m, d)
print(f"BASELINE (self-collision ON) : ncon={ncon0:5d}  steps/s={sps0:8,.0f}", flush=True)

# disable voxel-voxel collision: voxel geoms -> contype=2, conaffinity=1
# voxel-voxel: (2&1)|(2&1)=0 -> off ; voxel-floor(1,1): (2&1)|(1&1)=1 -> on
phys2 = MuJoCoTendonPhysics(); phys2.load_robot(g)
m2, d2 = phys2.model, phys2.data
for i in range(m2.ngeom):
    if m2.geom(i).name.startswith('geom_'):
        m2.geom_contype[i] = 2
        m2.geom_conaffinity[i] = 1
sps1, ncon1 = steps_per_sec(m2, d2)
print(f"NO self-collision (floor only): ncon={ncon1:5d}  steps/s={sps1:8,.0f}", flush=True)
print(f"-> self-collision removal speedup: {sps1/sps0:.1f}x  "
      f"(contacts {ncon0} -> {ncon1})", flush=True)
