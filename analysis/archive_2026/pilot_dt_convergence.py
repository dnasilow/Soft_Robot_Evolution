"""Is the beam pilot's result independent of the time step? Same robots at the auto step (frac 0.8)
and at half of it (frac 0.4). Robots from the pilot's first batch: the fastest-spinning one, the
best one, a bone-heavy one, a no-bone one. Also reports which voxel spins fastest and how many bonds
it has (a lone, weakly held voxel flapping is physical; a lattice-wide blow-up is not)."""
import os, sys, time
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def job(args):
    k, g, frac = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS, dt_frac=frac)
    e.load_robot(g)
    vmax, where = 0.0, None
    orig = e.step
    def tracked():
        nonlocal vmax, where
        orig()
        w = np.abs(e.data.cvel[1:, :3]).max(1)
        i = int(w.argmax())
        if w[i] > vmax:
            vmax, where = float(w[i]), i
    e.step = tracked
    t0 = time.time()
    f = float(e.get_fitness(simulation_time=1.0, settle_time=0.5))   # no early stop: full window
    nb = np.bincount(np.concatenate([e.bi, e.bj]), minlength=len(e.cells))
    return k, frac, dict(fit=f, dt=e.default_timestep, secs=time.time() - t0, spin=vmax,
                         spin_bonds=int(nb[where]) if where is not None else -1,
                         spin_mat=int(e.mats[where]) if where is not None else -1)


if __name__ == '__main__':
    import src.evolution.cppn_genome as _cg
    import src.evolution.genome_config as _gc
    import run_tendon_evolution as R
    _cg.VOXEL_INTERIOR_MAX = _gc.VOXEL_INTERIOR_MIN + 10; _gc.VOXEL_INTERIOR_MAX = _cg.VOXEL_INTERIOR_MAX
    _cg._COORD_CACHE = None; _cg.MAX_VOXELS_PER_ROBOT = 1000; _gc.MAX_VOXELS_PER_ROBOT = 1000
    np.random.seed(1); rng = np.random.default_rng(1)
    innov = R.InnovationCounter(); innov.flush_gen_cache()
    grids = [R._make_valid_cppn(innov, rng, init=lambda c: None)[1] for _ in range(30)]
    picks = {14: 'best of batch', 6: 'bone 122 / muscle 249', 13: 'bone-heavy (435)', 26: 'no bone'}
    jobs = [(k, grids[k], f) for k in picks for f in (0.8, 0.4)]
    t0 = time.time()
    with Pool(len(jobs)) as p:
        res = {(k, f): r for k, f, r in p.map(job, jobs)}
    print(f"done in {time.time()-t0:.0f}s   (full 10-cycle window, no early stop)\n")
    print(f"{'robot':<28}{'fit @dt':>9}{'fit @dt/2':>11}{'ratio':>7}{'dt ms':>9}{'max spin':>10}  spinning voxel")
    for k, lab in picks.items():
        a, b = res[(k, 0.8)], res[(k, 0.4)]
        ratio = b['fit'] / a['fit'] if abs(a['fit']) > 1e-9 else float('nan')
        print(f"{k:>2} {lab:<25}{a['fit']:>9.4f}{b['fit']:>11.4f}{ratio:>7.3f}{a['dt']*1e3:>9.4f}"
              f"{a['spin']:>8.1f}/s  mat {a['spin_mat']}, {a['spin_bonds']} bond(s)   (dt/2: {b['spin']:.1f}/s)")
