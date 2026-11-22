"""Stability margin of the INTEGRATED beam engine (Voxelyze damping) — measurement only, no code
changes. Robots: s2 champion (no bone) and pilot first-batch robot 6 (122 bone voxels).
For each dt_frac: short run (0.1 s settle + 0.4 s), stable = finite and max|qvel| sane, and the
fitness compared with the frac-0.8 reference (a step that is 'stable' but inaccurate would drift)."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
FRACS = (0.8, 1.6, 2.4, 3.2)


def job(args):
    tag, g, frac = args
    import warnings
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS, dt_frac=frac)
    e.load_robot(g)
    t0 = time.time()
    try:
        f = float(e.get_fitness(simulation_time=0.4, settle_time=0.1))
    except Exception as ex:
        f = float('nan')
    ok = bool(np.all(np.isfinite(e.data.qvel))) and float(np.abs(e.data.qvel).max()) < 1e3
    return tag, frac, dict(fit=f, ok=ok, dt=e.default_timestep, vmax=float(np.nanmax(np.abs(e.data.qvel))),
                           secs=time.time() - t0)


if __name__ == '__main__':
    import src.evolution.cppn_genome as _cg
    import src.evolution.genome_config as _gc
    import run_tendon_evolution as R
    _cg.VOXEL_INTERIOR_MAX = _gc.VOXEL_INTERIOR_MIN + 10; _gc.VOXEL_INTERIOR_MAX = _cg.VOXEL_INTERIOR_MAX
    _cg._COORD_CACHE = None; _cg.MAX_VOXELS_PER_ROBOT = 1000; _gc.MAX_VOXELS_PER_ROBOT = 1000
    np.random.seed(1); rng = np.random.default_rng(1)
    innov = R.InnovationCounter(); innov.flush_gen_cache()
    grids = [R._make_valid_cppn(innov, rng, init=lambda c: None)[1] for _ in range(30)]
    robots = {'s2 champion (no bone)': pickle.load(open('results/cheney_repro_s2/best_robot.pkl', 'rb'))['genome'],
              'batch robot 6 (122 bone)': grids[6]}
    jobs = [(t, g, f) for t, g in robots.items() for f in FRACS]
    t0 = time.time()
    with Pool(4) as p:
        res = {(t, f): r for t, f, r in p.map(job, jobs)}
    print(f"done in {time.time()-t0:.0f}s\n")
    for t in robots:
        ref = res[(t, 0.8)]['fit']
        for f in FRACS:
            r = res[(t, f)]
            dev = (r['fit'] - ref) / ref * 100 if ref and np.isfinite(r['fit']) else float('nan')
            print(f"  {t:<26} frac {f:<4} dt {r['dt']*1e3:.4f} ms  {'STABLE  ' if r['ok'] else 'UNSTABLE'}"
                  f"  fit {r['fit']:.4f} ({dev:+.1f}% vs frac 0.8)  max|qvel| {r['vmax']:.1f}  {r['secs']:.0f}s")
