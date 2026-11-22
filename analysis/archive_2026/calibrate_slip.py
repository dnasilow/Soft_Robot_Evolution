"""Calibrate the stick-slip speed thresholds against MuJoCo's soft-friction creep.

1. Creep: a stuck block (floor mu fixed at 1.0, no switching) under a constant sideways force of
   f x weight -> steady creep speed. The slip threshold must exceed the creep at the loads we
   want to count as 'stuck', else the block flips to kinetic before reaching mu_s.
2. Sweep v_on (v_off = v_on/2): pull-test breakaway and sliding resistance, plus the 35-deg
   incline hysteresis check, for a 1-voxel and a 2x2x1 block.
"""
import sys, numpy as np
sys.path.insert(0, r'C:/Users/DNASIL~1/AppData/Local/Temp/claude/C--SoftRobotEvolution/5cc73d86-944b-40cc-9802-a2f3f18f9a8b/scratchpad')
import v34_friction_physics as V
import mujoco


def creep(frac, shape=(1, 1, 1)):
    e = V.block({'mode': 'single', 'mu': 1.0}, shape); m, d = e.model, e.data
    nb = m.nbody; W = float(mujoco.mj_getTotalmass(m)) * 9.81
    for _ in range(400):
        e.step()
    d.xfrc_applied[1:nb, 0] = frac * W / (nb - 1)
    vs = []
    for s in range(int(0.6 / e.default_timestep)):
        e.step()
        if s > 600:
            vs.append(float(np.mean(d.qvel.reshape(-1, 6)[:, 0])))
    return float(np.mean(vs))


if __name__ == '__main__':
    print("1. CREEP of a stuck block (mu 1.0) under constant sideways load:")
    for shape in ((1, 1, 1), (2, 2, 1)):
        print(f"   block {shape}: " + "   ".join(f"{f:.2f}W -> {creep(f, shape)*1e3:6.2f} mm/s"
                                                for f in (0.5, 0.7, 0.9, 0.95, 0.99)))
    print("\n2. THRESHOLD SWEEP (v_off = v_on/2): breakaway / resistance / 35deg hold-from-rest & slide-when-pushed")
    for v_on in (0.01, 0.02, 0.03, 0.05, 0.08):
        fr = dict(V.SS, v_on=v_on, v_off=v_on / 2)
        row = []
        for shape in ((1, 1, 1), (2, 2, 1)):
            brk, res, _ = V.pull(fr, shape)
            row.append(f"{shape}: brk {brk if brk is None else round(brk, 3)} res {res:.3f}")
        _, v_rest, _ = V.incline(fr, 35, False)
        _, v_push, _ = V.incline(fr, 35, True)
        hyst = "OK" if (v_rest < v_on and v_push > 0.05) else "FAIL"
        print(f"   v_on {v_on*1e3:4.0f} mm/s | {' | '.join(row)} | incline rest {v_rest*1e3:5.2f} mm/s, "
              f"pushed {v_push:.2f} m/s -> hysteresis {hyst}")
