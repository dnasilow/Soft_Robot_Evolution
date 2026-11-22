"""Head to head under IDENTICAL settings: the pilot's champion (evolved without the volumetric
law) versus the new run's champion (evolved with it), both scored on the final physics."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)
BODIES = {'pilot champion (cheney_beam_s1)': 'results/cheney_beam_s1/best_robot.pkl',
          'new champion  (cheney_vox_s1)': 'results/cheney_vox_s1/best_robot.pkl'}


def job(a):
    name, settle = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open(BODIES[name], 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
    e.load_robot(g)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb])
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    f = float(e.get_fitness(1.0, settle, **ET))
    return name, settle, f, bl, int((g != 0).sum())


if __name__ == '__main__':
    jobs = [(n, s) for n in BODIES for s in (0.5, 2.0)]
    with Pool(4) as p:
        out = {(n, s): (f, bl, v) for n, s, f, bl, v in p.map(job, jobs)}
    print(f"{'body':<34}{'vox':>5}{'settle 0.5':>12}{'settle 2.0':>12}{'retention':>11}"
          f"{'metres':>9}{'BL/cycle':>10}")
    for n in BODIES:
        a, bl, v = out[(n, 0.5)]
        b, _, _ = out[(n, 2.0)]
        print(f"{n:<34}{v:>5}{a:>12.4f}{b:>12.4f}{100*b/max(a,1e-9):>10.0f}%"
              f"{a*bl:>9.3f}{a/10:>10.3f}")
    print("\n  Cheney 2013: 3.5-4.0 BL in 10 cycles = 0.35-0.40 BL/cycle")
