#!/usr/bin/env python
"""Debug: Test basic spring physics directly"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*60)
print("BASIC SPRING PHYSICS TEST")
print("="*60)

# Create robot
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3  # Single passive voxel
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
physics_engine.reset()
physics_engine.add_robot(robot)

# Lift cube
physics_engine.d_positions[:physics_engine.num_nodes, 1] += 1.0

print(f"\nInitial state:")
pos = physics_engine.get_positions()
com = robot.get_center_of_mass(pos)
print(f"  Center of mass: [{com[0]:.2f}, {com[1]:.2f}, {com[2]:.2f}]")

# Run 10 steps and track what's happening
print(f"\n{'Time':>6} {'Y_COM':>8} {'Fall':>8} {'Vel_Y':>8} {'SpringF_Y':>10} {'GravF_Y':>10}")
print("-" * 60)

initial_y = com[1]
for step in range(10):
    t = step * 0.001

    # Clear forces
    physics_engine.d_forces[:physics_engine.num_nodes] = 0.0

    # Compute spring forces
    physics_engine.compute_spring_forces_vectorized()
    spring_forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    spring_force_y = np.sum(spring_forces[:, 1])

    # Add gravity
    gravity_force = -np.sum(cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])) * 9.81

    # Get velocity before integration
    vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
    avg_vel_y = np.mean(vel[:, 1])

    # Run full step
    physics_engine.d_forces[:physics_engine.num_nodes] = 0.0
    physics_engine.step(0.001)

    # Get new position
    pos = physics_engine.get_positions()
    com = robot.get_center_of_mass(pos)
    fall = initial_y - com[1]

    print(f"{t:6.3f} {com[1]:8.3f} {fall:8.3f} {avg_vel_y:8.3f} {spring_force_y:10.1f} {gravity_force:10.1f}")

print("\nExpected behavior:")
print("  - Spring force should be ZERO initially (rest_length = current_length)")
print("  - Gravity force should be -1569N (160kg * 9.81)")
print("  - Cube should FALL (Y decreasing, velocity becoming negative)")
print("  - If cube RISES, springs are pushing upward (WRONG!)")
