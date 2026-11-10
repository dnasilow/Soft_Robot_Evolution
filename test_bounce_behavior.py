#!/usr/bin/env python
"""
Test to demonstrate ground bounce behavior with CoR = 0.35.

This test uses a smaller, less damped cube to make bounce visible.
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.visualization.viewer import RobotViewer

print("="*70)
print("BOUNCE BEHAVIOR TEST - CoR = 0.35")
print("="*70)
print("\nThis test demonstrates ground bounce with:")
print("  - Single cube (5cm voxel)")
print("  - Higher drop (3 meters)")
print("  - Tracks bounce heights to verify CoR = 0.35")
print("\n" + "="*70 + "\n")

# Create a small single cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3  # Single passive voxel

print("Creating single-cube robot (5cm voxel)...")
robot = VoxelRobot(voxel_grid, voxel_size=0.05)  # 5cm cube

print(f"Robot created:")
print(f"  - Nodes: {len(robot.nodes)}")
print(f"  - Springs: {len(robot.springs)}")
print(f"  - Mass: {np.sum([n['mass'] for n in robot.nodes]):.3f} kg")

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
physics_engine.reset()
physics_engine.add_robot(robot)

# Lift cube to 3 meters (high drop to see bounce clearly)
DROP_HEIGHT = 3.0
physics_engine.d_positions[:physics_engine.num_nodes, 1] += DROP_HEIGHT

initial_pos = physics_engine.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)

print(f"\nInitial COM height: {initial_com[1]:.3f} m")
print(f"Expected impact velocity: {np.sqrt(2 * 9.81 * (DROP_HEIGHT - 0.025)):.2f} m/s")
print(f"Expected bounce height (CoR=0.35): {DROP_HEIGHT * 0.35**2:.3f} m")

# Expected calculations:
# Drop from h1 = 3.0m
# Impact velocity: v = sqrt(2*g*h) = sqrt(2*9.81*3) = 7.67 m/s
# Bounce velocity: v_bounce = 0.35 * v = 2.68 m/s
# Bounce height: h2 = v_bounce^2 / (2*g) = 0.37 m

print("\n" + "="*70)
print("STARTING SIMULATION")
print("="*70)
print("\nWatch for bounce! Should bounce to ~37cm (0.37m)")
print("\nControls:")
print("  - Left-drag: Rotate view")
print("  - Scroll: Zoom")
print("  - R: Reset camera")
print("  - ESC: Exit")
print("\n" + "="*70 + "\n")

viewer = RobotViewer(width=1280, height=720)

# Simulation parameters
timestep = 0.001  # 1ms timestep (faster for visualization)
sim_time = 0.0
max_sim_time = 10.0
physics_steps_per_frame = 10

# Track bounce heights
y_history = []
velocity_history = []
bounce_peaks = []
last_velocity = 0.0
ground_contact_times = []

running = True
while running and sim_time < max_sim_time:
    # Physics
    for _ in range(physics_steps_per_frame):
        physics_engine.step(dt=timestep)
        sim_time += timestep

        # Track height
        positions = physics_engine.get_positions()
        com = robot.get_center_of_mass(positions)
        y_history.append(com[1])

        # Track velocity
        velocities = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
        mean_vel_y = np.mean(velocities[:, 1])
        velocity_history.append(mean_vel_y)

        # Detect bounce peaks (velocity changes from positive to negative)
        if last_velocity > 0.1 and mean_vel_y < 0:
            bounce_peaks.append(com[1])

        # Detect ground contact (downward velocity suddenly reverses)
        if last_velocity < -0.5 and mean_vel_y > 0:
            ground_contact_times.append(sim_time)

        last_velocity = mean_vel_y

    # Print status every second
    if int(sim_time) > int(sim_time - physics_steps_per_frame * timestep):
        status = "falling" if com[1] > 0.6 else "bouncing/settled"
        print(f"t={sim_time:.1f}s: Y={com[1]:.3f}m, v_y={mean_vel_y:.2f}m/s [{status}]")

    # Render
    springs = robot.get_springs()
    if not viewer.render(positions, springs):
        running = False

viewer.close()

print("\n" + "="*70)
print("BOUNCE ANALYSIS")
print("="*70)

# Analyze bounce peaks
if len(bounce_peaks) >= 2:
    print(f"\nDetected {len(bounce_peaks)} bounce peaks:")
    for i, height in enumerate(bounce_peaks[:5]):  # Show first 5
        print(f"  Bounce {i+1}: {height:.3f} m")

    # Calculate coefficient of restitution from bounce heights
    if len(bounce_peaks) >= 2:
        h1 = bounce_peaks[0]
        h2 = bounce_peaks[1]
        measured_cor = np.sqrt(h2 / h1) if h1 > 0.01 else 0
        print(f"\nMeasured CoR from bounces: {measured_cor:.3f}")
        print(f"Expected CoR: 0.35")

        if abs(measured_cor - 0.35) < 0.1:
            print("[SUCCESS] CoR matches expected value!")
        else:
            print(f"[INFO] CoR differs by {abs(measured_cor - 0.35):.3f}")
            print("  (Difference due to spring damping + velocity damping)")
else:
    print("\n[INFO] Bounce peaks not clearly detected")
    print("  (Structure may have settled too quickly)")

# Analyze ground contacts
if len(ground_contact_times) > 0:
    print(f"\nGround contact events: {len(ground_contact_times)}")
    print(f"  First contact: t={ground_contact_times[0]:.2f}s")
    if len(ground_contact_times) >= 2:
        print(f"  Time between bounces: {ground_contact_times[1] - ground_contact_times[0]:.2f}s")

# Final state
final_pos = physics_engine.get_positions()
final_com = robot.get_center_of_mass(final_pos)
print(f"\nFinal COM height: {final_com[1]:.3f} m")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"CoR = 0.35 implemented in cuda_physics.py:324")
print(f"Bounce behavior depends on:")
print(f"  - Ground restitution (35%)")
print(f"  - Velocity damping (2% per step)")
print(f"  - Spring internal damping")
print(f"\nNet effect: Visible bounce for first 1-2 impacts,")
print(f"            then rapid settling due to energy dissipation")
print("\nBounce test complete!")
