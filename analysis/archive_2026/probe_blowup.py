"""Where does the volumetric law diverge? Track the worst bond strain, the worst 'add' (the sum
of a voxel's constrained-axis strains, which drives the bulge) and the worst bulge, per step."""
import os, sys, pickle
import numpy as np
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics, POISSON

g = pickle.load(open('results/cheney_floor_s1/best_robot.pkl', 'rb'))['genome']
e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', poisson=True, dt_rule='ours')
e.load_robot(g)

log = []
orig = e.axial_bond_force


def traced(ext, rest):
    eps = ext / rest
    ps = e.poisson_strain(eps)
    add = np.where(e._tension, np.nan, np.nan)  # placeholder, recomputed below
    S = np.zeros((len(e.cells), 3))
    np.add.at(S, (e.bj, e.ba), e._f_pos * eps)
    np.add.at(S, (e.bi, e.ba), e._f_neg * eps)
    S *= e._half
    add = np.where(e._tension, S, 0.0).sum(1)
    free = ~e._tension.all(1)
    log.append((e.current_time, float(np.abs(eps).max()), float(add[free].min() if free.any() else 0),
                float(ps.max()), float(ps.min())))
    return orig(ext, rest)


e.axial_bond_force = traced
for k in range(int(0.12 / e.default_timestep)):
    e.step()

print(f"{'t (ms)':>8}{'max|eps|':>11}{'min 1+add':>12}{'max ps':>10}{'min ps':>10}")
for t, mx, mn, pmax, pmin in log[::25]:
    print(f"{t*1e3:8.1f}{mx:11.4f}{1+mn:12.4f}{pmax:10.3f}{pmin:10.3f}")
print("\nfirst step where max|eps| > 1:",
      next((f"t={t*1e3:.2f} ms" for t, mx, *_ in log if mx > 1), "never"))
