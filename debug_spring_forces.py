#!/usr/bin/env python
"""
Deep diagnostic: Identify which springs create upward forces causing floating.
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*70)
print("SPRING FORCE DIAGNOSTIC")
print("="*70)

# Create small 5cm cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=0.05)

print(f"\nRobot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Mass: {sum(n['mass'] for n in robot.nodes):.6f} kg")
print(f"Gravity force: {sum(n['mass'] for n in robot.nodes) * 9.81:.6f} N (downward)")

# Get node positions
node_positions = np.array([n['position'] for n in robot.nodes])
print(f"\nNode positions (Y-axis):")
print(f"  Min: {np.min(node_positions[:, 1]):.4f} m")
print(f"  Max: {np.max(node_positions[:, 1]):.4f} m")
print(f"  Range: {np.max(node_positions[:, 1]) - np.min(node_positions[:, 1]):.4f} m")

# Initialize physics WITHOUT gravity to isolate spring forces
physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
physics.reset()

# Temporarily disable gravity
original_gravity = physics.gravity
physics.gravity = 0.0

physics.add_robot(robot)

# Get initial spring forces (should be zero for neutral springs)
physics.compute_spring_forces_vectorized()

# Copy forces to CPU
spring_forces_gpu = physics.d_forces[:physics.num_nodes]
spring_forces = cp.asnumpy(spring_forces_gpu)

print(f"\nSpring forces (no gravity, equilibrium):")
print(f"  Total force X: {np.sum(spring_forces[:, 0]):.6f} N")
print(f"  Total force Y: {np.sum(spring_forces[:, 1]):.6f} N")
print(f"  Total force Z: {np.sum(spring_forces[:, 2]):.6f} N")

# Restore gravity and check net force
physics.gravity = original_gravity

# Manually compute gravity forces
gravity_forces = np.zeros_like(spring_forces)
masses = cp.asnumpy(physics.d_masses[:physics.num_nodes])
gravity_forces[:, 1] = -masses * physics.gravity

net_forces = spring_forces + gravity_forces

print(f"\nNet forces (springs + gravity):")
print(f"  Total X: {np.sum(net_forces[:, 0]):.6f} N")
print(f"  Total Y: {np.sum(net_forces[:, 1]):.6f} N")
print(f"  Total Z: {np.sum(net_forces[:, 2]):.6f} N")

if np.sum(net_forces[:, 1]) > 0.01:
    print(f"\n[FOUND BUG] Net UPWARD force: {np.sum(net_forces[:, 1]):.6f} N")
    print(f"  This exceeds gravity ({np.sum(gravity_forces[:, 1]):.6f} N)")
    print(f"  Spring forces sum: {np.sum(spring_forces[:, 1]):.6f} N")
elif np.sum(net_forces[:, 1]) < -0.01:
    print(f"\n[EXPECTED] Net downward force: {np.sum(net_forces[:, 1]):.6f} N")
else:
    print(f"\n[BALANCED] Net force ~zero: {np.sum(net_forces[:, 1]):.6f} N")

print("\nDone!")
