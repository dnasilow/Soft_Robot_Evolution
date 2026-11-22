"""Per-step cost and the resulting wall-clock per 10-cycle evaluation, for the three physics
settings. Measures the step itself (no early termination, no fitness bookkeeping)."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
COND = {'A pilot': (False, 'ours'), 'B volumetric': (True, 'ours'), 'C new default': (True, 'voxelyze')}
BODIES = {'beam_s1 champion (420 vox, 15 bone)': 'results/cheney_beam_s1/best_robot.pkl'}


def job(args):
    tag, cond, g = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    pois, rule = COND[cond]
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS,
                          poisson=pois, dt_rule=rule)
    e.load_robot(g)
    for _ in range(50):                       # warm up
        e.step()
    t0 = time.time()
    n = 400
    for _ in range(n):
        e.step()
    ms = (time.time() - t0) / n * 1e3
    steps = int(1.5 / e.default_timestep)
    return tag, cond, e.default_timestep, ms, steps, ms * steps / 1e3


if __name__ == '__main__':
    arc = pickle.load(open('results/cheney_beam_s1/archive.pkl', 'rb'))['archive']
    ranked = sorted(arc.values(), key=lambda x: -x['fitness'])
    bodies = {'champion 420 vox / 15 bone': ranked[0]['genome'],
              'no bone 630 vox': next(e['genome'] for e in ranked if (e['genome'] == 4).sum() == 0),
              'bone-heavy 850 vox / 301': max(ranked, key=lambda e: (e['genome'] == 4).sum())['genome']}
    jobs = [(t, c, g) for t, g in bodies.items() for c in COND]
    with Pool(3) as p:                        # 3 at a time: timing must not fight for cores
        out = p.map(job, jobs)
    res = {(t, c): r for t, c, *r in out}
    print(f"{'body':>28}{'setting':>16}{'dt (us)':>10}{'ms/step':>10}{'steps/eval':>12}"
          f"{'s/eval':>9}{'vs A':>7}")
    for t in bodies:
        base = res[(t, 'A pilot')][3]
        for c in COND:
            dt, ms, steps, sec = res[(t, c)]
            print(f"{t:>28}{c:>16}{dt*1e6:>10.2f}{ms:>10.3f}{steps:>12d}{sec:>9.1f}"
                  f"{base/sec:>7.2f}")
