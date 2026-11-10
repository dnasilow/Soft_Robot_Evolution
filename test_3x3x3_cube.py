#!/usr/bin/env python
"""
Visual test: 3×3×3 cube structure (27 voxels)

This is a large soft robot to see how it behaves.
"""

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.visualization.viewer import RobotViewer

print("="*70)
print("3×3×3 CUBE TEST (27 voxels)")
print("="*70)

# Create 3×3×3 cube
voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
for x in range(1, 4):
    for y in range(1, 4):
        for z in range(1, 4):
            voxel_grid[x, y, z] = 3  # Soft passive material

robot = VoxelRobot(voxel_grid, voxel_size=1.0)

total_mass = sum(n['mass'] for n in robot.nodes)
print(f"\nRobot created:")
print(f"  Voxels: 27 (3×3×3)")
print(f"  Nodes: {len(robot.nodes)}")
print(f"  Springs: {len(robot.springs)}")
print(f"  Total mass: {total_mass:.1f} kg")
print(f"  Expected mass: ~4320 kg (27 voxels × 160 kg/voxel)")

# Initialize physics
physics = CUDAPhysicsEngine(max_nodes=500, max_springs=2000)
physics.reset()
physics.add_robot(robot)

# Lift 3m above ground
physics.d_positions[:physics.num_nodes, 1] += 3.0

initial_pos = physics.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)
print(f"\nInitial COM: [{initial_com[0]:.2f}, {initial_com[1]:.2f}, {initial_com[2]:.2f}]")

# Create viewer
viewer = RobotViewer(width=1280, height=720)

print(f"\n{'='*70}")
print("STARTING SIMULATION")
print("="*70)
print("\nWatch the 3×3×3 cube fall and bounce!")
print("\nControls:")
print("  Left-drag: Rotate view")
print("  Scroll: Zoom")
print("  R: Reset camera")
print("  1/2/3: Camera presets")
print("  ESC: Exit")
print("="*70)

timestep = 0.001
sim_time = 0.0
max_sim_time = 20.0
physics_steps_per_frame = 10

last_print_time = 0.0
print_interval = 1.0

y_history = []

running = True
while running and sim_time < max_sim_time:
    # Physics steps
    for _ in range(physics_steps_per_frame):
        physics.step(timestep)
        sim_time += timestep

    # Get state
    positions = physics.get_positions()
    springs = robot.get_springs()
    com = robot.get_center_of_mass(positions)

    y_history.append(com[1])

    # Print stats
    if sim_time - last_print_time >= print_interval:
        fall_distance = initial_com[1] - com[1]

        # Calculate structure dimensions
        x_extent = np.max(positions[:, 0]) - np.min(positions[:, 0])
        y_extent = np.max(positions[:, 1]) - np.min(positions[:, 1])
        z_extent = np.max(positions[:, 2]) - np.min(positions[:, 2])

        status = "falling" if com[1] > 1.5 else "settled"
        print(f"t={sim_time:.1f}s: Y={com[1]:.2f}m, fall={fall_distance:.2f}m, size={x_extent:.1f}×{y_extent:.1f}×{z_extent:.1f}m [{status}]")
        last_print_time = sim_time

    # Render
    if not viewer.render(positions, springs):
        print("\nViewer closed")
        running = False
        break

    viewer.clock.tick(60)

# Final stats
final_pos = physics.get_positions()
final_com = robot.get_center_of_mass(final_pos)
total_fall = initial_com[1] - final_com[1]

print(f"\n{'='*70}")
print("SIMULATION COMPLETE")
print("="*70)
print(f"Simulation time: {sim_time:.1f}s")
print(f"Initial Y: {initial_com[1]:.2f}m")
print(f"Final Y: {final_com[1]:.2f}m")
print(f"Total fall: {total_fall:.2f}m")

# Calculate final deformation
final_x = np.max(final_pos[:, 0]) - np.min(final_pos[:, 0])
final_y = np.max(final_pos[:, 1]) - np.min(final_pos[:, 1])
final_z = np.max(final_pos[:, 2]) - np.min(final_pos[:, 2])

initial_x = 3.0
initial_y = 3.0
initial_z = 3.0

deform_x = final_x - initial_x
deform_y = final_y - initial_y
deform_z = final_z - initial_z

print(f"\nStructure deformation:")
print(f"  X: {initial_x:.1f}m → {final_x:.1f}m (change: {deform_x:+.2f}m, {abs(deform_x)/initial_x*100:.1f}%)")
print(f"  Y: {initial_y:.1f}m → {final_y:.1f}m (change: {deform_y:+.2f}m, {abs(deform_y)/initial_y*100:.1f}%)")
print(f"  Z: {initial_z:.1f}m → {final_z:.1f}m (change: {deform_z:+.2f}m, {abs(deform_z)/initial_z*100:.1f}%)")

# Oscillation analysis
if len(y_history) > 10:
    settle_idx = len(y_history) // 2
    y_settled = np.array(y_history[settle_idx:])
    oscillation = np.max(y_settled) - np.min(y_settled)
    print(f"\nOscillation (last half): {oscillation*100:.1f}cm")

print("\nDone!")
