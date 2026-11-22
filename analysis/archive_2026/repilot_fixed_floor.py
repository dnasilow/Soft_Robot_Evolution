"""Re-pilot the corrected physics on the FIXED floor, before committing a run.

Must be run as a FILE, never piped through stdin: on Windows, spawn re-imports __main__ and piped
workers fall into a respawn loop (this bit me twice now).
"""
import os
import sys
import time
import pickle

import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT)
os.chdir(ROOT)
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SP)

SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
N = 16


def build_population():
    import src.evolution.cppn_genome as _cg
    import src.evolution.genome_config as _gc
    import run_tendon_evolution as R
    side = 10
    _cg.VOXEL_INTERIOR_MAX = _gc.VOXEL_INTERIOR_MIN + side
    _gc.VOXEL_INTERIOR_MAX = _cg.VOXEL_INTERIOR_MAX
    _cg._COORD_CACHE = None
    _cg.MAX_VOXELS_PER_ROBOT = side ** 3
    _gc.MAX_VOXELS_PER_ROBOT = side ** 3
    np.random.seed(1)
    rng = np.random.default_rng(1)
    innov = R.InnovationCounter()
    innov.flush_gen_cache()
    return [R._make_valid_cppn(innov, rng, init=lambda c: None)[1] for _ in range(N)]


def job(a):
    idx, floor, g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                          fitness_mode='forward', friction=SS, materials='cheney2013',
                          floor_contact=floor)
    e.load_robot(g)
    nb, r = e.model.nbody, e.voxel_size / 2
    x0 = np.array(e.data.xpos[1:nb])
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    ix = float(e.get_position()[0])
    deep = 0.0
    t0 = time.time()
    for _ in range(int(0.25 / e.default_timestep)):
        e.step()
        deep = max(deep, (r - float(e.data.xpos[1:nb, 2].min())) / e.voxel_size)
    return idx, floor, deep, (float(e.get_position()[0]) - ix) / bl, e.diverged(), time.time() - t0


def main():
    pop = build_population()
    champ = pickle.load(open('results/cheney_corr_s1/best_robot.pkl', 'rb'))['genome']
    bodies = list(enumerate(pop)) + [(-1, champ)]
    jobs = [(i, f, g) for i, g in bodies for f in ('mujoco', 'voxelyze')]
    t0 = time.time()
    with Pool(8) as p:
        out = p.map(job, jobs)
    res = {(i, f): r for i, f, *r in out}
    print(f"done in {time.time() - t0:.0f}s   corrected materials, 40 Hz, 10 cycles, "
          f"{N} random bodies\n")
    print(f"{'floor':<24}{'peak penetration':>20}{'':>3}{'best BL':>9}{'mean BL':>9}"
          f"{'moving':>9}{'blew up':>9}")
    print(f"{'':<24}{'median':>9}{'worst':>10}")
    for f, label in (('mujoco', 'mujoco (20 ms default)'), ('voxelyze', 'voxelyze (0.5 ms, FIXED)')):
        d = np.array([res[(i, f)][0] for i in range(N)])
        b = np.array([max(0.0, res[(i, f)][1]) for i in range(N)])
        dv = sum(res[(i, f)][2] for i in range(N))
        print(f"{label:<24}{np.median(d):>9.2f}{d.max():>10.2f}{'':>3}{b.max():>9.3f}"
              f"{b.mean():>9.3f}{int((b > 0.02).sum()):>6}/{N}{dv:>6}/{N}")
    print("\n  1.00 = a voxel centre level with the floor. Voxelyze-faithful is well under 0.25.")
    print("\n  the invalidated cheney_corr_s1 champion (scored 4.1204 on the broken floor):")
    for f in ('mujoco', 'voxelyze'):
        d, b, dv, _ = res[(-1, f)]
        print(f"    {f:<9} {b:+.4f} BL over 10 cycles, peak penetration {d:.2f} voxels")


if __name__ == '__main__':
    main()
