"""Verification battery for cheney_vox_s1's top 3 — the same checks used on the pilot, so the
1.7592 can be compared like for like."""
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
    tag, test, g = a
    if test == 'A':   r = eng(g).get_fitness(1.0, 0.5, **ET)
    elif test == 'B': r = eng(g).get_fitness(1.0, 2.0, **ET)
    elif test == 'C': r = eng(g, 'directed').get_fitness(1.0, 2.0, **ET)
    elif test == 'G': r = eng(g).get_fitness(1.0, 0.5, early_term_threshold=-1e9)
    elif test == 'E':
        e = eng(g); e.default_timestep /= 4; e.model.opt.timestep = e.default_timestep
        r = e.get_fitness(1.0, 0.5, **ET)
    else:
        e = eng(g); nb = e.model.nbody
        x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
        for _ in range(int(0.5 / e.default_timestep)): e.step()
        z = e.data.xpos[1:nb, 2]; lo, hi = z <= np.quantile(z, .25), z >= np.quantile(z, .75)
        ix = float(e.get_position()[0]); n1 = int(1.0 / e.default_timestep)
        traj, upmin, zmax, rest = {}, 1.0, 0.0, float(e.get_position()[2])
        for s in range(1, 3 * n1 + 1):
            e.step()
            if s % 50 == 0:
                p = e.data.xpos[1:nb]; v = p[hi].mean(0) - p[lo].mean(0)
                upmin = min(upmin, float(v[2] / (np.linalg.norm(v) + 1e-12)))
                zmax = max(zmax, float(e.get_position()[2]))
            if s % n1 == 0: traj[s // n1] = (float(e.get_position()[0]) - ix) / bl
        r = dict(traj=traj, upmin=upmin, zmax=zmax, rest=rest, bl=bl, div=e.diverged())
    return tag, test, r


if __name__ == '__main__':
    arc = pickle.load(open('results/cheney_vox_s1/archive.pkl', 'rb'))['archive']
    top = sorted(arc.values(), key=lambda e: -e['fitness'])[:3]
    robots = [(f'#{i+1}', e['fitness'], e['genome']) for i, e in enumerate(top)]
    t0 = time.time()
    with Pool(18) as p:
        out = p.map(job, [(t, k, g) for t, _, g in robots for k in 'ABCEGD'])
    res = {(t, k): r for t, k, r in out}
    print(f"done in {time.time()-t0:.0f}s\n")
    print(f"{'robot':<6}{'archive':>9}{'A repro':>9}{'B settle2':>11}{'ret':>6}{'C dir':>8}"
          f"{'E dt/4':>9}{'G noET':>9}")
    for t, arch, g in robots:
        A, B, C, E, G = (float(res[(t, k)]) for k in 'ABCEG')
        print(f"{t:<6}{arch:>9.4f}{A:>9.4f}{B:>11.4f}{100*B/max(A,1e-9):>5.0f}%{C:>8.4f}"
              f"{E:>9.4f}{G:>9.4f}")
    print("\n3-second run (BL after 1/2/3 s), uprightness, COM rest -> peak, divergence")
    for t, arch, g in robots:
        D = res[(t, 'D')]; tr = D['traj']
        print(f"  {t:<4} {tr.get(1,0):.3f} {tr.get(2,0):.3f} {tr.get(3,0):.3f}  "
              f"3s/1s {tr.get(3,0)/max(tr.get(1,1e-9),1e-9):.2f}   upright {D['upmin']:.2f}   "
              f"COM {D['rest']*1e3:.0f} -> {D['zmax']*1e3:.0f} mm (body {D['bl']*1e3:.0f} mm)   "
              f"diverged {D['div']}")
    print("\nabsolute distance at 10 cycles:")
    for t, arch, g in robots:
        print(f"  {t:<4} {float(res[(t,'A')])*res[(t,'D')]['bl']:.3f} m   "
              f"({float(res[(t,'A')])/10:.3f} BL/cycle; Cheney 0.35-0.40)")
