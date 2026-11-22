"""Verification battery for the CPPN-NEAT champion (results/cheney_neat_s1)."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)


def eng(g, mode='forward'):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode=mode, friction=SS)
    e.load_robot(g)
    return e


def job(a):
    test, g = a
    if test == 'A':   return test, eng(g).get_fitness(1.0, 0.5, **ET)
    if test == 'B':   return test, eng(g).get_fitness(1.0, 2.0, **ET)
    if test == 'C':   return test, eng(g, 'directed').get_fitness(1.0, 2.0, **ET)
    if test == 'G':   return test, eng(g).get_fitness(1.0, 0.5, early_term_threshold=-1e9)
    if test == 'E':
        e = eng(g); e.default_timestep /= 4; e.model.opt.timestep = e.default_timestep
        return test, e.get_fitness(1.0, 0.5, **ET)
    e = eng(g); nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0)-x0.min(0)).max()) + e.voxel_size
    for _ in range(int(0.5/e.default_timestep)): e.step()
    z = e.data.xpos[1:nb, 2]; lo, hi = z <= np.quantile(z, .25), z >= np.quantile(z, .75)
    ix = float(e.get_position()[0]); n1 = int(1.0/e.default_timestep)
    traj, upmin, zmax = {}, 1.0, 0.0
    for s in range(1, 3*n1+1):
        e.step()
        if s % 50 == 0:
            p = e.data.xpos[1:nb]; v = p[hi].mean(0) - p[lo].mean(0)
            upmin = min(upmin, float(v[2]/(np.linalg.norm(v)+1e-12)))
            zmax = max(zmax, float(e.get_position()[2]))
        if s % n1 == 0: traj[s//n1] = (float(e.get_position()[0]) - ix)/bl
    return test, dict(traj=traj, upmin=upmin, zmax=zmax, bl=bl, div=e.diverged())


if __name__ == '__main__':
    g = pickle.load(open('results/cheney_neat_s1/best_robot.pkl', 'rb'))['genome']
    t0 = time.time()
    with Pool(6) as p:
        r = dict(p.map(job, [(k, g) for k in 'ABCEGD']))
    print(f"done in {time.time()-t0:.0f}s   CPPN-NEAT champion (recorded 2.0195)\n")
    for k, lab in (('A', 'reproduce'), ('B', 'settle 2.0 s'), ('C', 'ground penalty'),
                   ('E', 'quarter time step'), ('G', 'early termination off')):
        print(f"  {lab:<22}{float(r[k]):.4f}")
    print(f"  {'retention (B/A)':<22}{100*float(r['B'])/max(float(r['A']),1e-9):.0f}%")
    D = r['D']; tr = D['traj']
    print(f"\n  3-second run  {tr.get(1,0):.3f} / {tr.get(2,0):.3f} / {tr.get(3,0):.3f} BL"
          f"   3s/1s {tr.get(3,0)/max(tr.get(1,1e-9),1e-9):.2f}")
    print(f"  uprightness {D['upmin']:.2f}   peak COM {D['zmax']*1e3:.1f} mm on a {D['bl']*1e3:.0f} mm"
          f" body   diverged {D['div']}")
    print(f"  absolute {float(r['A'])*D['bl']:.3f} m = {float(r['A'])/10:.3f} BL/cycle"
          f"   (Cheney 0.35-0.40)")
