"""Verify beamstage2_s1's champion (2.2684 BL) WITH its evolved control net, and measure what
stage 2 added on top of each body's plain material gait.

The project's verify_corr_s1.py loads bodies without a control net, so it would score the stage-2
champion on the material gait only. Same battery, same physics, plus:
  M  the same body on its material gait alone (= what stage 2 started from, gain -> 0)
  top-10: material gait vs evolved gait for each of the 10 best archive bodies.
Run as a FILE (multiprocessing on Windows).
"""
import os, sys, glob, pickle, time
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
RUN = 'results/beamstage2_s1'
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
PHYS = dict(materials='cheney2013', floor_contact='voxelyze', actuation_frequency=40.0,
            phase_mode='offset')
CYCLES = 0.25
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)


def eng(g, net, mode='forward'):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode=mode, friction=SS, **PHYS)
    e.load_robot(g, gait_params=net)
    return e


def job(a):
    test, g, net = a
    if test.startswith('T'):                              # top-10: (material, evolved)
        return test, (float(eng(g, None).get_fitness(CYCLES, 0.0, **ET)),
                      float(eng(g, net).get_fitness(CYCLES, 0.0, **ET)))
    if test == 'A':
        return test, float(eng(g, net).get_fitness(CYCLES, 0.0, **ET))
    if test == 'M':
        return test, float(eng(g, None).get_fitness(CYCLES, 0.0, **ET))
    if test == 'B':
        return test, float(eng(g, net).get_fitness(CYCLES, 4 * CYCLES, **ET))
    if test == 'C':
        return test, float(eng(g, net, 'directed').get_fitness(CYCLES, 4 * CYCLES, **ET))
    if test == 'G':
        return test, float(eng(g, net).get_fitness(CYCLES, 0.0, early_term_threshold=-1e9))
    if test == 'E':
        e = eng(g, net)
        e.default_timestep /= 4
        e.model.opt.timestep = e.default_timestep
        return test, float(e.get_fitness(CYCLES, 0.0, **ET))
    e = eng(g, net)                                       # D: 30 cycles, physical sanity
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


def cheney_size_vs_fitness():
    """One champion per run (the gen-1000 files hold whole populations, mostly clones)."""
    SP = os.path.join(os.environ['TEMP'], 'claude', 'C--SoftRobotEvolution',
                      '5cc73d86-944b-40cc-9802-a2f3f18f9a8b', 'scratchpad')
    sys.path.insert(0, SP)
    from cheney_morphology import load_vxa
    for cond in ('2013-01-16-10^3-noCost', '2013-01-16-10^3-costNumActuated'):
        champs = []
        for run in sorted(glob.glob(os.path.join(SP, 'cheney', cond, 'run_*'))):
            best = None
            for f in glob.glob(os.path.join(run, '**', '*.vxa'), recursive=True):
                try:
                    g, fit = load_vxa(f)
                except Exception:
                    continue
                if best is None or fit > best[1]:
                    best = (int((g > 0).sum()), fit)
            if best:
                champs.append(best)
        v = np.array([c[0] for c in champs], float); f = np.array([c[1] for c in champs], float)
        rv = np.argsort(np.argsort(v)); rf = np.argsort(np.argsort(f))
        print(f"  Cheney {cond:<34} {len(champs)} run champions: voxels median {np.median(v):.0f}"
              f" (range {v.min():.0f}-{v.max():.0f}), spearman(voxels, fitness) "
              f"{np.corrcoef(rv, rf)[0, 1]:+.2f}")


def main():
    from morphology_scorecard import body_metrics
    best = pickle.load(open(f'{RUN}/best_robot.pkl', 'rb'))
    g, c = np.asarray(best['genome']), best['cppn']
    net = c.phase_cppn
    arc = pickle.load(open(f'{RUN}/archive.pkl', 'rb'))['archive']
    top = sorted(arc.values(), key=lambda e: -e['fitness'])[:10]

    jobs = [(k, g, net) for k in 'AMBCEGD']
    jobs += [(f'T{i}', np.asarray(e['genome']), e['cppn'].phase_cppn) for i, e in enumerate(top)]
    t0 = time.time()
    with Pool(len(jobs)) as p:
        r = dict(p.map(job, jobs))
    print(f"verified in {time.time() - t0:.0f}s\n")

    m = body_metrics(g)
    n = max(m['vox'], 1)
    print(f"beamstage2_s1 champion (stored {best['fitness']:.4f})  control gain "
          f"{net.phase_gain:.3f} (started 0.05)   size gene {c.size_gene:.3f}")
    print(f"  body: {m['vox']} vox, footprint {m['footprint']}, elong {m['elongation']:.2f}, "
          f"fill {m['fill']:.2f}, muscle {(m['mats'][0] + m['mats'][1]) / n:.2f}, "
          f"soft {m['mats'][2] / n:.2f}, bone {m['mats'][3] / n:.2f}   m1/m2/soft/bone "
          f"{'/'.join(map(str, m['mats']))}")
    for k, lab in (('A', 'reproduce (evolved gait)'), ('M', 'material gait only'),
                   ('B', 'settle 4 windows first'), ('C', 'ground penalty on'),
                   ('E', 'quarter time step'), ('G', 'early termination off')):
        print(f"  {lab:<28}{float(r[k]):.4f}")
    print(f"  {'retention (B/A)':<28}{100 * float(r['B']) / max(float(r['A']), 1e-9):.0f}%")
    print(f"  {'gait gain on this body':<28}{float(r['A']) / max(float(r['M']), 1e-9):.2f}x")
    D = r['D']; t = D['traj']
    print(f"\n  3 windows (30 cycles)        {t.get(1, 0):.3f} / {t.get(2, 0):.3f} / {t.get(3, 0):.3f} BL"
          f"   ratio {t.get(3, 0) / max(t.get(1, 1e-9), 1e-9):.2f} (steady = 3)")
    print(f"  uprightness (worst)          {D['upmin']:.2f}")
    print(f"  peak COM height              {D['zmax'] * 1e3:.1f} mm on a {D['bl'] * 1e3:.0f} mm body")
    print(f"  peak floor penetration       {100 * D['pen']:.0f}% of a voxel")
    print(f"  worst bond strain            {D['strain']:.2f}")
    print(f"  diverged                     {D['div']}")
    print(f"  absolute {float(r['A']) * D['bl']:.3f} m  =  {float(r['A']) / 10:.3f} BL/cycle")

    print("\nTOP 10 of the stage-2 archive: material gait -> evolved gait")
    print(f"{'rank':>5}{'stored':>9}{'material':>10}{'evolved':>9}{'x':>7}{'gain':>7}{'vox':>6}")
    ratios = []
    for i, e in enumerate(top):
        mat, evo = r[f'T{i}']
        ratios.append(evo / max(mat, 1e-9))
        print(f"{i + 1:>5}{e['fitness']:>9.4f}{mat:>10.4f}{evo:>9.4f}{ratios[-1]:>7.2f}"
              f"{e['cppn'].phase_cppn.phase_gain:>7.3f}{int((np.asarray(e['genome']) > 0).sum()):>6}")
    print(f"  median improvement over the material gait: {np.median(ratios):.2f}x")

    print("\nBODY SIZE vs SPEED in Cheney's own data")
    cheney_size_vs_fitness()


if __name__ == '__main__':
    main()
