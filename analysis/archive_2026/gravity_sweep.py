"""Which gravity is usable with the corrected materials and the Voxelyze floor?

274.68 matches Cheney's sag per voxel, but the settling work showed sag does NOT explain morphology,
so the rescaled gravity buys us nothing and costs floor fidelity. Sweeps gravity on the same random
bodies and reports how far voxels sink, at rest and at peak during actuation, plus what it does to
fitness. A body partly INSIDE the floor makes both the contact geometry and the friction model wrong,
so peak penetration is the number that decides this.
"""
import os, sys, time
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilot_corrected import make_population, SS

GRAVITIES = (9.81, 27.468, 100.0, 274.68)
POP = make_population()
N = 12


def job(a):
    k, g_acc = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                          fitness_mode='forward', friction=SS, materials='cheney2013',
                          floor_contact='voxelyze', gravity=g_acc)
    e.load_robot(POP[k])
    nb, r = e.model.nbody, e.voxel_size / 2
    amp = e.v_amp.copy(); e.v_amp[:] = 0.0
    for _ in range(int(0.5 / e.default_timestep)):
        e.step()
    static = (r - float(np.array(e.data.xpos[1:nb, 2]).min())) / e.voxel_size
    e.v_amp[:] = amp
    worst = static
    for _ in range(int(0.25 / e.default_timestep)):
        e.step()
        worst = max(worst, (r - float(np.array(e.data.xpos[1:nb, 2]).min())) / e.voxel_size)
    e2 = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                           fitness_mode='forward', friction=SS, materials='cheney2013',
                           floor_contact='voxelyze', gravity=g_acc)
    e2.load_robot(POP[k])
    f = float(e2.get_fitness(0.25, 0.0, early_term_threshold=0.02, early_term_fraction=0.5))
    return k, g_acc, static, worst, f, e2.diverged()


if __name__ == '__main__':
    jobs = [(k, g) for k in range(N) for g in GRAVITIES]
    with Pool(16) as p:
        out = p.map(job, jobs)
    res = {(k, g): r for k, g, *r in out}
    print(f"cheney2013 materials + Voxelyze floor, 40 Hz, 10 cycles, {N} random bodies\n")
    print(f"{'gravity':>9}{'static pen':>12}{'peak pen':>11}{'worst peak':>12}"
          f"{'best BL':>10}{'moving':>9}{'blew up':>9}")
    for g in GRAVITIES:
        st = np.array([res[(k, g)][0] for k in range(N)])
        wo = np.array([res[(k, g)][1] for k in range(N)])
        fs = np.array([res[(k, g)][2] for k in range(N)])
        dv = sum(res[(k, g)][3] for k in range(N))
        print(f"{g:>9.2f}{100*np.median(st):>11.1f}%{100*np.median(wo):>10.1f}%"
              f"{100*wo.max():>11.1f}%{fs.max():>10.4f}{int((fs > 0.02).sum()):>6}/{N}"
              f"{dv:>6}/{N}")
    print("\n  pen = how far the lowest voxel centre is below its resting height, in voxels.")
    print("  A usable floor keeps the PEAK well under ~25% of a voxel.")
