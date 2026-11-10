#!/usr/bin/env python
"""Check if spring force direction is correct"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

# Create robot
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
physics_engine.reset()
physics_engine.add_robot(robot)

print("="*60)
print("SPRING FORCE DIRECTION TEST")
print("="*60)

# Get spring info
rest_lengths = cp.asnumpy(physics_engine.d_rest_lengths[:physics_engine.num_springs])
print(f"\nRest lengths: min={np.min(rest_lengths):.3f}m, max={np.max(rest_lengths):.3f}m")

# Get current spring lengths
pos = physics_engine.get_positions()
node1_indices = cp.asnumpy(physics_engine.d_spring_node1[:physics_engine.num_springs])
node2_indices = cp.asnumpy(physics_engine.d_spring_node2[:physics_engine.num_springs])

current_lengths = []
for i in range(physics_engine.num_springs):
    p1 = pos[node1_indices[i]]
    p2 = pos[node2_indices[i]]
    length = np.linalg.norm(p2 - p1)
    current_lengths.append(length)

current_lengths = np.array(current_lengths)
print(f"Current lengths: min={np.min(current_lengths):.3f}m, max={np.max(current_lengths):.3f}m")

# Calculate compression
compression = current_lengths - rest_lengths
print(f"\nCompression/extension:")
print(f"  Min: {np.min(compression):.3f}m ({'compressed' if np.min(compression) < 0 else 'extended'})")
print(f"  Max: {np.max(compression):.3f}m ({'compressed' if np.max(compression) < 0 else 'extended'})")
print(f"  Avg: {np.mean(compression):.3f}m")

if np.mean(compression) > 0:
    print("\n  STATUS: Springs are EXTENDED (stretched)")
    print("  This means springs will PULL nodes together (WRONG for pre-compression!)")
else:
    print("\n  STATUS: Springs are COMPRESSED (squeezed)")
    print("  This means springs will PUSH nodes apart (CORRECT for pre-compression!)")

# Now compute spring forces
physics_engine.d_forces[:physics_engine.num_nodes] = 0.0
physics_engine.compute_spring_forces_vectorized()

spring_forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
total_spring_force_y = np.sum(spring_forces[:, 1])

print(f"\nSpring forces:")
print(f"  Total Y-component: {total_spring_force_y:.1f} N")
print(f"  Gravity force: {-160 * 9.81:.1f} N")

if total_spring_force_y > 0:
    print(f"\n  PROBLEM: Springs push UPWARD (+Y direction)")
    print(f"  This is WRONG - compressed springs should resist compression")
else:
    print(f"\n  OK: Springs push DOWNWARD (-Y direction)")

print("="*60)
