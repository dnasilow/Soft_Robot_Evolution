"""Run one evaluation with the engine from a given code root; save final state + fitness.
usage: engine_probe.py ROOT ROBOT FRICTION_JSON SIM SETTLE OUT.npz
ROBOT: 'smallest' (smallest cheney_repro_s1 archive body) or a best_robot.pkl path.
FRICTION_JSON: 'null' for the original floor (kwarg not passed, so the live code works too)."""
import sys, json, pickle, time
import numpy as np
root, robot, fr_json, sim, settle, out = sys.argv[1:7]
sys.path.insert(0, root)
import mujoco
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

if robot == 'smallest':
    arc = pickle.load(open(r'C:/SoftRobotEvolution/results/cheney_repro_s1/archive.pkl', 'rb'))['archive']
    g = min(arc.values(), key=lambda e: int((e['genome'] != 0).sum()))['genome']
else:
    g = pickle.load(open(robot, 'rb'))['genome']
fr = json.loads(fr_json)
kw = {} if fr is None else {'friction': fr}
e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward', **kw)
e.load_robot(g)
t0 = time.time()
f = float(e.get_fitness(simulation_time=float(sim), settle_time=float(settle)))
secs = time.time() - t0
m, d = e.model, e.data
ground = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, 'ground')
ng = sum(1 for i in range(d.ncon) if ground in (d.contact[i].geom1, d.contact[i].geom2))
np.savez(out, qpos=np.array(d.qpos), fit=f, ncon=d.ncon, nground=ng, secs=secs,
         nvox=int((g != 0).sum()), npair=m.npair)
print(f"{out.split('/')[-1]}: fit={f:.6f} ncon={d.ncon} ground={ng} npair={m.npair} ({secs:.1f}s)", flush=True)
