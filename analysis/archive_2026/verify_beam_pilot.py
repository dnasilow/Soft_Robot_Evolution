"""Verify the cheney_beam_s1 pilot's top 3 (beam body, stick-slip 1.0/0.5, amp 0.2, 10 cycles,
early-term 0.02 BL @ 50%). Checks per robot:
  A reproduce (exact run settings)          B settle 2.0 s (transient?)
  C directed = ground penalty (airborne?)   D 3-s run: linear? upright? NaN? peak voxel speed/spin
  E half time step                          F Voxelyze's own step rule (0.7/(2*pi*sqrt(k/m)))
  G early termination off (full window)"""
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


def set_dt(e, dt):
    e.default_timestep = dt; e.model.opt.timestep = dt


def job(a):
    tag, test, g = a
    t0 = time.time()
    if test == 'A': r = eng(g).get_fitness(1.0, 0.5, **ET)
    elif test == 'B': r = eng(g).get_fitness(1.0, 2.0, **ET)
    elif test == 'C': r = eng(g, 'directed').get_fitness(1.0, 2.0, **ET)
    elif test == 'E':
        e = eng(g); set_dt(e, e.default_timestep / 2); r = e.get_fitness(1.0, 0.5, **ET)
    elif test == 'F':
        e = eng(g); set_dt(e, min(0.7 / (2 * np.pi * np.sqrt(e.K_ax.max() / e._m)), 0.0005))
        r = e.get_fitness(1.0, 0.5, **ET)
    elif test == 'G': r = eng(g).get_fitness(1.0, 0.5, early_term_threshold=-1e9)
    else:                                                     # D: 3-second trajectory
        e = eng(g); nb = e.model.nbody
        x0 = np.array(e.data.xpos[1:nb]); bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
        for _ in range(int(0.5 / e.default_timestep)): e.step()
        z = e.data.xpos[1:nb, 2]; lo, hi = z <= np.quantile(z, 0.25), z >= np.quantile(z, 0.75)
        def up():
            p = e.data.xpos[1:nb]; v = p[hi].mean(0) - p[lo].mean(0); return float(v[2] / (np.linalg.norm(v) + 1e-12))
        ix = float(e.get_position()[0]); traj, upmin, vmax, wmax, zmax, nan = {}, 1.0, 0.0, 0.0, 0.0, False
        n1 = int(1.0 / e.default_timestep)
        for s in range(1, 3 * n1 + 1):
            e.step()
            if s % 50 == 0:
                if not np.all(np.isfinite(e.data.qvel)): nan = True; break
                upmin = min(upmin, up())
                vmax = max(vmax, float(np.abs(e.data.cvel[1:, 3:]).max()))
                wmax = max(wmax, float(np.abs(e.data.cvel[1:, :3]).max()))
                zmax = max(zmax, float(e.get_position()[2]))
            if s % n1 == 0: traj[s // n1] = (float(e.get_position()[0]) - ix) / bl
        r = dict(traj=traj, upmin=upmin, vmax=vmax, wmax=wmax, zmax=zmax, nan=nan, bl=bl, dt=e.default_timestep)
    return tag, test, r, time.time() - t0


if __name__ == '__main__':
    arc = pickle.load(open('results/cheney_beam_s1/archive.pkl', 'rb'))['archive']
    top = sorted(arc.values(), key=lambda e: -e['fitness'])[:3]
    robots = [(f'#{i+1}', e['fitness'], e['genome']) for i, e in enumerate(top)]
    t0 = time.time()
    with Pool(21) as p:
        out = p.map(job, [(t, k, g) for t, _, g in robots for k in 'ABCDEFG'])
    res = {(t, k): r for t, k, r, _ in out}; secs = {(t, k): s for t, k, _, s in out}
    print(f"done in {time.time()-t0:.0f}s\n")
    print(f"{'robot':<5}{'archive':>9}{'A:repro':>9}{'B:st2.0':>9}{'ret':>6}{'C:dir':>8}{'E:dt/2':>9}{'F:Vxlz dt':>10}{'G:no ET':>9}")
    for t, arch, g in robots:
        A, B, C, E, F, G = (float(res[(t, k)]) for k in 'ABCEFG')
        print(f"{t:<5}{arch:>9.4f}{A:>9.4f}{B:>9.4f}{100*B/A:>5.0f}%{C:>8.4f}{E:>9.4f}{F:>10.4f}{G:>9.4f}")
    print("\n3-second run (BL after 1/2/3 s; steady = linear), min uprightness, peak voxel speed / spin, peak COM height, NaN")
    for t, arch, g in robots:
        D = res[(t, 'D')]; tr = D['traj']
        print(f"  {t:<4} {tr.get(1, float('nan')):.3f} {tr.get(2, float('nan')):.3f} {tr.get(3, float('nan')):.3f}  "
              f"3s/1s {tr.get(3, float('nan'))/max(tr.get(1, 1e-9), 1e-9):.2f}  upright {D['upmin']:.2f}  "
              f"v {D['vmax']:.2f} m/s  w {D['wmax']:.0f} rad/s  COMz {D['zmax']*1e3:.1f} mm  NaN {D['nan']}  (dt {D['dt']*1e3:.4f} ms)")
    print("\ncomposition:")
    for t, arch, g in robots:
        n = int((g != 0).sum()); m = [int((g == k).sum()) for k in (1, 2, 3, 4)]
        idx = np.argwhere(g != 0); ext = idx.max(0) - idx.min(0) + 1
        print(f"  {t:<4} vox={n:<4} mus1/mus2/soft/bone={m}  bbox={tuple(int(x) for x in ext)}  fill={n/np.prod(ext):.2f}  "
              f"abs@10cyc={float(res[(t,'A')])*res[(t,'D')]['bl']:.3f} m")
