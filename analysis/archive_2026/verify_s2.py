"""Verify cheney_repro_s2's 4.08 BL jump: is it real locomotion or an exploit?

Per robot, five independent checks (run in parallel):
  A  forward  settle 0.5, 2.5 s      -> must reproduce the archive value
  B  forward  settle 2.0, 2.5 s      -> transient check (retention)
  C  directed settle 2.0, 2.5 s      -> ground penalty re-applied (airborne check)
  D  trajectory settle 0.5, 5.0 s    -> steady gait (BL@5s ~ 2x BL@2.5s) vs one-off lunge;
                                        uprightness (flip), max |qvel|, NaN
  E  forward  settle 0.5, 2.5 s at HALF timestep -> numerical exploit check
"""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
AMP = 0.16


def _engine(genome, mode):
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    e = MuJoCoTendonPhysics(actuation_amplitude=AMP, fitness_mode=mode)
    e.load_robot(genome)
    return e


def job(args):
    tag, test, genome = args
    t0 = time.time()
    if test in ('A', 'B', 'C', 'E'):
        mode = 'directed' if test == 'C' else 'forward'
        settle = 2.0 if test in ('B', 'C') else 0.5
        e = _engine(genome, mode)
        if test == 'E':
            e.model.opt.timestep = 0.00025
            e.default_timestep = 0.00025
        f = float(e.get_fitness(simulation_time=2.5, settle_time=settle))
        return tag, test, dict(fit=f, secs=time.time() - t0)

    # D: manual trajectory, replicating get_fitness's body_length / initial_x convention
    e = _engine(genome, 'forward')
    nb = e.model.nbody
    x0 = np.array(e.data.xpos[1:nb], copy=True)
    body_length = max(float((x0.max(0) - x0.min(0)).max()) + e.voxel_size, e.voxel_size)
    for _ in range(int(0.5 / e.default_timestep)):
        e.step()
    xs = np.array(e.data.xpos[1:nb], copy=True)
    # uprightness: unit vector from the initially-lowest quartile of voxels to the highest
    z = xs[:, 2]
    lo, hi = z <= np.quantile(z, 0.25), z >= np.quantile(z, 0.75)
    def upright():
        p = e.data.xpos[1:nb]
        v = p[hi].mean(0) - p[lo].mean(0)
        return float(v[2] / (np.linalg.norm(v) + 1e-12))
    ix = float(e.get_position()[0])
    marks, out = {1.25, 2.5, 3.75, 5.0}, {}
    n = int(5.0 / e.default_timestep)
    qmax, zmin, zmax, up_min, nan = 0.0, 9e9, -9e9, 1.0, False
    for s in range(1, n + 1):
        e.step()
        if s % 20 == 0:
            q = e.data.qvel
            if not np.all(np.isfinite(q)):
                nan = True
                break
            qmax = max(qmax, float(np.abs(q).max()))
            cz = float(e.get_position()[2]); zmin, zmax = min(zmin, cz), max(zmax, cz)
            up_min = min(up_min, upright())
        t = round(s * e.default_timestep, 6)
        if t in marks:
            out[t] = (float(e.get_position()[0]) - ix) / body_length
    return tag, test, dict(traj=out, qmax=qmax, zmin=zmin, zmax=zmax, up_end=upright(),
                           up_min=up_min, nan=nan, bl=body_length, secs=time.time() - t0)


if __name__ == '__main__':
    robots = []
    a2 = pickle.load(open('results/cheney_repro_s2/archive.pkl', 'rb'))['archive']
    for i, e in enumerate(sorted(a2.values(), key=lambda e: -e['fitness'])[:3]):
        robots.append((f's2#{i+1}', e['fitness'], e['genome']))
    b1 = pickle.load(open('results/cheney_repro_s1/best_robot.pkl', 'rb'))
    robots.append(('s1#1', b1['fitness'], b1['genome']))

    jobs = [(tag, t, g) for tag, _, g in robots for t in 'ABCDE']
    nproc = min(len(jobs), os.cpu_count() or 4)
    print(f'{len(jobs)} jobs on {nproc} processes (cpu_count={os.cpu_count()})', flush=True)
    t0 = time.time()
    with Pool(nproc) as p:
        res = {(tag, t): r for tag, t, r in p.imap_unordered(job, jobs)}
    print(f'done in {time.time()-t0:.0f}s\n', flush=True)

    print(f"{'robot':<6}{'arch':>8}{'A:repro':>9}{'B:st2.0':>9}{'C:dir':>8}{'ret':>6}{'E:dt/2':>8}{'E/A':>6}")
    for tag, arch, g in robots:
        A, B, C, E = (res[(tag, k)]['fit'] for k in 'ABCE')
        print(f"{tag:<6}{arch:>8.4f}{A:>9.4f}{B:>9.4f}{C:>8.4f}{100*B/max(A,1e-9):>5.0f}%{E:>8.4f}{100*E/max(A,1e-9):>5.0f}%")

    print(f"\nTRAJECTORY (5 s, BL travelled at each mark; steady gait => 5.0s ~ 2x 2.5s)")
    print(f"{'robot':<6}{'1.25s':>7}{'2.5s':>7}{'3.75s':>7}{'5.0s':>7}{'5/2.5':>7}{'up_end':>8}{'up_min':>8}{'qmax':>8}{'comZ':>14}{'NaN':>5}")
    for tag, arch, g in robots:
        D = res[(tag, 'D')]; tr = D['traj']
        r = tr.get(5.0, float('nan')) / max(tr.get(2.5, 1e-9), 1e-9)
        print(f"{tag:<6}" + ''.join(f"{tr.get(k, float('nan')):>7.3f}" for k in (1.25, 2.5, 3.75, 5.0))
              + f"{r:>7.2f}{D['up_end']:>8.2f}{D['up_min']:>8.2f}{D['qmax']:>8.2f}"
              + f"{D['zmin']:>7.3f}-{D['zmax']:<6.3f}{'YES' if D['nan'] else 'no':>5}")

    print('\ncomposition:')
    for tag, arch, g in robots:
        n = int((g != 0).sum()); m = {k: int((g == k).sum()) for k in (1, 2, 3, 4)}
        idx = np.argwhere(g != 0); ext = idx.max(0) - idx.min(0) + 1
        print(f"  {tag:<6} vox={n:<4} mat1={m[1]:<4} mat2={m[2]:<4} soft={m[3]:<4} stiff={m[4]:<4} "
              f"bbox={tuple(int(x) for x in ext)} fill={n/np.prod(ext):.2f} abs@2.5s={res[(tag,'A')]['fit']*res[(tag,'D')]['bl']:.3f} m")
