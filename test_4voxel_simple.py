"""Simple demo: 4 voxels side-by-side on ground, each different material"""
import numpy as np
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine
from src.visualization.viewer import RobotViewer
import cupy as cp

print("="*70)
print("SIMPLE 4-VOXEL DEMO - Side by Side on Ground")
print("="*70)
print("\nPurpose: Clean demonstration of all 4 material types")
print("Structure: 4 voxels in a row along X-axis, sitting on ground")
print("="*70)

# Create simple 4-voxel structure
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)

# Place 4 voxels side-by-side along X-axis at ground level (Y=1)
# Centered in Z direction (Z=3,4 middle)
print("\nBuilding 4-voxel structure:")
print("  Position (X, Y, Z) | Material")
print("  " + "-"*50)

voxel_grid[2, 1, 3] = 1  # Active 0° (GREEN)
print("  (2, 1, 3)          | Material 1 - Active 0° (GREEN)")

voxel_grid[3, 1, 3] = 2  # Active 180° (RED)
print("  (3, 1, 3)          | Material 2 - Active 180° (RED)")

voxel_grid[4, 1, 3] = 3  # Soft passive (CYAN)
print("  (4, 1, 3)          | Material 3 - Soft passive (CYAN)")

voxel_grid[5, 1, 3] = 4  # Stiff passive (BLUE)
print("  (5, 1, 3)          | Material 4 - Stiff passive (BLUE)")

print(f"\nTotal: 4 voxels in a horizontal line")
print(f"Grid: 8×8×8 (using only 4 voxels)")

# Create robot
print(f"\nBuilding robot structure...")
robot = VoxelRobot(voxel_grid, voxel_size=0.01)

print(f"\nRobot structure:")
print(f"  Nodes: {len(robot.nodes)}")
print(f"  Springs: {len(robot.springs)}")

# Count each spring type
spring_counts = {1: 0, 2: 0, 3: 0, 4: 0}
for spring in robot.springs:
    if hasattr(spring['material'], 'is_actuated'):
        if spring['material'].is_actuated:
            if abs(spring['material'].actuation_phase) < 0.1:
                spring_counts[1] += 1  # Active 0°
            else:
                spring_counts[2] += 1  # Active 180°
        else:
            if spring['material'].young_modulus > 50000:
                spring_counts[4] += 1  # Stiff passive
            else:
                spring_counts[3] += 1  # Soft passive

print(f"\nSpring counts by material:")
print(f"  GREEN (Active 0°):      {spring_counts[1]} springs")
print(f"  RED (Active 180°):      {spring_counts[2]} springs")
print(f"  CYAN (Soft passive):    {spring_counts[3]} springs")
print(f"  BLUE (Stiff passive):   {spring_counts[4]} springs")

# Initialize physics
print(f"\n" + "="*70)
print("PHYSICS SIMULATION")
print("="*70)

physics = OptimizedCUDAPhysicsEngine(default_timestep=0.0005)
physics.add_robot(robot)

# Position robot on ground (already at Y=1)
initial_pos = physics.get_positions()
# Center in X and Z
initial_pos[:, 0] -= np.mean(initial_pos[:, 0])
initial_pos[:, 2] -= np.mean(initial_pos[:, 2])
# Place on ground
initial_pos[:, 1] -= np.min(initial_pos[:, 1]) - 0.005
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

initial_com = robot.get_center_of_mass(initial_pos)
print(f"\nInitial COM: ({initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f})")

# Create viewer
print(f"\n" + "="*70)
print("3D VISUALIZATION")
print("="*70)
print(f"\nYou should see:")
print(f"  - 4 voxels in a horizontal line")
print(f"  - From left to right: GREEN, RED, CYAN, BLUE springs")
print(f"  - Sitting on the ground grid")
print(f"  - Active voxels (GREEN/RED) will oscillate")
print(f"  - Passive voxels (CYAN/BLUE) stay static")
print(f"\nControls:")
print(f"  - Left-drag: Rotate view")
print(f"  - Scroll: Zoom")
print(f"  - R: Reset camera")
print(f"  - ESC: Exit")
print(f"\n" + "="*70 + "\n")

try:
    viewer = RobotViewer(width=1280, height=720)

    # Run simulation with visualization
    simulation_time = 5.0
    steps = int(simulation_time / 0.0005)
    physics_steps_per_frame = 5

    for step in range(steps):
        physics.step(0.0005)

        # Update viewer
        if step % physics_steps_per_frame == 0:
            positions = physics.get_positions()

            # Convert springs to format expected by viewer
            spring_data = {
                'indices': [],
                'is_actuator': [],
                'material': []
            }
            for spring in robot.springs:
                spring_data['indices'].append(spring['indices'])
                spring_data['is_actuator'].append(spring['is_actuator'])
                spring_data['material'].append(spring['material'])

            # Render
            if not viewer.render(positions, spring_data):
                print("\nViewer closed by user")
                break

        # Print progress every 0.5 seconds
        if step % 1000 == 0:  # Every 0.5s (1000 steps × 0.0005s)
            pos = physics.get_positions()
            com = robot.get_center_of_mass(pos)
            xz_disp = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
            time = step * 0.0005
            print(f"t={time:4.1f}s: COM=({com[0]:7.4f}, {com[1]:7.4f}, {com[2]:7.4f}), Disp={xz_disp:7.4f}m")

    import pygame
    pygame.quit()

except Exception as e:
    print(f"\nVisualization error: {e}")
    print(f"Falling back to text-only simulation...")

    # Text-only fallback
    for step in range(int(5.0 / 0.0005)):
        physics.step(0.0005)

        if step % 1000 == 0:
            pos = physics.get_positions()
            com = robot.get_center_of_mass(pos)
            xz_disp = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
            time = step * 0.0005
            print(f"t={time:4.1f}s: COM=({com[0]:7.4f}, {com[1]:7.4f}, {com[2]:7.4f}), Disp={xz_disp:7.4f}m")

# Final results
final_pos = physics.get_positions()
final_com = robot.get_center_of_mass(final_pos)
total_displacement = np.sqrt((final_com[0]-initial_com[0])**2 + (final_com[2]-initial_com[2])**2)

print(f"\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\nInitial COM: ({initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f})")
print(f"Final COM:   ({final_com[0]:.4f}, {final_com[1]:.4f}, {final_com[2]:.4f})")
print(f"\nXZ Displacement: {total_displacement:.4f}m ({total_displacement*100:.1f}cm)")
print(f"\nSimple 4-voxel demo complete!")
print(f"All 4 material types should be clearly visible with distinct colors.")
print("="*70)
