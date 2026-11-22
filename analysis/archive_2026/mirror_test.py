"""Is the right-hand turn a physics bias? Mirror the plateau champion (material gait, no control
net, so the mirror is exact) in y and in x. A symmetric engine must give mirrored paths."""
import os, sys, pickle
import numpy as np
from multiprocessing import Pool
ROOT = r'C:\SoftRobotEvolution'
sys.path.insert(0, ROOT); os.chdir(ROOT)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}

def run(a):
    name, g = a
    from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
    e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0, fitness_mode='forward',
                          friction=SS, materials='cheney2013', floor_contact='voxelyze')
    e.load_robot(g)
    c0 = np.array(e.get_position(), float)
    n1 = int(0.025 / e.default_timestep)
    out = {}
    for cyc in range(1, 61):
        for _ in range(n1):
            e.step()
        if cyc in (10, 30, 60):
            out[cyc] = (np.array(e.get_position(), float) - c0) / (10 * e.voxel_size)
    return name, out

def main():
    g = np.asarray(pickle.load(open('results/cheney_fix_s1/best_robot.pkl', 'rb'))['genome'])
    jobs = [('original', g), ('mirrored in y', g[:, ::-1, :].copy()), ('mirrored in x', g[::-1, :, :].copy())]
    with Pool(3) as p:
        out = dict(p.map(run, jobs))
    print("plateau champion, COM displacement in workspace widths (x, y)")
    for n, o in out.items():
        print(f"  {n:<15}" + "   ".join(f"c{c}: ({v[0]:+.2f}, {v[1]:+.2f})" for c, v in o.items()))
    print("  symmetric engine: y-mirror flips the sign of y only; x-mirror flips the sign of x only")

if __name__ == '__main__':
    main()
