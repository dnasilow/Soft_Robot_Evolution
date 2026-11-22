"""Is the 36.6% floor penetration a soft floor, or just dynamic impact? Measures both, on the same
30 random robots, plus the true per-generation wall clock (the slowest robot, not the sum)."""
import os, sys, time
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilot_corrected import make_population, CFG, SS


def job(a):
    k, name = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    c = CFG[name]
    g = POP[k]
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=c['freq'],
                          fitness_mode='forward', friction=SS, materials=c['materials'],
                          floor_contact=c['floor_contact'])
    e.load_robot(g)
    nb, r = e.model.nbody, e.voxel_size / 2
    amp = e.v_amp.copy()
    e.v_amp[:] = 0.0                                   # settle with muscles OFF
    for _ in range(int(0.5 / e.default_timestep)):
        e.step()
    static = (r - float(np.array(e.data.xpos[1:nb, 2]).min())) / e.voxel_size
    e.v_amp[:] = amp
    t0 = time.time()
    worst = static
    for _ in range(int(c['sim'] / e.default_timestep)):
        e.step()
        worst = max(worst, (r - float(np.array(e.data.xpos[1:nb, 2]).min())) / e.voxel_size)
    return k, name, static, worst, time.time() - t0


POP = make_population()

if __name__ == '__main__':
    jobs = [(k, n) for k in range(30) for n in CFG]
    with Pool(15) as p:
        out = p.map(job, jobs)
    res = {(k, n): (s, w, t) for k, n, s, w, t in out}
    print(f"{'config':<14}{'static pen':>12}{'peak pen':>11}{'slowest robot':>15}"
          f"{'gen time est':>14}")
    for n in CFG:
        st = np.array([res[(k, n)][0] for k in range(30)])
        wo = np.array([res[(k, n)][1] for k in range(30)])
        ts = np.array([res[(k, n)][2] for k in range(30)])
        print(f"{n:<14}{100*np.median(st):>11.1f}%{100*np.median(wo):>10.1f}%"
              f"{ts.max():>14.0f}s{ts.max()/60:>13.1f}m")
        print(f"{'':<14}  worst-case static {100*st.max():>5.1f}%   worst-case peak "
              f"{100*wo.max():>5.1f}%")
    a = np.array([res[(k, 'A old')][2] for k in range(30)]).max()
    b = np.array([res[(k, 'B corrected')][2] for k in range(30)]).max()
    print(f"\n  per-generation wall clock (30 robots on 30 workers = the slowest one):")
    print(f"    A old        {a/60:5.1f} min  -> 300 gens = {a*300/3600:5.1f} h")
    print(f"    B corrected  {b/60:5.1f} min  -> 300 gens = {b*300/3600:5.1f} h")
    print("  (cheney_neat_s1 actually averaged ~3.5 min/gen, so treat these as upper bounds:")
    print("   this pilot ran 15 workers on 30 jobs, and the settle pass is extra.)")
