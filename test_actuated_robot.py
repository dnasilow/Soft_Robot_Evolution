#!/usr/bin/env python
"""Test actuated robot locomotion - manual setup without evolution framework"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.visualization.viewer import RobotViewer

print("="*70)
print("ACTUATED ROBOT LOCOMOTION TEST")
print("="*70)
print("\nThis tests:")
print("  - Actuated springs (sinusoidal contraction)")
print("  - Locomotion from actuation")
print("  - Visual playback of movement")
print("\n" + "="*70 + "\n")

# Create a simple 2x2x2 robot with some actuators
print("Creating 2x2x2 robot...")
voxel_grid = np.zeros((4, 4, 4), dtype=np.int8)

# Create a 2x2x2 block of actuated material (material type 2)
voxel_grid[1:3, 1:3, 1:3] = 2  # Material 2 = Active (has actuators)

robot = VoxelRobot(voxel_grid, voxel_size=0.05)  # 5cm voxels

print(f"Robot created:")
print(f"  - Nodes: {len(robot.nodes)}")
print(f"  - Springs: {len(robot.springs)}")

# Count actuators
num_actuators = sum(1 for spring in robot.springs if spring['is_actuator'])
print(f"  - Actuators: {num_actuators}")

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=500, max_springs=2000,
                                  actuation_frequency=2.0)  # 2 Hz actuation
physics_engine.reset()
physics_engine.add_robot(robot)

# Get initial position
initial_pos = physics_engine.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)

print(f"\nInitial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")

# Create viewer
print("\n" + "="*70)
print("STARTING SIMULATION")
print("="*70)
print("\nSimulating for 10 seconds...")
print("Watch the robot move with actuation!")
print("\nControls:")
print("  - Left-drag: Rotate view")
print("  - Scroll: Zoom")
print("  - R: Reset camera")
print("  - ESC: Exit")
print("\n" + "="*70 + "\n")

viewer = RobotViewer(width=1280, height=720)

# Simulation parameters
timestep = 0.001
sim_time = 0.0
max_sim_time = 10.0
physics_steps_per_frame = 10

running = True
last_print = 0.0

while running and sim_time < max_sim_time:
    # Run physics
    for _ in range(physics_steps_per_frame):
        physics_engine.step(timestep)
        sim_time += timestep

    # Get current state
    positions = physics_engine.get_positions()
    springs = robot.get_springs()
    com = robot.get_center_of_mass(positions)

    # Print progress every second
    if sim_time - last_print >= 1.0:
        # Calculate horizontal distance traveled
        horizontal_distance = np.sqrt((com[0] - initial_com[0])**2 + (com[2] - initial_com[2])**2)
        print(f"t={sim_time:.1f}s: COM=[{com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f}], distance={horizontal_distance:.4f}m")
        last_print = sim_time

    # Render
    if not viewer.render(positions, springs):
        print("\nViewer closed by user")
        running = False
        break

    viewer.clock.tick(60)  # 60 FPS

# Final statistics
final_pos = physics_engine.get_positions()
final_com = robot.get_center_of_mass(final_pos)

# Calculate distances
horizontal_distance = np.sqrt((final_com[0] - initial_com[0])**2 + (final_com[2] - initial_com[2])**2)
total_distance_3d = np.linalg.norm(final_com - initial_com)

print("\n" + "="*70)
print("SIMULATION COMPLETE")
print("="*70)
print(f"\nInitial COM: [{initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f}]")
print(f"Final COM:   [{final_com[0]:.4f}, {final_com[1]:.4f}, {final_com[2]:.4f}]")
print(f"\nHorizontal distance traveled: {horizontal_distance:.4f} m")
print(f"Total 3D distance: {total_distance_3d:.4f} m")
print(f"Vertical change: {final_com[1] - initial_com[1]:.4f} m")

print("\n" + "="*70)
print("EVALUATION")
print("="*70)

if horizontal_distance > 0.02:
    print(f"[SUCCESS] Robot moved {horizontal_distance*100:.2f} cm! Actuation is working!")
elif horizontal_distance > 0.005:
    print(f"[OK] Robot moved {horizontal_distance*100:.2f} cm - some locomotion")
else:
    print(f"[INFO] Robot moved only {horizontal_distance*100:.2f} cm - minimal movement")

print("\nActuated robot test complete!")
