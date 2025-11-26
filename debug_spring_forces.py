#!/usr/bin/env python
"""Debug: Are spring forces actually being computed?"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def debug_spring_forces():
    """Check if spring forces are actually being computed"""
    print("="*60)
    print("SPRING FORCE DEBUG")
    print("="*60)

    # Create robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)

    # Initialize physics
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)

    print(f"\nSetup:")
    print(f"  Nodes: {physics_engine.num_nodes}")
    print(f"  Springs: {physics_engine.num_springs}")
    print(f"  Gravity: {physics_engine.gravity} m/s²")

    # Get initial state
    initial_pos = physics_engine.get_positions()
    print(f"\nInitial positions (first 3 nodes):")
    for i in range(min(3, len(initial_pos))):
        print(f"  Node {i}: [{initial_pos[i,0]:.3f}, {initial_pos[i,1]:.3f}, {initial_pos[i,2]:.3f}]")

    # Check spring rest lengths
    rest_lengths = cp.asnumpy(physics_engine.d_rest_lengths[:physics_engine.num_springs])
    stiffnesses = cp.asnumpy(physics_engine.d_stiffnesses[:physics_engine.num_springs])

    print(f"\nSpring properties:")
    print(f"  Rest lengths: min={np.min(rest_lengths):.3f}m, max={np.max(rest_lengths):.3f}m, avg={np.mean(rest_lengths):.3f}m")
    print(f"  Stiffnesses: min={np.min(stiffnesses):.1f}N/m, max={np.max(stiffnesses):.1f}N/m, avg={np.mean(stiffnesses):.1f}N/m")

    # Run ONE physics step and inspect forces
    print(f"\n{'='*60}")
    print("STEP-BY-STEP FORCE INSPECTION")
    print("="*60)

    # Clear forces
    physics_engine.d_forces[:physics_engine.num_nodes] = 0.0

    # Step 1: Compute spring forces
    print("\n1. Computing spring forces...")
    physics_engine.compute_spring_forces_vectorized()

    spring_forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    print(f"   Spring forces sum: {np.sum(np.abs(spring_forces)):.3f} N")
    print(f"   Spring forces Y-component: {np.sum(spring_forces[:, 1]):.3f} N")
    print(f"   Max node force: {np.max(np.linalg.norm(spring_forces, axis=1)):.3f} N")

    # Step 2: Add gravity
    print("\n2. Adding gravity...")
    physics_engine.d_forces[:physics_engine.num_nodes, 1] -= physics_engine.d_masses[:physics_engine.num_nodes] * physics_engine.gravity

    total_forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    print(f"   Total forces sum: {np.sum(np.abs(total_forces)):.3f} N")
    print(f"   Total forces Y-component: {np.sum(total_forces[:, 1]):.3f} N (should be ~-1569N)")
    print(f"   Expected gravity: {-np.sum(cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])) * 9.81:.1f} N")

    # Step 3: Integration
    print("\n3. Checking integration...")
    dt = 0.001
    masses = cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])
    accelerations = total_forces / masses[:, np.newaxis]

    print(f"   Average Y acceleration: {np.mean(accelerations[:, 1]):.3f} m/s²")
    print(f"   Expected (gravity only): -9.81 m/s²")

    if abs(np.mean(accelerations[:, 1]) + 9.81) > 0.5:
        print(f"   ⚠️ WARNING: Acceleration significantly different from gravity!")
        if np.mean(accelerations[:, 1]) > 0:
            print(f"   ❌ UPWARD acceleration detected! Springs pushing, not pulling!")

    # Now run a full step and check results
    print(f"\n{'='*60}")
    print("RUNNING FULL PHYSICS STEP")
    print("="*60)

    physics_engine.reset()
    physics_engine.add_robot(robot)

    initial_vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
    print(f"\nBefore step:")
    print(f"  Avg velocity Y: {np.mean(initial_vel[:, 1]):.3f} m/s")

    physics_engine.step(0.001)

    final_vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
    final_pos = physics_engine.get_positions()

    print(f"\nAfter step:")
    print(f"  Avg velocity Y: {np.mean(final_vel[:, 1]):.3f} m/s")
    print(f"  Velocity change Y: {np.mean(final_vel[:, 1]) - np.mean(initial_vel[:, 1]):.6f} m/s")
    print(f"  Expected change (gravity): {-9.81 * 0.001:.6f} m/s")

    if np.mean(final_vel[:, 1]) > 0:
        print(f"\n❌ CRITICAL BUG: Velocity is UPWARD after gravity step!")
        print(f"   This should be impossible - gravity always pulls down")

    print(f"\n{'='*60}")

if __name__ == "__main__":
    debug_spring_forces()
