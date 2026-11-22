"""Validation before seeds 2-3: the volumetric (Poisson) law + Voxelyze's time-step rule, on a
realistic population. Full 10-cycle window, stick-slip Cheney floor, amp 0.2, early termination
as the run uses it.

Conditions per body:
  A  pilot physics          poisson off, dt rule 'ours'      (what cheney_beam_s1 ran)
  B  volumetric only        poisson on,  dt rule 'ours'
  C  new default            poisson on,  dt rule 'voxelyze'
  D  accuracy reference     poisson on,  voxelyze step / 2   (C is accurate if C ~ D)

Bodies: 16 from the pilot archive (real evolved bodies, spread over fitness) and 16 fresh random
CPPN bodies (what generation 1 of a new run actually sees).
"""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)
COND = {'A': (False, 'ours', 1), 'B': (True, 'ours', 1), 'C': (True, 'voxelyze', 1),
        'D': (True, 'voxelyze', 2)}


def job(args):
    tag, cond, g = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    pois, rule, div = COND[cond]
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS,
                          poisson=pois, dt_rule=rule)
    e.load_robot(g)
    if div != 1:
        e.default_timestep /= div
        e.model.opt.timestep = e.default_timestep
    t0 = time.time()
    f = float(e.get_fitness(simulation_time=1.0, settle_time=0.5, **ET))
    return tag, cond, f, e.diverged(), e.default_timestep, time.time() - t0


def make_bodies():
    import src.evolution.cppn_genome as _cg
    import src.evolution.genome_config as _gc
    import run_tendon_evolution as R
    bodies = {}
    arc = pickle.load(open('results/cheney_beam_s1/archive.pkl', 'rb'))['archive']
    ranked = sorted(arc.values(), key=lambda x: -x['fitness'])
    for k, idx in enumerate(np.linspace(0, len(ranked) - 1, 16).astype(int)):
        bodies[f'arc{k:02d}'] = ranked[idx]['genome']
    np.random.seed(7)
    rng = np.random.default_rng(7)
    innov = R.InnovationCounter(); innov.flush_gen_cache()
    for k in range(16):
        bodies[f'rnd{k:02d}'] = R._make_valid_cppn(innov, rng, init=lambda c: None)[1]
    return bodies


if __name__ == '__main__':
    bodies = make_bodies()
    jobs = [(t, c, g) for t, g in bodies.items() for c in COND]
    t0 = time.time()
    with Pool(24) as p:
        out = p.map(job, jobs)
    res = {(t, c): (f, d, dt, s) for t, c, f, d, dt, s in out}
    print(f"done in {time.time()-t0:.0f}s\n")
    print(f"{'body':>7}{'vox':>6}{'bone':>6} | {'A fit':>8}{'B fit':>8}{'C fit':>8}{'D fit':>8}"
          f" | {'C vs D':>8} | {'A s':>7}{'C s':>7}{'x':>6} | diverged")
    tot = {c: [0.0, 0.0, 0] for c in COND}
    cd = []
    for t, g in bodies.items():
        r = {c: res[(t, c)] for c in COND}
        vox = int((g != 0).sum()); bone = int((g == 4).sum())
        dev = (r['C'][0] - r['D'][0]) / r['D'][0] * 100 if abs(r['D'][0]) > 1e-6 else float('nan')
        if np.isfinite(dev) and not r['C'][1] and not r['D'][1]:
            cd.append(dev)
        flags = ''.join(c for c in COND if r[c][1])
        print(f"{t:>7}{vox:>6}{bone:>6} | " + ''.join(f"{r[c][0]:>8.4f}" for c in COND)
              + f" | {dev:>7.1f}% | {r['A'][3]:>7.1f}{r['C'][3]:>7.1f}"
              f"{r['A'][3]/max(r['C'][3],1e-9):>6.2f} | {flags or '-'}")
        for c in COND:
            tot[c][0] += r[c][0]; tot[c][1] += r[c][3]; tot[c][2] += int(r[c][1])
    n = len(bodies)
    print()
    for c in COND:
        pois, rule, div = COND[c]
        print(f"  {c}: poisson={str(pois):5s} dt={rule:9s}/{div}  mean fit {tot[c][0]/n:7.4f}  "
              f"total sim {tot[c][1]:8.1f} s  diverged {tot[c][2]}/{n}")
    print(f"\n  speed A -> C: {tot['A'][1]/tot['C'][1]:.2f}x")
    if cd:
        print(f"  Voxelyze step accuracy (C vs half step, {len(cd)} clean bodies): "
              f"mean {np.mean(cd):+.2f}%  worst {max(cd, key=abs):+.2f}%")
