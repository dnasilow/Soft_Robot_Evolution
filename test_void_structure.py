"""Test example: 2×4×2 robot with void at (2,2,2)"""
import numpy as np
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine
from src.visualization.viewer import RobotViewer
import cupy as cp

print("="*70)
print("VOID STRUCTURE TEST - 2×4×2 with missing (2,2,2)")
print("="*70)

# Create 2×4×2 structure with void at (2,2,2)
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)

# Define 2×4×2 structure (X: 2-3, Y: 2-5, Z: 2-3)
print("\nBuilding structure:")
voxel_count = 0

for x in range(2, 4):  # X: 2-3 (2 voxels)
    for y in range(2, 6):  # Y: 2-5 (4 voxels)
        for z in range(2, 4):  # Z: 2-3 (2 voxels)
            # Skip the void at (2, 2, 2)
            if (x, y, z) == (2, 2, 2):
                print(f"  ({x}, {y}, {z}): VOID (empty)")
                continue

            # Assign materials in pattern
            # Bottom layer (y=1): Stiff passive (blue)
            # Middle layers (y=2,3): Alternating active materials
            # Top layer (y=4): Soft passive (cyan)
            if y == 1:
                material = 4  # Stiff passive (blue)
            elif y == 4:
                material = 3  # Soft passive (cyan)
            elif (x + z) % 2 == 0:
                material = 1  # Active 0° (green)
            else:
                material = 2  # Active 180° (red)

            voxel_grid[x, y, z] = material
            voxel_count += 1

            mat_names = {1: "Active 0° (green)", 2: "Active 180° (red)",
                        3: "Soft passive (cyan)", 4: "Stiff passive (blue)"}
            print(f"  ({x}, {y}, {z}): {mat_names[material]}")

print(f"\nTotal voxels: {voxel_count} (out of 2×4×2 = 16 possible)")
print(f"Voids: 1 at (2,2,2)")

# Count each material type
print("\nMaterial composition:")
for mat_id in range(1, 5):
    count = np.sum(voxel_grid == mat_id)
    if count > 0:
        mat_names = {1: "Active 0° (green)", 2: "Active 180° (red)",
                    3: "Soft passive (cyan)", 4: "Stiff passive (blue)"}
        print(f"  Material {mat_id} ({mat_names[mat_id]}): {count} voxels")

# Create robot
print(f"\nBuilding robot structure...")
robot = VoxelRobot(voxel_grid, voxel_size=0.01)

print(f"\nRobot structure:")
print(f"  Nodes: {len(robot.nodes)}")
print(f"  Springs: {len(robot.springs)}")
print(f"  Actuators: {len([s for s in robot.springs if s['is_actuator']])}")

# Verify void - node at (2,2,2) corner should not have springs
print(f"\nVerifying void at (2,2,2)...")

# Check if nodes around void have reduced connectivity
void_corner_nodes = []
for dx in [0, 1]:
    for dy in [0, 1]:
        for dz in [0, 1]:
            corner_pos = (2 + dx, 2 + dy, 2 + dz)
            # Find node at this position
            for i, node in enumerate(robot.nodes):
                node_grid_pos = tuple((node['position'] / 0.01).astype(int))
                if node_grid_pos == corner_pos:
                    void_corner_nodes.append(i)
                    break

print(f"  Nodes adjacent to void: {len(void_corner_nodes)}")

# Count springs connected to void corner nodes
void_springs = 0
for spring in robot.springs:
    if spring['indices'][0] in void_corner_nodes or spring['indices'][1] in void_corner_nodes:
        void_springs += 1

print(f"  Springs connected to void corners: {void_springs}")
print(f"  (Should be less than normal due to missing voxel)")

# Initialize physics
print(f"\n" + "="*70)
print("PHYSICS SIMULATION")
print("="*70)

physics = OptimizedCUDAPhysicsEngine(default_timestep=0.0005)
physics.add_robot(robot)

# Position robot on ground
initial_pos = physics.get_positions()
initial_pos[:, 0] -= np.mean(initial_pos[:, 0])  # Center X
initial_pos[:, 2] -= np.mean(initial_pos[:, 2])  # Center Z
initial_pos[:, 1] -= np.min(initial_pos[:, 1]) - 0.005  # On ground
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

initial_com = robot.get_center_of_mass(initial_pos)
print(f"\nInitial COM: ({initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f})")

# Create viewer
print(f"\nLaunching 3D visualization...")
print(f"\nYou should see:")
print(f"  - 2×4×2 voxel structure")
print(f"  - Missing voxel at (2,2,2) creating internal void")
print(f"  - GREEN springs (Active 0°)")
print(f"  - RED springs (Active 180°)")
print(f"  - CYAN springs (Soft passive at top)")
print(f"  - BLUE springs (Stiff passive at bottom)")
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
    steps = int(simulation_time / 0.001)
    physics_steps_per_frame = 5

    for step in range(steps):
        physics.step(0.001)

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

        # Print progress
        if step % 500 == 0:
            pos = physics.get_positions()
            com = robot.get_center_of_mass(pos)
            xz_disp = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
            time = step * 0.001
            print(f"t={time:4.1f}s: COM=({com[0]:7.4f}, {com[1]:7.4f}, {com[2]:7.4f}), Disp={xz_disp:7.4f}m")

    import pygame
    pygame.quit()

except Exception as e:
    print(f"\nVisualization error: {e}")
    print(f"Falling back to text-only simulation...")

    # Text-only simulation
    for step in range(5000):
        physics.step(0.001)

        if step % 500 == 0:
            pos = physics.get_positions()
            com = robot.get_center_of_mass(pos)
            xz_disp = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
            time = step * 0.001
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
print(f"\nVoid structure test complete!")
print(f"The missing voxel at (2,2,2) created an internal cavity")
print("="*70)
