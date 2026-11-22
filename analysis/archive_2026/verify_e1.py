"""Verify the E1 (cheney_floor_s1) champion: Cheney stick-slip floor, 10 cycles, early-term 0.02 @20%.
Checks per robot: A reproduce | B settle 2.0 | C directed (ground) | D 3-s trajectory, upright, NaN |
E half timestep | F original floor (cross-floor). Reference: old s2 champion on the same tests."""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def eng(g, mode='forward', fr=SS, dt=None):
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode=mode, **({} if fr is None else {'friction': fr}))
    e.load_robot(g)
    if dt:
        e.model.opt.timestep = dt; e.default_timestep = dt
    return e


def job(a):
    tag, test, g = a
    if test == 'A': return tag, test, float(eng(g).get_fitness(1.0, 0.5, early_term_threshold=0.02))
    if test == 'B': return tag, test, float(eng(g).get_fitness(1.0, 2.0, early_term_threshold=0.02))
    if test == 'C': return tag, test, float(eng(g, 'directed').get_fitness(1.0, 2.0, early_term_threshold=0.02))
    if test == 'E': return tag, test, float(eng(g, dt=0.00025).get_fitness(1.0, 0.5, early_term_threshold=0.02))
    if test == 'F': return tag, test, float(eng(g, fr=None).get_fitness(1.0, 0.5, early_term_threshold=0.02))
    e = eng(g); nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    for _ in range(int(0.5 / e.default_timestep)): e.step()
    xs = np.array(e.data.xpos[1:nb]); z = xs[:, 2]
    lo, hi = z <= np.quantile(z, 0.25), z >= np.quantile(z, 0.75)
    def up():
        p = e.data.xpos[1:nb]; v = p[hi].mean(0) - p[lo].mean(0); return float(v[2] / (np.linalg.norm(v) + 1e-12))
    ix = float(e.get_position()[0]); out, upmin, nan = {}, 1.0, False
    for s in range(1, int(3.0 / e.default_timestep) + 1):
        e.step()
        if s % 40 == 0:
            if not np.all(np.isfinite(e.data.qvel)): nan = True; break
            upmin = min(upmin, up())
        if s % 2000 == 0: out[s // 2000] = (float(e.get_position()[0]) - ix) / bl
    return tag, test, dict(traj=out, upmin=upmin, nan=nan, bl=bl)


if __name__ == '__main__':
    arc = pickle.load(open('results/cheney_floor_s1/archive.pkl', 'rb'))['archive']
    robots = [(f'E1#{i+1}', e['fitness'], e['genome']) for i, e in
              enumerate(sorted(arc.values(), key=lambda e: -e['fitness'])[:3])]
    robots.append(('old s2', float('nan'), pickle.load(open('results/cheney_repro_s2/best_robot.pkl', 'rb'))['genome']))
    t0 = time.time()
    with Pool(24) as p:
        res = {(t, k): r for t, k, r in p.map(job, [(t, k, g) for t, _, g in robots for k in 'ABCDEF'])}
    print(f"done in {time.time()-t0:.0f}s\n")
    print(f"{'robot':<8}{'archive':>8}{'A:repro':>9}{'B:st2.0':>9}{'ret':>6}{'C:dir':>8}{'E:dt/2':>8}{'E/A':>6}{'F:orig floor':>13}")
    for t, arch, g in robots:
        A, B, C, E, F = (res[(t, k)] for k in 'ABCEF')
        print(f"{t:<8}{arch:>8.4f}{A:>9.4f}{B:>9.4f}{100*B/A:>5.0f}%{C:>8.4f}{E:>8.4f}{100*E/A:>5.0f}%{F:>13.4f}")
    print("\n3-second run on the Cheney floor (BL after 1 / 2 / 3 s; steady gait = linear), min uprightness, NaN")
    for t, arch, g in robots:
        D = res[(t, 'D')]; tr = D['traj']
        print(f"  {t:<8} " + '  '.join(f"{tr.get(k, float('nan')):.3f}" for k in (1, 2, 3))
              + f"   ratio 3s/1s {tr.get(3, float('nan'))/max(tr.get(1, 1e-9), 1e-9):.2f}   upright min {D['upmin']:.2f}   NaN {D['nan']}")
    print("\ncomposition:")
    for t, arch, g in robots:
        n = int((g != 0).sum()); m = [int((g == k).sum()) for k in (1, 2, 3, 4)]
        idx = np.argwhere(g != 0); ext = idx.max(0) - idx.min(0) + 1
        print(f"  {t:<8} vox={n:<4} mus1/mus2/soft/stiff={m}  bbox={tuple(int(x) for x in ext)}  fill={n/np.prod(ext):.2f}  "
              f"abs@10cyc={res[(t,'A')]*res[(t,'D')]['bl']:.3f} m")
