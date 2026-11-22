"""Find a small body that walks clearly in 10 cycles, for the score tests (fast to simulate)."""
import os, sys, time
import numpy as np
sys.path.insert(0, r'C:\SoftRobotEvolution'); os.chdir(r'C:\SoftRobotEvolution')
from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}

def grid(spec):
    g = np.zeros((20, 20, 20), np.int8)
    for c, m in spec: g[c] = m
    return g

bodies = {
 'halves 4x3x3': [((x, y, z), 1 if x < 2 else 2) for x in range(4) for y in range(3) for z in range(3)],
 'halves 6x3x3': [((x, y, z), 1 if x < 3 else 2) for x in range(6) for y in range(3) for z in range(3)],
 'L 5x3x3 + soft': [((x, y, z), (1 if x < 2 else 2) if z < 2 else 3) for x in range(5) for y in range(3) for z in range(3)],
 'wedge': [((x, y, z), 1 if z == 0 else 2) for x in range(5) for y in range(3) for z in range(3) if z <= x // 2],
 'legs': [((x, y, z), 1 if x < 2 else 2) for x in range(5) for y in range(3) for z in range(3) if z > 0 or x in (0, 4)],
}
for name, spec in bodies.items():
    for mirror in (False, True):
        g = grid(spec)
        if mirror:
            g = np.zeros_like(g); 
            mx = max(c[0] for c, _ in spec)
            for c, m in spec: g[(mx - c[0], c[1], c[2])] = m
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0, fitness_mode='forward',
                              friction=SS, materials='cheney2013', floor_contact='voxelyze')
        e.load_robot(g)
        t = time.time()
        c0 = np.array(e.get_position())
        for _ in range(int(0.25 / e.default_timestep)): e.step()
        d = (np.array(e.get_position()) - c0) / e.voxel_size
        print(f"{name:<16}{'mirror' if mirror else 'orig':<7} disp voxels ({d[0]:+.3f},{d[1]:+.3f},{d[2]:+.3f})  "
              f"{time.time()-t:.1f}s  div={e.diverged()}")
