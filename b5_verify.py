"""Verify: (1) tendon model still locomotes with self-collision off + how many
floor contacts remain during a real gait; (2) flex internal contact count. (throwaway)"""
import pickle, time
import numpy as np, mujoco
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
import b5_flex_spike as fx

with open('results/gait_qd2/best_robot.pkl', 'rb') as f:
    g = pickle.load(f)['genome']

# ---- tendon champion WITH self-collision off: fitness + floor-contact load ----
phys = MuJoCoTendonPhysics(); phys.load_robot(g)
m, d = phys.model, phys.data
for i in range(m.ngeom):
    if m.geom(i).name.startswith('geom_'):
        m.geom_contype[i] = 2; m.geom_conaffinity[i] = 1
# step through a real gait, track contacts (floor only now)
mujoco.mj_resetData(m, d)
maxcon = 0
t0 = time.perf_counter()
for s in range(5000):                       # 2.5 s at dt=0.0005
    phys.apply_actuation(); mujoco.mj_step(m, d)
    maxcon = max(maxcon, int(d.ncon))
wall = time.perf_counter() - t0
fit = phys.get_fitness(simulation_time=2.5)
print(f"tendon (self-collide OFF): 2.5s gait ran in {wall:.2f}s wall "
      f"({5000/wall:,.0f} steps/s), max floor-contacts during gait={maxcon}, "
      f"fitness={fit:.3f} (saved was 0.640)", flush=True)

# ---- flex robot internal contact count (should be ~floor only) ----
fm, seg, sl, nseg, ax, nm = fx.build_flex_robot(count=(11,7,6), pos=(0,0,0.2))
fd = mujoco.MjData(fm)
for a in range(fm.nu): fd.ctrl[a] = sl
for _ in range(50): mujoco.mj_step(fm, fd)
print(f"flex robot (300 cells): nflexedge={fm.nflexedge}, ncon during sim={int(fd.ncon)} "
      f"(flex handles internal connectivity natively -> no contact blowup)", flush=True)
