"""Pilot the corrected physics on the SAME 30 random robots a seed-1 run starts from, before
committing a 300-generation run.

  A  what we have run so far : evosoro materials, MuJoCo floor, 10 Hz, 1.0 s + 0.5 s settle
  B  corrected              : cheney2013 materials, Voxelyze floor, 40 Hz, 0.25 s, NO settle

10 cycles are measured either way (1.0 s at 10 Hz, 0.25 s at 40 Hz). Reports whether anything moves
at all under B, how often it blows up, and the wall-clock per evaluation -- the three things that
decide whether the run is worth launching.
"""
import os, sys, time
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
CFG = {
    'A old':       dict(materials='evosoro',    floor_contact='mujoco',   freq=10.0,
                        sim=1.0,  settle=0.5),
    'B corrected': dict(materials='cheney2013', floor_contact='voxelyze', freq=40.0,
                        sim=0.25, settle=0.0),
}


def job(a):
    k, cfg_name, g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    c = CFG[cfg_name]
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=c['freq'],
                          fitness_mode='forward', friction=SS, materials=c['materials'],
                          floor_contact=c['floor_contact'])
    e.load_robot(g)
    t0 = time.time()
    f = float(e.get_fitness(c['sim'], c['settle'], early_term_threshold=0.02,
                            early_term_fraction=0.5))
    secs = time.time() - t0
    nb = e.model.nbody
    z = np.array(e.data.xpos[1:nb, 2])
    return (k, cfg_name, f, e.diverged(), e.default_timestep, secs, int(len(e.cells)),
            float(e.g_acc), float(e.voxel_size / 2 - z.min()) / e.voxel_size)


def make_population():
    import src.evolution.cppn_genome as _cg
    import src.evolution.genome_config as _gc
    import run_tendon_evolution as R
    side = 10                                    # --grid-size 10 --no-trim, as the runs use
    _cg.VOXEL_INTERIOR_MAX = _gc.VOXEL_INTERIOR_MIN + side
    _gc.VOXEL_INTERIOR_MAX = _cg.VOXEL_INTERIOR_MAX
    _cg._COORD_CACHE = None
    _cg.MAX_VOXELS_PER_ROBOT = side ** 3
    _gc.MAX_VOXELS_PER_ROBOT = side ** 3
    np.random.seed(1)
    rng = np.random.default_rng(1)
    innov = R.InnovationCounter(); innov.flush_gen_cache()
    return [R._make_valid_cppn(innov, rng, init=lambda c: None)[1] for _ in range(30)]


if __name__ == '__main__':
    pop = make_population()
    jobs = [(k, c, g) for k, g in enumerate(pop) for c in CFG]
    t0 = time.time()
    with Pool(15) as p:
        out = p.map(job, jobs)
    res = {(k, c): r for k, c, *r in out}
    print(f"done in {time.time()-t0:.0f}s\n")
    print(f"{'robot':>6}{'vox':>6} | " + " | ".join(
        f"{c:<12}{'BL':>8}{'s':>6}{'blew':>6}" for c in CFG))
    for k in range(30):
        line = f"{k:>6}{res[(k,'A old')][4]:>6} | "
        parts = []
        for c in CFG:
            f, div, dt, secs, n, g_acc, pen = res[(k, c)]
            parts.append(f"{'':<12}{f:>8.4f}{secs:>6.0f}{('YES' if div else '-'):>6}")
        print(line + " | ".join(parts))
    print()
    for c in CFG:
        fs = np.array([res[(k, c)][0] for k in range(30)])
        dv = sum(res[(k, c)][1] for k in range(30))
        sc = np.array([res[(k, c)][3] for k in range(30)])
        dt = res[(0, c)][2]; g_acc = res[(0, c)][5]
        pen = np.array([res[(k, c)][6] for k in range(30)])
        print(f"  {c:<13} dt {dt*1e6:6.2f} us  gravity {g_acc:7.2f}  "
              f"best {fs.max():.4f}  mean {fs.mean():.4f}  moving(>0.02) {int((fs>0.02).sum())}/30  "
              f"blew up {dv}/30  total sim {sc.sum():.0f}s  floor penetration median "
              f"{100*np.median(pen):.1f}% of a voxel")
    a = np.array([res[(k, 'A old')][3] for k in range(30)]).sum()
    b = np.array([res[(k, 'B corrected')][3] for k in range(30)]).sum()
    print(f"\n  cost per generation of 30: A {a:.0f}s  ->  B {b:.0f}s  ({a/max(b,1e-9):.2f}x "
          f"{'faster' if b < a else 'slower'})")
    print(f"  => 300 generations at 30 workers: A ~{a/60*300/60:.1f} h   B ~{b/60*300/60:.1f} h "
          f"(single-robot-per-worker estimate)")
