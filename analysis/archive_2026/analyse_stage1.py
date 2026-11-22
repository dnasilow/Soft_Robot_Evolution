"""Stage 1 on beam bodies: did morphology diversify, and how fast are the bodies really?

The archive's fitness includes the muscle tax (x (1 - muscle fraction)), so it says nothing about
speed. This re-scores every archived body in plain 'forward' mode on the run's own physics, and
compares the morphology against the plateaued champion and Cheney's robots.
Run as a FILE (multiprocessing on Windows).
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


def job(a):
    key, g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                          fitness_mode='forward', friction=SS, materials='cheney2013',
                          floor_contact='voxelyze')
    e.load_robot(g)
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb])
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    f = float(e.get_fitness(0.25, 0.0, early_term_threshold=0.02, early_term_fraction=0.5))
    return key, f, f * bl, e.diverged()


def main():
    from morphology_scorecard import body_metrics
    arc = pickle.load(open('results/beamstage1_s1/archive.pkl', 'rb'))['archive']
    items = list(arc.items())
    with Pool(30) as p:
        out = p.map(job, [(k, e['genome']) for k, e in items])
    fwd = {k: (f, m, dv) for k, f, m, dv in out}

    rows = []
    for k, e in items:
        g = np.asarray(e['genome'])
        m = body_metrics(g)
        n = max(m['vox'], 1)
        mats = m['mats']
        rows.append(dict(key=k, tax=e['fitness'], fwd=fwd[k][0], metres=fwd[k][1],
                         div=fwd[k][2], vox=m['vox'], foot=m['footprint'], feet=m['feet'],
                         elong=m['elongation'], fill=m['fill'],
                         muscle=(mats[0] + mats[1]) / n, soft=mats[2] / n, bone=mats[3] / n,
                         nmat=sum(1 for x in (mats[0] + mats[1], mats[2], mats[3]) if x > 0)))
    a = lambda k: np.array([r[k] for r in rows], float)

    print(f"beamstage1_s1 archive: {len(rows)} bodies, all re-scored WITHOUT the muscle tax\n")
    print("MORPHOLOGY (whole archive)")
    print(f"  muscle fraction  median {np.median(a('muscle')):.2f}   in 0.1-0.7 band "
          f"{100*np.mean((a('muscle') >= 0.1) & (a('muscle') <= 0.7)):.0f}%   100% muscle "
          f"{100*np.mean(a('muscle') > 0.999):.0f}%")
    print(f"  bodies using all three materials  {int((a('nmat') == 3).sum())}/{len(rows)}")
    print(f"  voxels  median {np.median(a('vox')):.0f}  range {a('vox').min():.0f}-{a('vox').max():.0f}")
    print(f"  fill    median {np.median(a('fill')):.2f}  min {a('fill').min():.2f}")
    print(f"  elongation median {np.median(a('elong')):.2f}  max {a('elong').max():.2f}")
    print(f"  footprint median {np.median(a('foot')):.0f}  min {a('foot').min():.0f}   "
          f">=2 feet {100*np.mean(a('feet') >= 2):.0f}%")
    print(f"  diverged when re-scored: {int(a('div').sum())}")

    rows.sort(key=lambda r: -r['fwd'])
    print("\nFASTEST BODIES BY REAL SPEED (forward BL, 10 cycles, no tax)")
    print(f"{'rank':>5}{'fwd BL':>9}{'metres':>8}{'taxed':>8}{'vox':>6}{'foot':>6}{'elong':>7}"
          f"{'fill':>6}{'musc':>6}{'soft':>6}{'bone':>6}")
    for i, r in enumerate(rows[:10], 1):
        print(f"{i:>5}{r['fwd']:>9.4f}{r['metres']:>8.3f}{r['tax']:>8.4f}{r['vox']:>6}{r['foot']:>6}"
              f"{r['elong']:>7.2f}{r['fill']:>6.2f}{r['muscle']:>6.2f}{r['soft']:>6.2f}{r['bone']:>6.2f}")
    print("\nREFERENCE")
    print("  cheney_fix_s1 champion (plateau): fwd 2.6118 BL, 0.261 m, 370 vox, foot 70, elong 1.43, "
          "muscle 1.00")
    print("  Cheney's 35 champions:            652 vox, foot 26, elong 1.00, muscle 1.00")

    best = rows[0]
    keys = [r['key'] for r in rows[:3]]
    for rank, k in enumerate(keys, 1):
        pickle.dump({'genome': np.asarray(arc[k]['genome']), 'fitness': fwd[k][0],
                     'cppn': arc[k]['cppn']},
                    open(f'results/beamstage1_s1/fast{rank}.pkl', 'wb'))
    print(f"\nwrote results/beamstage1_s1/fast1..3.pkl (fastest by real speed)")


if __name__ == '__main__':
    main()
