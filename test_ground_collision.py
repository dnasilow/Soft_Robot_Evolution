#!/usr/bin/env python
"""Debug: Test what happens at ground collision"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*60)
print("GROUND COLLISION TEST")
print("="*60)

# Create robot
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
physics_engine.reset()
physics_engine.add_robot(robot)

# Start with bottom nodes JUST above ground
# Robot spans Y=[0,2], so shift to Y=[0.01, 2.01]
physics_engine.d_positions[:physics_engine.num_nodes, 1] += 0.01

pos = physics_engine.get_positions()
print(f"\nInitial positions:")
for i in range(physics_engine.num_nodes):
    print(f"  Node {i}: Y = {pos[i, 1]:.4f} m")

print(f"\n{'Step':>4} {'Min_Y':>8} {'Max_Y':>8} {'COM_Y':>8} {'Vel_Y':>8} {'Below?':>7}")
print("-" * 55)

# Run simulation
for step in range(3000):  # Run long enough to hit ground
    physics_engine.step(0.001)

    if step % 100 == 0:
        pos = physics_engine.get_positions()
        com = robot.get_center_of_mass(pos)
        vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
        avg_vel_y = np.mean(vel[:, 1])

        min_y = np.min(pos[:, 1])
        max_y = np.max(pos[:, 1])
        below = "YES" if min_y < 0.001 else "NO"

        print(f"{step:4d} {min_y:8.4f} {max_y:8.4f} {com[1]:8.4f} {avg_vel_y:8.3f} {below:>7}")

print("\nExpected: Cube should fall and settle on ground")
print("If COM rises above initial, ground collision is adding energy!")
