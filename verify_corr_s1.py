"""Verify cheney_corr_s1's 4.12 BL champion, and describe the morphology it found.

4.12 BL is double the previous record, and in this project every big jump has needed checking first
(two turned out to be artefacts). This runs the same battery used on every earlier champion, under
the run's own physics: corrected materials, Voxelyze floor, 40 Hz, 10 cycles, no settle.

    python verify_corr_s1.py
"""
import os
import pickle
import sys
import time

import numpy as np
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

RUN = os.environ.get('RUN', 'results/cheney_corr_s1')
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
PHYS = dict(materials='cheney2013', floor_contact=os.environ.get('FLOOR','voxelyze'),
            actuation_frequency=40.0)
CYCLES = 0.25                      # 10 cycles at 40 Hz
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)


def eng(g, mode='forward'):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode=mode, friction=SS, **PHYS)
    e.load_robot(g)
    return e


def job(a):
    test, g = a
    if test == 'A':                                    # reproduce exactly as the run scored it
        return test, float(eng(g).get_fitness(CYCLES, 0.0, **ET))
    if test == 'B':                                    # was it a start-up transient?
        return test, float(eng(g).get_fitness(CYCLES, 4 * CYCLES, **ET))
    if test == 'C':                                    # does it stay on the ground?
        return test, float(eng(g, 'directed').get_fitness(CYCLES, 4 * CYCLES, **ET))
    if test == 'G':                                    # early termination irrelevant?
        return test, float(eng(g).get_fitness(CYCLES, 0.0, early_term_threshold=-1e9))
    if test == 'E':                                    # numerically converged?
        e = eng(g)
        e.default_timestep /= 4
        e.model.opt.timestep = e.default_timestep
        return test, float(e.get_fitness(CYCLES, 0.0, **ET))
    # D: long run - steady gait? upright? grounded? physically sane?
    e = eng(g)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb])
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    r = e.voxel_size / 2
    z = e.data.xpos[1:nb, 2]
    lo, hi = z <= np.quantile(z, 0.25), z >= np.quantile(z, 0.75)
    ix = float(e.get_position()[0])
    n1 = int(CYCLES / e.default_timestep)
    traj, upmin, zmax, pen, strain = {}, 1.0, 0.0, 0.0, 0.0
    i, j = e.bi, e.bj
    for s in range(1, 3 * n1 + 1):
        e.step()
        if s % 25 == 0:
            p = e.data.xpos[1:nb]
            v = p[hi].mean(0) - p[lo].mean(0)
            upmin = min(upmin, float(v[2] / (np.linalg.norm(v) + 1e-12)))
            zmax = max(zmax, float(e.get_position()[2]))
            pen = max(pen, (r - float(p[:, 2].min())) / e.voxel_size)
            d = np.linalg.norm(p[j] - p[i], axis=1) / e.voxel_size
            strain = max(strain, float(np.abs(d - 1).max()))
        if s % n1 == 0:
            traj[s // n1] = (float(e.get_position()[0]) - ix) / bl
    return test, dict(traj=traj, upmin=upmin, zmax=zmax, bl=bl, pen=pen, strain=strain,
                      div=e.diverged())


def main():
    from morphology_scorecard import body_metrics
    g = pickle.load(open(f'{RUN}/best_robot.pkl', 'rb'))['genome']
    pop = pickle.load(open(f'{RUN}/final_population.pkl', 'rb'))
    fits = np.array(pop['fitnesses'], float)

    t0 = time.time()
    with Pool(6) as p:
        r = dict(p.map(job, [(k, g) for k in 'ABCEGD']))
    print(f"verified in {time.time() - t0:.0f}s\n")

    print("cheney_corr_s1 champion  (''' + RUN + ''', 10 cycles at 40 Hz)")
    for k, lab in (('A', 'reproduce'), ('B', 'settle 4 windows first'), ('C', 'ground penalty on'),
                   ('E', 'quarter time step'), ('G', 'early termination off')):
        print(f"  {lab:<26}{float(r[k]):.4f}")
    print(f"  {'retention (B/A)':<26}{100 * float(r['B']) / max(float(r['A']), 1e-9):.0f}%")

    D = r['D']
    t = D['traj']
    print(f"\n  3 windows (30 cycles)      {t.get(1, 0):.3f} / {t.get(2, 0):.3f} / {t.get(3, 0):.3f} BL"
          f"   steady would be 1:2:3, ratio {t.get(3, 0) / max(t.get(1, 1e-9), 1e-9):.2f}")
    print(f"  uprightness (worst)        {D['upmin']:.2f}")
    print(f"  peak COM height            {D['zmax'] * 1e3:.1f} mm on a {D['bl'] * 1e3:.0f} mm body")
    print(f"  peak floor penetration     {100 * D['pen']:.0f}% of a voxel")
    print(f"  worst bond strain          {D['strain']:.2f}   (volumetric law turns unstable ~0.8)")
    print(f"  diverged                   {D['div']}")
    print(f"\n  absolute {float(r['A']) * D['bl']:.3f} m  =  {float(r['A']) / 10:.3f} BL/cycle")
    print("  Cheney's 35 run champions: median 4.39, mean 4.61, range 3.39-5.95 (his metric)")

    print(f"\nfinal population: best {fits.max():.4f}  top-10 mean {np.sort(fits)[-10:].mean():.4f}"
          f"  zeros {(fits == 0).sum()}/{len(fits)}")
    print(f"{'rank':>5}{'fit':>9}{'vox':>6}{'feet':>6}{'footpr':>8}{'fill':>7}{'elong':>7}"
          f"{'muscle':>8}   m1/m2/soft/bone")
    rows = []
    for i in np.argsort(-fits):
        gg = np.asarray(pop['genomes'][i])
        if (gg != 0).sum() == 0:
            continue
        m = body_metrics(gg)
        m['fit'] = float(fits[i])
        m['muscle'] = (m['mats'][0] + m['mats'][1]) / max(m['vox'], 1)
        rows.append(m)
    for k, m in enumerate(rows[:6], 1):
        print(f"{k:>5}{m['fit']:>9.4f}{m['vox']:>6}{m['feet']:>6}{m['footprint']:>8}{m['fill']:>7.2f}"
              f"{m['elongation']:>7.2f}{m['muscle']:>8.2f}   {'/'.join(map(str, m['mats']))}")
    a = lambda key: np.array([m[key] for m in rows], float)
    print(f"\n  champion                        vox {rows[0]['vox']:>4}  footprint "
          f"{rows[0]['footprint']:>3}  elong {rows[0]['elongation']:.2f}"
          f"  muscle {rows[0]['muscle']:.2f}  feet {rows[0]['feet']}")
    print(f"  whole population (median)       vox {np.median(a('vox')):>4.0f}  footprint "
          f"{np.median(a('footprint')):>3.0f}  elong {np.median(a('elongation')):.2f}"
          f"  muscle {np.median(a('muscle')):.2f}  feet>=2 {100 * np.mean(a('feet') >= 2):.0f}%")
    print("  cheney_neat_s1 champ (old phys)  vox  290  footprint  71  elong 1.67  muscle 1.00")
    print("  CHENEY's 35 champions            vox  652  footprint  26  elong 1.00  muscle 1.00")

    for rank, i in enumerate(np.argsort(-fits)[:3], 1):
        pickle.dump({'genome': np.asarray(pop['genomes'][i]), 'fitness': float(fits[i]),
                     'cppn': pop['cppns'][i]}, open(f'{RUN}/top{rank}.pkl', 'wb'))
    print(f"\nwrote {RUN}/top1.pkl .. top3.pkl")


if __name__ == '__main__':
    main()
