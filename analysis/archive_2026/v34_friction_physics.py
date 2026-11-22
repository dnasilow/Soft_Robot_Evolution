"""V3 (incline hysteresis) and V4 (pull test) for the stick-slip floor, dev code.

V3: tilt gravity by theta (equivalent to tilting the floor); a block starting at rest vs. one
    given a 0.2 m/s push down-slope. Stick-slip 1.0/0.5 at 35 deg (tan = 0.70, between mu_k
    and mu_s) must HOLD at rest but KEEP SLIDING once pushed. A single mu cannot do both.
V4: flat floor, ramp a horizontal force on the block; breakaway force/weight should be ~mu_s,
    then under a constant force the sliding resistance/weight should be ~mu_k.
"""
import sys, numpy as np
DEV = r'C:/Users/DNASIL~1/AppData/Local/Temp/claude/C--SoftRobotEvolution/5cc73d86-944b-40cc-9802-a2f3f18f9a8b/scratchpad/dev_friction'
sys.path.insert(0, DEV)
import mujoco
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def block(fr, shape=(1, 1, 1)):
    g = np.zeros((10, 10, 10), np.int8)
    g[4:4 + shape[0], 4:4 + shape[1], 0:shape[2]] = 3
    e = MuJoCoTendonPhysics(actuation_amplitude=0.16, friction=fr)
    e.load_robot(g)
    return e


def com(e):
    return np.mean(e.data.xpos[1:e.model.nbody], axis=0)


def incline(fr, deg, push, T=1.0, shape=(1, 1, 1)):
    e = block(fr, shape); m, d = e.model, e.data
    th = np.radians(deg)
    m.opt.gravity[:] = [9.81 * np.sin(th), 0.0, -9.81 * np.cos(th)]
    nb = m.nbody
    if push:
        d.qvel.reshape(-1, 6)[:, 0] = 0.2
    mujoco.mj_forward(m, d)
    x0 = com(e)[0]; vs = []
    n = int(T / e.default_timestep)
    for s in range(n):
        e.step()
        if s >= n // 2:
            vs.append(float(np.mean(d.qvel.reshape(-1, 6)[:, 0])))
    return com(e)[0] - x0, float(np.mean(d.qvel.reshape(-1, 6)[:, 0])), float(np.mean(vs))


def pull(fr, shape=(1, 1, 1)):
    e = block(fr, shape); m, d = e.model, e.data
    nb = m.nbody; W = float(mujoco.mj_getTotalmass(m)) * 9.81; M = W / 9.81
    for _ in range(400):                       # settle 0.2 s
        e.step()
    # 1) ramp force 0 -> 1.4 W over 1.4 s; breakaway = force when speed first > 2 cm/s
    ramp, brk = 1.0, None
    x_start = com(e)[0]
    for s in range(int(1.4 / e.default_timestep)):
        F = ramp * W * s * e.default_timestep
        d.xfrc_applied[1:nb, 0] = F / (nb - 1)
        e.step()
        if brk is None and float(np.mean(d.qvel.reshape(-1, 6)[:, 0])) > 0.02:
            brk = F / W
            break
    # 2) constant force 0.8 W while sliding: resistance = (F - M a) / W
    d.xfrc_applied[1:nb, 0] = 0.8 * W / (nb - 1)
    vels = []
    for s in range(int(0.3 / e.default_timestep)):
        e.step()
        vels.append(float(np.mean(d.qvel.reshape(-1, 6)[:, 0])))
    v = np.array(vels[len(vels) // 3:]); t = np.arange(len(v)) * e.default_timestep
    a = np.polyfit(t, v, 1)[0] if v[-1] > 0.02 else 0.0
    resist = (0.8 * W - M * a) / W if v[-1] > 0.02 else float('nan')
    return brk, resist, v[-1]


if __name__ == '__main__':
    print("V3 INCLINE  (displacement over 1 s; creep = mean speed over the last 0.5 s)")
    cases = [("stick-slip 1.0/0.5", SS, 35), ("single mu 0.7", {'mode': 'single', 'mu': 0.7}, 33),
             ("single mu 0.7", {'mode': 'single', 'mu': 0.7}, 37)]
    for label, fr, deg in cases:
        for push in (False, True):
            dx, vend, vmean = incline(fr, deg, push)
            state = "SLIDES" if vend > 0.01 else "HOLDS"
            print(f"  {label:<20} {deg}deg  {'pushed 0.2 m/s' if push else 'from rest     '}: "
                  f"moved {dx*1e3:8.2f} mm   end speed {vend*1e3:7.2f} mm/s  -> {state}")
    print("  expect: stick-slip at 35deg HOLDS from rest but SLIDES when pushed (hysteresis);")
    print("          single mu gives the SAME outcome both ways (holds at 33deg, slides at 37deg)")
    print("\nV4 PULL TEST (flat floor; force/weight at breakaway, then sliding resistance/weight)")
    for label, fr in (("stick-slip 1.0/0.5", SS), ("single mu 0.7", {'mode': 'single', 'mu': 0.7}),
                      ("original floor (0.7)", None)):
        for shape in ((1, 1, 1), (2, 2, 1)):
            brk, res, vend = pull(fr, shape)
            print(f"  {label:<21} block {shape}: breakaway {brk if brk is None else round(brk, 3)}   "
                  f"sliding resistance {res:.3f}   (end speed {vend:.3f} m/s)")
    print("  expect: stick-slip breakaway ~1.0, resistance ~0.5; single/original ~0.7 and ~0.7")
