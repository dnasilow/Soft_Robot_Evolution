#!/usr/bin/env python
"""Debug why small cube doesn't fall"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*70)
print("SMALL CUBE DEBUG TEST")
print("="*70)

# Create small cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=0.05)
print(f"\nRobot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Mass: {sum(n['mass'] for n in robot.nodes):.6f} kg")

# Check spring properties
if len(robot.springs) > 0:
    s = robot.springs[0]
    print(f"\nSpring properties (first spring):")
    print(f"  Stiffness: {s['stiffness']:.2f} N/m")
    print(f"  Rest length: {s['rest_length']:.4f} m")
    print(f"  Damping: {s['damping']:.4f}")

# Initialize physics
physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
physics.reset()
physics.add_robot(robot)

# Lift to 1m height
physics.d_positions[:physics.num_nodes, 1] += 1.0

print(f"\nInitial positions:")
pos = physics.get_positions()
print(f"  Y range: [{np.min(pos[:, 1]):.4f}, {np.max(pos[:, 1]):.4f}]")
print(f"  COM: {robot.get_center_of_mass(pos)}")

# Run 1000 steps with diagnostics
print(f"\nRunning simulation...")
for i in range(100):
    physics.step(0.001)  # 1ms timestep

    if i % 10 == 0:
        pos = physics.get_positions()
        vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
        forces = cp.asnumpy(physics.d_forces[:physics.num_nodes])

        com = robot.get_center_of_mass(pos)
        mean_vy = np.mean(vel[:, 1])
        total_force_y = np.sum(forces[:, 1])

        print(f"Step {i*10:4d}: Y={com[1]:.4f}m, v_y={mean_vy:.3f}m/s, F_y={total_force_y:.4f}N")

print("\nDone!")
