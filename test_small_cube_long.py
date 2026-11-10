#!/usr/bin/env python
"""Test if small cube eventually falls with long simulation"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("LONG SMALL CUBE TEST (10 seconds real-time)")

# Create small cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=0.05)

# Initialize physics with DEFAULT timestep
physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
physics.reset()
physics.add_robot(robot)

# Lift to 1m height
physics.d_positions[:physics.num_nodes, 1] += 1.0

pos = physics.get_positions()
print(f"Initial COM: {robot.get_center_of_mass(pos)}")

# Run for 10 seconds with DEFAULT timestep (0.0001s)
for i in range(100000):  # 10 seconds / 0.0001s
    physics.step()  # Use default timestep

    if i % 10000 == 0:
        pos = physics.get_positions()
        vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
        com = robot.get_center_of_mass(pos)
        mean_vy = np.mean(vel[:, 1])
        print(f"t={i*0.0001:.1f}s: Y={com[1]:.4f}m, v_y={mean_vy:.4f}m/s")

pos = physics.get_positions()
print(f"Final COM: {robot.get_center_of_mass(pos)}")
print("Done!")
