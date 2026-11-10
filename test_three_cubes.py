#!/usr/bin/env python
"""Test 3 connected cubes falling - tests multi-voxel structures"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.visualization.viewer import RobotViewer

print("="*70)
print("THREE CONNECTED CUBES TEST")
print("="*70)
print("\nCreating 3 cubes in a horizontal line...")
print("This tests:")
print("  - Multi-voxel structures")
print("  - Inter-voxel spring connections")
print("  - Structural integrity during fall")
print("  - Bending/flexing behavior")
print("\n" + "="*70 + "\n")

# Create a 3-cube horizontal line
# Grid will be 5x3x3 to fit 3 cubes side by side
voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)

# Place 3 cubes in a row (X direction)
# Each cube is 1x1x1 in voxel space
voxel_grid[1, 1, 1] = 3  # Cube 1 (left)
voxel_grid[2, 1, 1] = 3  # Cube 2 (center)
voxel_grid[3, 1, 1] = 3  # Cube 3 (right)

print("Voxel layout (side view):")
print("  X X X  (3 cubes in a line)")
print("\nCreating robot with 1m voxels...")

robot = VoxelRobot(voxel_grid, voxel_size=1.0)

print(f"\nRobot created:")
print(f"  - Total voxels: 3")
print(f"  - Nodes: {len(robot.nodes)}")
print(f"  - Springs: {len(robot.springs)}")
print(f"  - Total mass: {np.sum([n['mass'] for n in robot.nodes]):.1f} kg")

# Expected: 3 cubes * 8 nodes = 24 nodes
# Expected: 3 cubes * 28 springs + inter-cube connections
expected_mass = 3 * 160  # 3 cubes * 160kg each
print(f"  - Expected mass: ~{expected_mass} kg")

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=200)
physics_engine.reset()
physics_engine.add_robot(robot)

# Lift above ground
physics_engine.d_positions[:physics_engine.num_nodes, 1] += 1.0

# Get initial state
initial_pos = physics_engine.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)

print(f"\nInitial center of mass: [{initial_com[0]:.2f}, {initial_com[1]:.2f}, {initial_com[2]:.2f}]")

# Check initial structure dimensions
min_pos = np.min(initial_pos, axis=0)
max_pos = np.max(initial_pos, axis=0)
dimensions = max_pos - min_pos

print(f"\nStructure dimensions:")
print(f"  - X (width): {dimensions[0]:.2f} m (should be ~3m for 3 cubes)")
print(f"  - Y (height): {dimensions[1]:.2f} m (should be ~1m)")
print(f"  - Z (depth): {dimensions[2]:.2f} m (should be ~1m)")

# Create viewer
print("\n" + "="*70)
print("STARTING SIMULATION")
print("="*70)
print("\nSimulating for 10 seconds...")
print("Watch the 3-cube structure fall!")
print("\nControls:")
print("  - Left-drag: Rotate view")
print("  - Scroll: Zoom")
print("  - R: Reset camera")
print("  - ESC: Exit")
print("\n" + "="*70 + "\n")

viewer = RobotViewer(width=1280, height=720)

# Simulation
timestep = 0.001
sim_time = 0.0
max_sim_time = 10.0
physics_steps_per_frame = 10

last_print = 0.0
y_history = []

running = True
while running and sim_time < max_sim_time:
    # Physics
    for _ in range(physics_steps_per_frame):
        physics_engine.step(timestep)
        sim_time += timestep

    # Get state
    positions = physics_engine.get_positions()
    springs = robot.get_springs()
    com = robot.get_center_of_mass(positions)

    y_history.append(com[1])

    # Print stats every second
    if sim_time - last_print >= 1.0:
        fall_dist = initial_com[1] - com[1]

        # Check structure dimensions
        current_min = np.min(positions, axis=0)
        current_max = np.max(positions, axis=0)
        current_dims = current_max - current_min

        # Check for bending/deformation
        width_change = abs(current_dims[0] - dimensions[0])

        status = "falling"
        if len(y_history) > 100:
            recent_change = max(y_history[-100:]) - min(y_history[-100:])
            if recent_change < 0.01:
                status = "settled"

        print(f"t={sim_time:.1f}s: Y={com[1]:.3f}m, fall={fall_dist:.3f}m, width={current_dims[0]:.2f}m, [{status}]")
        last_print = sim_time

    # Render
    if not viewer.render(positions, springs):
        print("\nViewer closed by user")
        running = False
        break

    viewer.clock.tick(60)

# Final analysis
final_pos = physics_engine.get_positions()
final_com = robot.get_center_of_mass(final_pos)
total_fall = initial_com[1] - final_com[1]

# Final dimensions
final_min = np.min(final_pos, axis=0)
final_max = np.max(final_pos, axis=0)
final_dims = final_max - final_min

print("\n" + "="*70)
print("SIMULATION COMPLETE")
print("="*70)

print(f"\nInitial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")
print(f"Final COM:   [{final_com[0]:.3f}, {final_com[1]:.3f}, {final_com[2]:.3f}]")
print(f"Fall distance: {total_fall:.3f} m")

print(f"\nStructure deformation:")
print(f"  Initial width (X): {dimensions[0]:.3f} m")
print(f"  Final width (X):   {final_dims[0]:.3f} m")
print(f"  Change: {abs(final_dims[0] - dimensions[0]):.3f} m ({abs(final_dims[0] - dimensions[0])/dimensions[0]*100:.1f}%)")

print(f"\n  Initial height (Y): {dimensions[1]:.3f} m")
print(f"  Final height (Y):   {final_dims[1]:.3f} m")
print(f"  Change: {abs(final_dims[1] - dimensions[1]):.3f} m ({abs(final_dims[1] - dimensions[1])/dimensions[1]*100:.1f}%)")

print("\n" + "="*70)
print("EVALUATION")
print("="*70)

# Check if structure maintained integrity
width_deformation = abs(final_dims[0] - dimensions[0]) / dimensions[0]
height_deformation = abs(final_dims[1] - dimensions[1]) / dimensions[1]

if width_deformation < 0.1 and height_deformation < 0.1:
    print("[SUCCESS] Structure maintained integrity (<10% deformation)")
elif width_deformation < 0.2 and height_deformation < 0.2:
    print("[OK] Structure slightly deformed but stable (<20% deformation)")
else:
    print(f"[INFO] Structure deformed: width {width_deformation*100:.1f}%, height {height_deformation*100:.1f}%")

# Check if it behaves like connected structure
expected_free_fall = 0.5 * 9.81 * 10**2  # 490.5m
spring_effectiveness = (1 - total_fall / expected_free_fall) * 100

print(f"\nSpring effectiveness: {spring_effectiveness:.1f}%")
print(f"  (How much springs resisted fall vs free fall)")

if spring_effectiveness > 99:
    print("  [EXCELLENT] Springs are very strong")
elif spring_effectiveness > 95:
    print("  [GOOD] Springs working well")
else:
    print(f"  [INFO] Structure fell {total_fall:.2f}m")

print("\nThree-cube test complete!")
