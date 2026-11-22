"""Amplitude sweep on the corrected physics.

The 4.12 BL gait was carried by the body sinking ~1.8 voxels into the floor. At the corrected
stiffness a +-20% linear strain makes ~20 N per voxel against 0.01 N of weight, so amplitude is the
prime suspect - and the papers put it anywhere from 6.3% to 39% linear, so 20% is not privileged.

Measures, on the same 30 random seed-1 robots a run starts from (the population evolution actually
sees, not champions tuned to one amplitude):
  - peak floor penetration, in voxels, over 10 cycles
  - fitness, and how many robots move at all
If penetration scales with amplitude then the floor is behaving as a spring and amplitude is the fix;
if it does not, the floor model itself is at fault.
"""
import os, sys, time
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilot_corrected import make_population, SS

AMPS = (0.06, 0.10, 0.14, 0.20)
POP = make_population()
N = 20


def job(a):
    k, amp = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=amp, actuation_frequency=40.0,
                          fitness_mode='forward', friction=SS, materials='cheney2013',
                          floor_contact='voxelyze')
    e.load_robot(POP[k])
    nb, r = e.model.nbody, e.voxel_size / 2
    x0 = np.array(e.data.xpos[1:nb])
    bl = float((x0.max(0) - x0.min(0)).max()) + e.voxel_size
    ix = float(e.get_position()[0])
    deep = 0.0
    for _ in range(int(0.25 / e.default_timestep)):
        e.step()
        deep = max(deep, (r - float(e.data.xpos[1:nb, 2].min())) / e.voxel_size)
    f = max(0.0, (float(e.get_position()[0]) - ix) / bl)
    return k, amp, deep, f, e.diverged()


if __name__ == '__main__':
    jobs = [(k, a) for k in range(N) for a in AMPS]
    t0 = time.time()
    with Pool(16) as p:
        out = p.map(job, jobs)
    res = {(k, a): r for k, a, *r in out}
    print(f"done in {time.time()-t0:.0f}s   corrected physics, 40 Hz, 10 cycles, {N} random bodies\n")
    print(f"{'amp':>6}{'peak penetration (voxels)':>28}{'':>4}{'best BL':>9}{'mean BL':>9}"
          f"{'moving':>9}{'blew up':>9}")
    print(f"{'':>6}{'median':>10}{'90th':>9}{'worst':>9}")
    base = None
    for a in AMPS:
        d = np.array([res[(k, a)][0] for k in range(N)])
        f = np.array([res[(k, a)][1] for k in range(N)])
        dv = sum(res[(k, a)][2] for k in range(N))
        if base is None:
            base = np.median(d) / a
        print(f"{a:>6.2f}{np.median(d):>10.2f}{np.quantile(d, .9):>9.2f}{d.max():>9.2f}{'':>4}"
              f"{f.max():>9.3f}{f.mean():>9.3f}{int((f > 0.02).sum()):>6}/{N}{dv:>6}/{N}")
    print("\n  1.00 = a voxel centre exactly at floor level. Voxelyze-faithful is well under 0.25.")
    print("  If penetration is proportional to amplitude, the floor is a spring and amplitude is the")
    print("  lever; if it flattens out, the floor model is the problem instead.")
    for a in AMPS:
        d = np.median([res[(k, a)][0] for k in range(N)])
        print(f"    amp {a:.2f}: penetration/amplitude = {d/a:.2f}   (proportional would be constant)")
