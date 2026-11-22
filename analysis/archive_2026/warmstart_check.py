"""Stage 2's warm start attaches a RANDOM control CPPN to every seeded body. With phase_mode
'offset' that is material gait + a random offset of up to +-pi - and a large offset scored 0.0000 on
the beam champion. If the stage-1 bodies collapse to ~0 under a random control net, stage 2 starts
from a population of zeros and offset mode buys nothing.

Measures, for the 10 fastest stage-1 bodies: material gait vs 5 random control nets, plus a
damped variant (offset scaled by 0.05) to show what a near-zero initialisation would give.
"""
import os
import sys
import pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT)
os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
SCALES = (0.0, 0.05, 1.0)          # 0 = material gait; 1 = what the warm start does today


class Scaled:
    def __init__(self, net, s):
        self.net, self.s = net, s

    def evaluate_batch(self, c):
        return self.s * np.asarray(self.net.evaluate_batch(c), float)


def job(a):
    key, g, seed, scale = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    from src.evolution.cppn_genome import CPPNGenome, _phase_innov
    net = CPPNGenome(_phase_innov(), np.random.default_rng(seed))
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                          fitness_mode='forward', friction=SS, materials='cheney2013',
                          floor_contact='voxelyze', phase_mode='offset')
    e.load_robot(g, gait_params=Scaled(net, scale))
    return key, seed, scale, float(e.get_fitness(0.25, 0.0, early_term_threshold=0.02,
                                                 early_term_fraction=0.5))


def main():
    arc = pickle.load(open('results/beamstage1_s1/archive.pkl', 'rb'))['archive']
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    # the 10 fastest by real speed (fast1..3 were written by analyse_stage1; rank the rest here)
    speeds = []
    for k, e in arc.items():
        speeds.append((k, e))
    tops = [pickle.load(open(f'results/beamstage1_s1/fast{i}.pkl', 'rb'))['genome']
            for i in (1, 2, 3)]
    bodies = [(f'fast{i+1}', g) for i, g in enumerate(tops)]
    jobs = [(k, g, s, sc) for k, g in bodies for s in range(5) for sc in SCALES
            if not (sc == 0.0 and s > 0)]
    with Pool(24) as p:
        out = p.map(job, jobs)
    res = {}
    for k, s, sc, f in out:
        res.setdefault((k, sc), []).append(f)
    print("stage-1 bodies under the control net stage 2's warm start would give them\n")
    print(f"{'body':<7}{'material gait':>15}{'random net x0.05':>18}{'random net (as now)':>21}")
    for k, _ in bodies:
        m = res[(k, 0.0)][0]
        d = res[(k, 0.05)]
        r = res[(k, 1.0)]
        print(f"{k:<7}{m:>15.4f}{np.mean(d):>12.4f} ({min(d):.2f}-{max(d):.2f})"
              f"{np.mean(r):>11.4f} ({min(r):.2f}-{max(r):.2f})")
    print("\n  5 random control nets per body. 'as now' = an unscaled fresh CPPN, which is what")
    print("  init_phase_cppn gives every seeded body today.")


if __name__ == '__main__':
    main()
