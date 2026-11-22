"""Verify cheney_score_s1's champion (2.7170 W on Cheney's score) with the usual battery, on the
run's own physics and score: --direction any --divide-by workspace (10 voxels), 10 cycles at 40 Hz.
Also: the old score (+X / own length), a 60-cycle path, morphology, and when the peak arrived.
"""
import os, sys, json, pickle, time
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
RUN = 'results/cheney_score_s1'
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
CHENEY = dict(direction='any', divide_by='workspace', workspace_voxels=10)
CYC = 0.25
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)


def eng(g, score=CHENEY):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze', **score)
    e.load_robot(g)
    return e


def job(a):
    test, g = a
    if test == 'A':
        return test, float(eng(g).get_fitness(CYC, 0.0, **ET))
    if test == 'F':                                   # the old score: +X / own body length
        return test, float(eng(g, {}).get_fitness(CYC, 0.0, **ET))
    if test == 'B':
        return test, float(eng(g).get_fitness(CYC, 4 * CYC, **ET))
    if test == 'G':
        return test, float(eng(g).get_fitness(CYC, 0.0, early_term_threshold=-1e9))
    if test == 'E':
        e = eng(g)
        e.default_timestep /= 4
        e.model.opt.timestep = e.default_timestep
        return test, float(e.get_fitness(CYC, 0.0, **ET))
    # D: 60 cycles - path, posture, floor, bonds
    e = eng(g)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb])
    z = x0[:, 2]
    lo, hi = z <= np.quantile(z, 0.25), z >= np.quantile(z, 0.75)
    r = e.voxel_size / 2
    W = 10 * e.voxel_size
    c0 = np.array(e.get_position())
    n1 = int(0.025 / e.default_timestep)
    path, upmin, pen, strain = [np.zeros(3)], 1.0, 0.0, 0.0
    i, j = e.bi, e.bj
    for cyc in range(60):
        for s in range(n1):
            e.step()
            if s % 25 == 0:
                p = e.data.xpos[1:nb]
                v = p[hi].mean(0) - p[lo].mean(0)
                upmin = min(upmin, float(v[2] / (np.linalg.norm(v) + 1e-12)))
                pen = max(pen, (r - float(p[:, 2].min())) / e.voxel_size)
                d = np.linalg.norm(p[j] - p[i], axis=1) / e.voxel_size
                strain = max(strain, float(np.abs(d - 1).max()))
        path.append((np.array(e.get_position()) - c0) / W)
    return test, dict(path=np.array(path), upmin=upmin, pen=pen, strain=strain, div=e.diverged())


def main():
    from morphology_scorecard import body_metrics
    best = pickle.load(open(f'{RUN}/best_robot.pkl', 'rb'))
    g = np.asarray(best['genome'])
    t0 = time.time()
    with Pool(6) as p:
        r = dict(p.map(job, [(k, g) for k in 'AFBEGD']))
    print(f"verified in {time.time() - t0:.0f}s\n")

    print(f"cheney_score_s1 champion (stored {best['fitness']:.4f} W)")
    for k, lab in (('A', 'reproduce'), ('E', 'quarter time step'), ('G', 'early termination off'),
                   ('B', 'walk 40 cycles first, then score'), ('F', 'OLD score (+X / own length)')):
        print(f"  {lab:<34}{float(r[k]):.4f}{' BL' if k == 'F' else ' W'}")
    print(f"  {'retention (B/A)':<34}{100 * float(r['B']) / max(float(r['A']), 1e-9):.0f}%")

    D = r['D']; P = D['path']
    print("\n  60 cycles, net displacement per 10-cycle window (W) and heading")
    for w in range(6):
        d = P[10 * (w + 1)] - P[10 * w]
        print(f"    cycles {10*w+1:>2}-{10*w+10:<3} {np.linalg.norm(d):.3f} W   heading "
              f"{np.degrees(np.arctan2(d[1], d[0])):+5.0f} deg")
    print(f"  net after 60 cycles      {np.linalg.norm(P[60]):.3f} W   (plateau record 15.99 W)")
    print(f"  uprightness (worst)      {D['upmin']:.2f}")
    print(f"  peak floor penetration   {100 * D['pen']:.0f}% of a voxel")
    print(f"  worst bond strain        {D['strain']:.2f}")
    print(f"  diverged                 {D['div']}")

    m = body_metrics(g)
    n = max(m['vox'], 1)
    idx = np.argwhere(g > 0)
    ext = sorted(int(e) for e in idx.max(0) - idx.min(0) + 1)
    print(f"\n  body: {m['vox']} vox, bbox {ext}, fill {m['fill']:.2f}, footprint {m['footprint']}, "
          f"feet {m['feet']}, elong {m['elongation']:.2f}, muscle {(m['mats'][0] + m['mats'][1]) / n:.2f}, "
          f"soft {m['mats'][2] / n:.2f}, bone {m['mats'][3] / n:.2f}   m1/m2/soft/bone "
          f"{'/'.join(map(str, m['mats']))}")

    h = json.load(open(f'{RUN}/history.json'))
    bf = np.array(h['best_fitness'])
    first = int(np.argmax(bf >= bf.max() - 1e-12)) + 1
    print(f"\n  best by generation: " + "  ".join(f"{gg}:{bf[gg - 1]:.4f}" for gg in (1, 25, 50, 100, 150, 200, 250, 300)))
    print(f"  peak first reached at generation {first}, flat for {300 - first} generations")

    pop = pickle.load(open(f'{RUN}/final_population.pkl', 'rb'))
    f = np.array(pop['fitnesses'], float)
    print(f"  final population: top-10 mean {np.sort(f)[-10:].mean():.4f} W, median {np.median(f):.4f}, "
          f"zeros {(f == 0).sum()}/{len(f)}")
    rows = []
    for k in np.argsort(-f)[:10]:
        mm = body_metrics(np.asarray(pop['genomes'][k]))
        rows.append((f[k], mm['vox'], mm['footprint'], mm['elongation'],
                     (mm['mats'][0] + mm['mats'][1]) / max(mm['vox'], 1)))
    print(f"  top-10 bodies: vox {[r_[1] for r_ in rows]}")
    print(f"                 footprint {[r_[2] for r_ in rows]}  muscle {[round(r_[4], 2) for r_ in rows]}")

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.plot(P[:, 0], P[:, 1], '-', color='#d62728', lw=2, label='cheney_score_s1 champion')
    ax.plot(P[10, 0], P[10, 1], 'o', color='#d62728', ms=7, label='end of the 10 scored cycles')
    ax.plot(P[-1, 0], P[-1, 1], 's', color='#d62728', ms=6, label='cycle 60')
    ax.plot(0, 0, 'k+', ms=10)
    ax.set_xlabel('x (workspace widths)'); ax.set_ylabel('y (workspace widths)')
    ax.set_title('Top-down path over 60 cycles')
    ax.axis('equal'); ax.grid(alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(f'{RUN}/path_60cycles.png', dpi=110)
    print(f"\nsaved {RUN}/path_60cycles.png")


if __name__ == '__main__':
    main()
