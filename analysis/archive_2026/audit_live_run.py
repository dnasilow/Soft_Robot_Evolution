"""Audit the LIVE cheney_vox_s1 archive while it runs: do the elites reproduce, are any of them
actually diverged bodies that slipped past the guard, and are their strains/velocities physical?
Low worker count so it does not steal cores from the run."""
import os, sys, time, pickle, shutil
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)
SNAP = os.path.join(os.environ['TEMP'], 'vox_s1_snapshot.pkl')


def job(args):
    """Reproduce with the RUN's own scoring path (get_fitness), then a second pass that only
    watches the physics. body_length is taken from the undeformed layout, as get_fitness does."""
    tag, g = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
    e.load_robot(g)
    fit = float(e.get_fitness(simulation_time=1.0, settle_time=0.5, **ET))
    div1 = e.diverged()

    e2 = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
    e2.load_robot(g)
    i, j = e2.bi, e2.bj
    nb = e2.model.nbody
    worst_strain, vmax, zmax = 0.0, 0.0, 0.0
    for k in range(int(1.5 / e2.default_timestep)):
        e2.step()
        if k % 20 == 0:
            d = np.linalg.norm(e2.data.xpos[1:nb][j] - e2.data.xpos[1:nb][i], axis=1) / e2.voxel_size
            worst_strain = max(worst_strain, float(np.abs(d - 1).max()))
            vmax = max(vmax, float(np.abs(e2.data.qvel).max()))
            zmax = max(zmax, float(e2.get_position()[2]))
    return tag, fit, div1 or e2.diverged(), worst_strain, vmax, zmax


if __name__ == '__main__':
    for attempt in range(5):                       # the run rewrites the checkpoint each generation
        try:
            shutil.copy('results/cheney_vox_s1/checkpoint.pkl', SNAP)
            ck = pickle.load(open(SNAP, 'rb'))
            break
        except Exception as ex:
            print('retry:', ex); time.sleep(5)
    arc = ck['archive']
    print(f"checkpoint: iteration {ck.get('iteration', '?')}, {len(arc)} cells filled")
    fits = np.array([e['fitness'] for e in arc.values()])
    print(f"archive fitness: max {fits.max():.4f}  top-10 mean {np.sort(fits)[-10:].mean():.4f}  "
          f"zeros {(fits == 0).sum()}")
    top = sorted(arc.values(), key=lambda e: -e['fitness'])[:10]
    jobs = [(f'#{k+1}', e['genome']) for k, e in enumerate(top)]
    t0 = time.time()
    with Pool(3) as p:
        out = p.map(job, jobs)
    print(f"\nre-evaluated in {time.time()-t0:.0f}s   (settle 0.5 s, then 10 cycles)")
    print(f"{'rank':>5}{'archive':>10}{'re-run':>10}{'diff':>9}{'vox':>6}{'bone':>6}"
          f"{'worst strain':>14}{'peak|qvel|':>12}{'peak COM':>10}{'diverged':>10}")
    for (tag, fit, div, ws, vm, zm), e in zip(out, top):
        g = e['genome']
        print(f"{tag:>5}{e['fitness']:>10.4f}{fit:>10.4f}{fit-e['fitness']:>9.4f}"
              f"{int((g != 0).sum()):>6}{int((g == 4).sum()):>6}{ws:>14.3f}{vm:>12.1f}"
              f"{zm*1e3:>9.1f}m{str(div):>10}")
    print("\n  worst strain = largest |bond length / rest - 1| seen; a sane body stays well under 1.")
