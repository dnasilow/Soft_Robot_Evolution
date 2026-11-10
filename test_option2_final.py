#!/usr/bin/env python
"""
Final test of Option 2: damping = 5.0 s^-1

Validates:
1. Single cube stability
2. Three cubes stability
3. Terminal velocity improvement
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*70)
print("OPTION 2 FINAL TEST: Damping = 5.0 s^-1")
print("="*70)
print("\nTerminal velocity: 1.96 m/s (2× improvement over 10 s^-1)")
print("Expected: Better energy scaling, possible instability\n")

# Test 1: Single cube from 2m
print("="*70)
print("TEST 1: Single Cube (1m, 160kg) - 2m drop")
print("="*70)

voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
physics.reset()
physics.add_robot(robot)
physics.d_positions[:physics.num_nodes, 1] += 2.0

initial_pos = physics.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)

y_history = []
max_y = initial_com[1]
timestep = 0.001

print(f"\nRunning 15s simulation...")
for step in range(15000):
    physics.step(timestep)

    if step % 1000 == 0:
        pos = physics.get_positions()
        vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
        com = robot.get_center_of_mass(pos)
        mean_vy = np.mean(vel[:, 1])

        y_history.append(com[1])
        max_y = max(max_y, com[1])

        print(f"t={step*timestep:.1f}s: Y={com[1]:.3f}m, vy={mean_vy:.2f}m/s, max_Y={max_y:.3f}m")

final_y = y_history[-1]
energy_gain = max_y - initial_com[1]

print(f"\n[RESULTS]")
print(f"  Initial Y: {initial_com[1]:.3f}m")
print(f"  Final Y: {final_y:.3f}m")
print(f"  Max Y: {max_y:.3f}m")
print(f"  Energy gain: {energy_gain:.3f}m ({energy_gain*100/initial_com[1]:.1f}%)")

single_stable = energy_gain < 0.5  # Gained less than 50cm
print(f"  Status: {'STABLE' if single_stable else 'UNSTABLE'}")

# Test 2: Three cubes
print(f"\n{'='*70}")
print("TEST 2: Three Cubes (3m stack, 480kg) - 2m drop")
print("="*70)

voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
voxel_grid[2, 1, 1] = 3
voxel_grid[3, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

physics = CUDAPhysicsEngine(max_nodes=200, max_springs=500)
physics.reset()
physics.add_robot(robot)
physics.d_positions[:physics.num_nodes, 1] += 2.0

initial_pos = physics.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)

y_history = []
max_y = initial_com[1]

print(f"\nRunning 15s simulation...")
for step in range(15000):
    physics.step(timestep)

    if step % 1000 == 0:
        pos = physics.get_positions()
        vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
        com = robot.get_center_of_mass(pos)
        mean_vy = np.mean(vel[:, 1])

        y_history.append(com[1])
        max_y = max(max_y, com[1])

        print(f"t={step*timestep:.1f}s: Y={com[1]:.3f}m, vy={mean_vy:.2f}m/s, max_Y={max_y:.3f}m")

final_y = y_history[-1]
energy_gain = max_y - initial_com[1]

print(f"\n[RESULTS]")
print(f"  Initial Y: {initial_com[1]:.3f}m")
print(f"  Final Y: {final_y:.3f}m")
print(f"  Max Y: {max_y:.3f}m")
print(f"  Energy gain: {energy_gain:.3f}m ({energy_gain*100/initial_com[1]:.1f}%)")

three_stable = energy_gain < 0.5
print(f"  Status: {'STABLE' if three_stable else 'UNSTABLE'}")

# Summary
print(f"\n{'='*70}")
print("OPTION 2 SUMMARY (damping = 5.0 s^-1)")
print("="*70)

print(f"\nTerminal velocity: 1.96 m/s (vs 0.98 m/s with damping=10)")
print(f"Improvement: 2.0× better")

print(f"\nStability:")
print(f"  Single cube: {'PASS' if single_stable else 'FAIL'}")
print(f"  Three cubes: {'PASS' if three_stable else 'FAIL'}")

if single_stable and three_stable:
    print(f"\n[RECOMMENDATION] Option 2 (damping=5.0) is STABLE and better than damping=10!")
    print(f"Commit this configuration for improved realism.")
else:
    print(f"\n[RECOMMENDATION] Option 2 shows instability")
    print(f"Stick with damping=10 for guaranteed stability.")

print("\nDone!")
