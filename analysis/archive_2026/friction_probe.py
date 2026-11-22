"""Does the full 10x10 footprint act as a friction BRAKE, or is friction the ENGINE?

Robot: cheney_repro_s2 champion (4.0823 BL). Two experiments:
  1. Friction sweep: scale sliding friction of every geom (ground + voxels; MuJoCo combines a
     contact pair by element-wise max, so the contact coefficient scales by k) and re-measure
     fitness. Brake -> less friction is faster. Engine -> less friction is slower.
  2. Contact trace over 5 steady-state cycles: how much of the footprint actually touches the
     floor, where the load sits (normal-force-weighted contact x, relative to COM), and whether
     the load shifts front/back in step with which edge moves (the anchoring signature).
"""
import os, sys, time, pickle
import numpy as np
from multiprocessing import Pool

ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
GENOME = pickle.load(open('results/cheney_repro_s2/best_robot.pkl', 'rb'))['genome']


def engine(k=1.0):
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward')
    e.load_robot(GENOME)
    e.model.geom_friction[:, 0] *= k
    return e


def sweep(k):
    t0 = time.time()
    f = float(engine(k).get_fitness(simulation_time=2.5, settle_time=0.5))
    return ('sweep', k, dict(fit=f, secs=time.time() - t0))


def trace(_):
    import mujoco
    e = engine(1.0); m, d = e.model, e.data
    nb = m.nbody
    x0 = np.array(d.xpos[1:nb], copy=True)
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    ground = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, 'ground')
    weight = float(mujoco.mj_getTotalmass(m)) * 9.81
    # bottom layer, front (+X) edge and rear edge, by undeformed position
    zb = x0[:, 2] <= x0[:, 2].min() + 0.5 * e.voxel_size
    bottom = set(np.where(zb)[0] + 1)                     # body ids
    xb = x0[zb, 0]
    front = np.where(zb & (x0[:, 0] >= xb.max() - 0.5 * e.voxel_size))[0] + 1
    rear = np.where(zb & (x0[:, 0] <= xb.min() + 0.5 * e.voxel_size))[0] + 1

    for _ in range(int(0.5 / e.default_timestep)):     # settle
        e.step()
    for _ in range(int(1.0 / e.default_timestep)):     # 10 cycles to reach steady state
        e.step()
    f6 = np.zeros(6)
    rows = []
    every = 5                                          # 2.5 ms -> 40 samples per 100 ms cycle
    prev_f = prev_r = None
    for s in range(int(0.5 / e.default_timestep)):     # 5 steady cycles
        e.step()
        if s % every:
            continue
        touching, fn_tot, fx = set(), 0.0, 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            if ground not in (c.geom1, c.geom2):
                continue
            other = c.geom2 if c.geom1 == ground else c.geom1
            mujoco.mj_contactForce(m, d, i, f6)
            touching.add(int(m.geom_bodyid[other]))
            fn_tot += f6[0]; fx += f6[0] * c.pos[0]
        com_x = float(np.mean(d.xpos[1:nb, 0]))
        load_x = (fx / fn_tot - com_x) / bl if fn_tot > 0 else 0.0
        fxp = float(d.xpos[front, 0].mean()); rxp = float(d.xpos[rear, 0].mean())
        vf = (fxp - prev_f) / (every * e.default_timestep) if prev_f is not None else np.nan
        vr = (rxp - prev_r) / (every * e.default_timestep) if prev_r is not None else np.nan
        prev_f, prev_r = fxp, rxp
        rows.append((len(touching), len(touching & bottom), fn_tot / weight, load_x, vf, vr))
    R = np.array(rows[1:], dtype=float)
    return ('trace', 0, dict(R=R, n_bottom=len(bottom), n_front=len(front), n_rear=len(rear)))


def dispatch(job):
    kind, arg = job
    return sweep(arg) if kind == 's' else trace(arg)


if __name__ == '__main__':
    t0 = time.time()
    with Pool(5) as p:
        res = p.map(dispatch, [('s', 0.25), ('s', 0.5), ('s', 1.0), ('s', 2.0), ('t', 0)])
    print(f'done in {time.time()-t0:.0f}s\n')

    print('1. FRICTION SWEEP  (contact mu = 0.7 x k; brake -> lower k faster, engine -> lower k slower)')
    base = next(r['fit'] for kind, k, r in res if kind == 'sweep' and k == 1.0)
    for kind, k, r in res:
        if kind == 'sweep':
            print(f'   k={k:<5} mu={0.7*k:.3f}   fitness {r["fit"]:.4f} BL   ({100*r["fit"]/max(base,1e-9):.0f}% of baseline)')

    R, info = next((r['R'], r) for kind, _, r in res if kind == 'trace')
    n_touch, n_bot, load, lx, vf, vr = R.T
    print(f'\n2. CONTACT TRACE  (5 steady cycles, {len(R)} samples; bottom layer = {info["n_bottom"]} voxels)')
    print(f'   voxels touching floor : mean {n_touch.mean():.1f}  min {n_touch.min():.0f}  max {n_touch.max():.0f}')
    print(f'   of which bottom-layer : mean {n_bot.mean():.1f} / {info["n_bottom"]}  '
          f'(= {100*n_bot.mean()/info["n_bottom"]:.0f}% of the footprint in contact on average)')
    print(f'   normal force / weight : mean {load.mean():.2f}  range {load.min():.2f}-{load.max():.2f}')
    print(f'   load centre vs COM    : range {lx.min():+.3f} to {lx.max():+.3f} BL   (+ = load toward the front)')
    ok = np.isfinite(vf) & np.isfinite(vr)
    print(f'   front-edge x-velocity : mean {vf[ok].mean():+.4f} m/s   range {vf[ok].min():+.3f}..{vf[ok].max():+.3f}')
    print(f'   rear-edge  x-velocity : mean {vr[ok].mean():+.4f} m/s   range {vr[ok].min():+.3f}..{vr[ok].max():+.3f}')
    print(f'   corr(load centre, front-edge velocity) = {np.corrcoef(lx[ok], vf[ok])[0,1]:+.2f}')
    print(f'   corr(load centre, rear-edge  velocity) = {np.corrcoef(lx[ok], vr[ok])[0,1]:+.2f}')
    print('   anchoring signature: load at REAR while FRONT advances (corr<0 with front), '
          'load at FRONT while REAR advances (corr>0 with rear)')
    # load-centre trace over one cycle (40 samples), coarse
    cyc = lx[:40]
    print('   one cycle of load centre (every 10 ms): ' + ' '.join(f'{v:+.2f}' for v in cyc[::4]))
    print('   one cycle of voxels in contact        : ' + ' '.join(f'{int(v):>5}' for v in n_touch[:40:4]))
