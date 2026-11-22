"""V5 (speed), V6 (stability / chatter) and the Phase-2 preview, on real champions, dev code.

Each champion at 10 cycles (sim 1.0 s after 0.5 s settle) on three floors:
  original (0.7) | single 1.0 | Cheney stick-slip 1.0 / 0.5 (slip > 20 mm/s, stick < 10 mm/s)
Stick-slip runs also count state flips per voxel (chatter = a voxel flipping every few steps).
"""
import sys, time, pickle
import numpy as np
from multiprocessing import Pool
DEV = r'C:/Users/DNASIL~1/AppData/Local/Temp/claude/C--SoftRobotEvolution/5cc73d86-944b-40cc-9802-a2f3f18f9a8b/scratchpad/dev_friction'
ROBOTS = {'s2 champ': r'C:/SoftRobotEvolution/results/cheney_repro_s2/best_robot.pkl',
          's1 champ': r'C:/SoftRobotEvolution/results/cheney_repro_s1/best_robot.pkl'}
FLOORS = {'original 0.7': None,
          'single 1.0': {'mode': 'single', 'mu': 1.0},
          'Cheney 1.0/0.5': {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}}


def job(args):
    tag, floor = args
    sys.path.insert(0, DEV)
    from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
    g = pickle.load(open(ROBOTS[tag], 'rb'))['genome']
    fr = FLOORS[floor]
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward',
                            **({} if fr is None else {'friction': fr}))
    e.load_robot(g)
    st = {'flips': None, 'steps': 0}
    if e._ss_sliding is not None:
        st['flips'] = np.zeros(len(e._ss_sliding), int)
        orig = e._update_floor_friction
        def counted():
            before = e._ss_sliding.copy(); orig()
            st['flips'] += before != e._ss_sliding; st['steps'] += 1
        e._update_floor_friction = counted
    t0 = time.time()
    f = float(e.get_fitness(simulation_time=1.0, settle_time=0.5))
    secs = time.time() - t0
    finite = bool(np.all(np.isfinite(e.data.qpos))) and bool(np.all(np.isfinite(e.data.qvel)))
    out = dict(fit=f, secs=secs, finite=finite, vmax=float(np.abs(e.data.qvel).max()))
    if st['flips'] is not None:
        sim_s = st['steps'] * e.default_timestep
        out.update(flips_per_voxel_s=float(st['flips'].mean() / sim_s),
                   max_flips_s=float(st['flips'].max() / sim_s),
                   sliding_now=float(e._ss_sliding.mean()))
    return tag, floor, out


if __name__ == '__main__':
    t0 = time.time()
    with Pool(len(ROBOTS) * len(FLOORS)) as p:
        res = {(t, f): r for t, f, r in p.map(job, [(t, f) for t in ROBOTS for f in FLOORS])}
    print(f"done in {time.time()-t0:.0f}s\n")
    print("PHASE 2 PREVIEW - BL at 10 cycles (Cheney's protocol), same bodies, three floors")
    print(f"  {'robot':<9}" + ''.join(f"{f:>18}" for f in FLOORS))
    for t in ROBOTS:
        base = res[(t, 'original 0.7')]['fit']
        print(f"  {t:<9}" + ''.join(f"{res[(t, f)]['fit']:>11.4f} ({100*res[(t, f)]['fit']/base:>3.0f}%)" for f in FLOORS))
    print("\nV5 speed (wall time for 1.5 s simulated; contended machine, so compare ratios)")
    for t in ROBOTS:
        b = res[(t, 'original 0.7')]['secs']
        print(f"  {t}: " + '   '.join(f"{f} {res[(t, f)]['secs']:.0f}s ({res[(t, f)]['secs']/b:.2f}x)" for f in FLOORS))
    print("\nV6 stability / chatter")
    for t in ROBOTS:
        for f in FLOORS:
            r = res[(t, f)]
            extra = (f"  flips {r['flips_per_voxel_s']:.1f}/voxel/s (max voxel {r['max_flips_s']:.0f}/s), "
                     f"sliding at end {100*r['sliding_now']:.0f}%") if 'flips_per_voxel_s' in r else ''
            print(f"  {t:<9} {f:<15} finite={r['finite']}  max|qvel|={r['vmax']:.1f}{extra}")
    print("  chatter would show as a voxel flipping hundreds of times per second (2000 steps/s)")
