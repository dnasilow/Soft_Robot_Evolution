"""Initial simulation tests for the beam pilot: regenerate the EXACT first batch the pilot will
evaluate (seed 1, grid 10, no trim) and evaluate every robot under the full pilot configuration,
one process per robot, catching exceptions individually (the evaluator itself maps a crash to 0,
which would hide it)."""
import os, sys, time, traceback
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def evaluate(args):
    k, g = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    try:
        t0 = time.time()
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
        e.load_robot(g)
        f, desc = e.get_fitness(simulation_time=1.0, settle_time=0.5, return_descriptors=True,
                                early_term_threshold=0.02, early_term_fraction=0.5)
        return dict(k=k, ok=True, fit=float(f), desc=desc, dt=e.default_timestep, secs=time.time() - t0,
                    vox=len(e.cells), bone=int((g == 4).sum()), muscle=int(np.isin(g, (1, 2)).sum()),
                    finite=bool(np.all(np.isfinite(e.data.qpos))), vmax=float(np.abs(e.data.qvel).max()),
                    t_end=e.current_time)
    except Exception:
        return dict(k=k, ok=False, err=traceback.format_exc()[-600:])


if __name__ == '__main__':
    import src.evolution.cppn_genome as _cg
    import src.evolution.genome_config as _gc
    import run_tendon_evolution as R
    side = 10                                       # --grid-size 10 --no-trim, as the CLI sets them
    _cg.VOXEL_INTERIOR_MAX = _gc.VOXEL_INTERIOR_MIN + side; _gc.VOXEL_INTERIOR_MAX = _cg.VOXEL_INTERIOR_MAX
    _cg._COORD_CACHE = None
    _cg.MAX_VOXELS_PER_ROBOT = side ** 3; _gc.MAX_VOXELS_PER_ROBOT = side ** 3
    np.random.seed(1); rng = np.random.default_rng(1)           # run_map_elites(seed=1)
    innov = R.InnovationCounter(); innov.flush_gen_cache()
    grids = [R._make_valid_cppn(innov, rng, init=lambda c: None)[1] for _ in range(30)]
    t0 = time.time()
    with Pool(30) as p:
        res = sorted(p.map(evaluate, list(enumerate(grids))), key=lambda r: r['k'])
    wall = time.time() - t0
    bad = [r for r in res if not r['ok']]
    good = [r for r in res if r['ok']]
    print(f"30 robots (the pilot's first batch) evaluated in {wall:.0f}s wall on 30 processes")
    print(f"  crashes: {len(bad)}   non-finite states: {sum(not r['finite'] for r in good)}   "
          f"max |qvel| {max(r['vmax'] for r in good):.1f}")
    for r in bad:
        print(f"  CRASH robot {r['k']}:\n{r['err']}")
    fit = np.array([r['fit'] for r in good]); secs = np.array([r['secs'] for r in good])
    dts = np.array([r['dt'] for r in good]) * 1e3; vox = np.array([r['vox'] for r in good])
    bone = np.array([r['bone'] for r in good]) > 0
    stopped = np.array([r['t_end'] < 1.49 for r in good])
    print(f"  voxels: min {vox.min()} median {int(np.median(vox))} max {vox.max()}")
    print(f"  fitness (BL, 10 cycles): max {fit.max():.4f}  median {np.median(fit):.4f}  "
          f"zeros {(fit == 0).sum()}  stopped early (under 0.02 BL at 5 cycles): {stopped.sum()}")
    print(f"  time step: {dts.min():.4f}-{dts.max():.4f} ms   eval time: median {np.median(secs):.1f}s max {secs.max():.1f}s")
    print(f"  with bone: {bone.sum()} robots  eval median {np.median(secs[bone]) if bone.any() else float('nan'):.1f}s "
          f"(dt {np.median(dts[bone]) if bone.any() else float('nan'):.4f} ms)  | without: {np.median(secs[~bone]):.1f}s "
          f"(dt {np.median(dts[~bone]):.4f} ms)")
    print(f"  descriptors (COM height, bounce) ranges: h {min(r['desc'][0] for r in good):.3f}-{max(r['desc'][0] for r in good):.3f}  "
          f"b {min(r['desc'][1] for r in good):.3f}-{max(r['desc'][1] for r in good):.3f}")
    print("\n  k   vox  mus bone  dt(ms)   secs   fit")
    for r in good:
        print(f"  {r['k']:>2}  {r['vox']:>4} {r['muscle']:>4} {r['bone']:>4}  {r['dt']*1e3:.4f}  {r['secs']:>5.1f}  {r['fit']:.4f}")
