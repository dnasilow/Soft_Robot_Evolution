"""Can the beam engine use Voxelyze's own time-step rule (evosoro: 0.7 x recommendedTimeStep, i.e.
0.7 / (2*pi*sqrt(max_link axial stiffness / min voxel mass)))? Measurement only — the running pilot is
untouched. Full 10-cycle window, early termination OFF, per robot: our current dt (reference), the
Voxelyze rule, and 1.5x the Voxelyze rule. Accurate = fitness within a few % of the reference."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def voxelyze_dt(e):
    m = e._m
    return 0.7 / (2 * np.pi * np.sqrt(e.K_ax.max() / m))       # evosoro DtFrac 0.7


def job(args):
    tag, g, rule = args
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
    e.load_robot(g)
    ours = e.default_timestep
    dt = {'ours': ours, 'voxelyze': min(voxelyze_dt(e), 0.0005), 'voxelyze x1.5': min(1.5 * voxelyze_dt(e), 0.0005)}[rule]
    e.default_timestep = dt; e.model.opt.timestep = dt
    vmax = 0.0
    orig = e.step
    def tracked():
        nonlocal vmax
        orig(); vmax = max(vmax, float(np.abs(e.data.qvel).max()))
    e.step = tracked
    t0 = time.time()
    f = float(e.get_fitness(simulation_time=1.0, settle_time=0.5, early_term_threshold=-1e9))
    return tag, rule, dict(fit=f, dt=dt, ours=ours, ok=bool(np.all(np.isfinite(e.data.qvel))) and vmax < 1e3,
                           vmax=vmax, secs=time.time() - t0)


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
              'batch 14 (best, 39 bone)': grids[14], 'batch 6 (122 bone)': grids[6],
              'batch 18 (212 bone)': grids[18], 'batch 3 (431 bone)': grids[3]}
    rules = ('ours', 'voxelyze', 'voxelyze x1.5')
    jobs = [(t, g, r) for t, g in robots.items() for r in rules]
    t0 = time.time()
    with Pool(8) as p:
        res = {(t, r): x for t, r, x in p.map(job, jobs)}
    print(f"done in {time.time()-t0:.0f}s  (full 10 cycles, no early stop)\n")
    print(f"  {'robot':<26}{'rule':<15}{'dt (ms)':>9}{'fitness':>10}{'vs ours':>9}{'max|qvel|':>11}{'stable':>8}{'secs':>6}")
    for t in robots:
        ref = res[(t, 'ours')]['fit']
        for r in rules:
            x = res[(t, r)]
            dev = (x['fit'] - ref) / abs(ref) * 100 if abs(ref) > 1e-6 and np.isfinite(x['fit']) else float('nan')
            print(f"  {t:<26}{r:<15}{x['dt']*1e3:>9.4f}{x['fit']:>10.4f}{dev:>8.1f}%{x['vmax']:>11.1f}"
                  f"{('yes' if x['ok'] else 'NO'):>8}{x['secs']:>6.0f}")
