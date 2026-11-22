"""Is the pilot champion's jump from 1.6401 to 1.9145 BL under the new physics genuine, or a
transient / hop / divergence artefact? Same battery used on the pilot."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
ET = dict(early_term_threshold=0.02, early_term_fraction=0.5)


def eng(mode='forward'):
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    g = pickle.load(open('results/cheney_beam_s1/best_robot.pkl', 'rb'))['genome']
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode=mode, friction=SS)
    e.load_robot(g)
    return e


def job(test):
    if test == 'A':  r = eng().get_fitness(1.0, 0.5, **ET)
    elif test == 'B': r = eng().get_fitness(1.0, 2.0, **ET)
    elif test == 'C': r = eng('directed').get_fitness(1.0, 2.0, **ET)
    elif test == 'G': r = eng().get_fitness(1.0, 0.5, early_term_threshold=-1e9)
    elif test == 'E':
        e = eng(); e.default_timestep /= 4; e.model.opt.timestep = e.default_timestep
        r = e.get_fitness(1.0, 0.5, **ET)
    else:
        e = eng(); nb = e.model.nbody
        x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
        for _ in range(int(0.5 / e.default_timestep)): e.step()
        z = e.data.xpos[1:nb, 2]; lo, hi = z <= np.quantile(z, .25), z >= np.quantile(z, .75)
        ix = float(e.get_position()[0]); n1 = int(1.0 / e.default_timestep)
        traj, upmin, zmax = {}, 1.0, 0.0
        for s in range(1, 3 * n1 + 1):
            e.step()
            if s % 50 == 0:
                p = e.data.xpos[1:nb]; v = p[hi].mean(0) - p[lo].mean(0)
                upmin = min(upmin, float(v[2] / (np.linalg.norm(v) + 1e-12)))
                zmax = max(zmax, float(e.get_position()[2]))
            if s % n1 == 0: traj[s // n1] = (float(e.get_position()[0]) - ix) / bl
        r = dict(traj=traj, upmin=upmin, zmax=zmax, bl=bl, div=e.diverged())
    return test, r


if __name__ == '__main__':
    t0 = time.time()
    with Pool(6) as p:
        res = dict(p.map(job, list('ABCEGD')))
    print(f"done in {time.time()-t0:.0f}s   (beam pilot champion, NEW physics: poisson on, "
          f"Voxelyze step rule)\n")
    print(f"  pilot physics (recorded)      1.6401")
    print(f"  A reproduce                   {float(res['A']):.4f}")
    print(f"  B settle 2.0 s                {float(res['B']):.4f}   "
          f"retention {100*float(res['B'])/float(res['A']):.0f}%")
    print(f"  C ground penalty (directed)   {float(res['C']):.4f}")
    print(f"  E quarter time step           {float(res['E']):.4f}")
    print(f"  G early termination off       {float(res['G']):.4f}")
    D = res['D']
    print(f"\n  3-second run: {D['traj'].get(1,0):.3f} / {D['traj'].get(2,0):.3f} / "
          f"{D['traj'].get(3,0):.3f} BL   3s/1s {D['traj'].get(3,0)/max(D['traj'].get(1,1e-9),1e-9):.2f}"
          f"   min uprightness {D['upmin']:.2f}   peak COM {D['zmax']*1e3:.1f} mm"
          f"   diverged {D['div']}")
    print(f"  absolute at 10 cycles: {float(res['A'])*D['bl']:.3f} m  (body length {D['bl']*100:.1f} cm)")
