"""Visualize the best robot from test_evolution_quick.py"""
import numpy as np
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine
from src.visualization.viewer import InteractiveViewer

print("="*70)
print("BEST ROBOT VISUALIZATION - Robot #6")
print("="*70)

# Recreate Robot #6 (best fitness: 279.66)
# Set the same random seed to get the same robots
np.random.seed(42)  # Start with same seed as test

# Generate robots until we get to #6
for i in range(6):
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
    # Random 3D structure
    for _ in range(np.random.randint(5, 15)):
        x, y, z = np.random.randint(1, 4, 3)
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])

# This should be Robot #6
robot = VoxelRobot(voxel_grid, voxel_size=0.01)

print(f"\nRobot #6 (Best performer):")
print(f"  Nodes: {len(robot.nodes)}")
print(f"  Springs: {len(robot.springs)}")
print(f"  Actuators: {len([s for s in robot.springs if s['is_actuator']])}")
print(f"  Fitness: 279.66")

# Count voxel types
voxel_types = {}
for i in range(1, 5):
    count = np.sum(voxel_grid == i)
    if count > 0:
        voxel_types[i] = count
        material_names = {1: "Active 0°", 2: "Active 180°", 3: "Soft passive", 4: "Stiff passive"}
        print(f"  Material {i} ({material_names[i]}): {count} voxels")

# Initialize physics
print(f"\nInitializing physics simulation...")
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(robot)

# Set initial position (start on ground)
initial_pos = physics.get_positions()
# Center at origin, place on ground (Y=0.5 for 0.01m voxels)
initial_pos[:, 0] -= np.mean(initial_pos[:, 0])
initial_pos[:, 2] -= np.mean(initial_pos[:, 2])
initial_pos[:, 1] -= np.min(initial_pos[:, 1]) - 0.005  # Just above ground

import cupy as cp
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print(f"\nInitial position: Y={robot.get_center_of_mass(initial_pos)[1]:.4f}m")

# Create viewer
print(f"\nLaunching interactive viewer...")
print(f"\nControls:")
print(f"  - Left-drag mouse: Rotate view")
print(f"  - Scroll wheel: Zoom")
print(f"  - R key: Reset camera")
print(f"  - SPACE: Pause/Resume")
print(f"  - ESC: Exit")
print(f"\nThe robot will actuate with CPG-like oscillations (5 cycles = 5 seconds)")
print(f"Watch how it moves and deforms!")
print("="*70)

viewer = InteractiveViewer(
    physics_engine=physics,
    robot=robot,
    window_title="Best Robot Visualization (Fitness: 279.66)"
)

# Run simulation with visualization
steps_per_frame = 10  # 10 physics steps per frame
total_steps = 5000  # 5 seconds at 0.001s timestep
frames = total_steps // steps_per_frame

for frame in range(frames):
    # Physics steps
    for _ in range(steps_per_frame):
        physics.step(0.001)

    # Update viewer
    viewer.update()

    # Print progress every 100 frames
    if frame % 100 == 0:
        pos = physics.get_positions()
        com = robot.get_center_of_mass(pos)
        time = frame * steps_per_frame * 0.001
        print(f"t={time:.1f}s: COM=({com[0]:.3f}, {com[1]:.3f}, {com[2]:.3f})")

    # Check if window closed
    if viewer.should_close():
        break

viewer.close()

# Final statistics
final_pos = physics.get_positions()
final_com = robot.get_center_of_mass(final_pos)
initial_com = robot.get_center_of_mass(initial_pos)
displacement = np.linalg.norm(final_com[:2] - initial_com[:2])  # XZ plane

print(f"\n" + "="*70)
print("SIMULATION COMPLETE")
print("="*70)
print(f"\nInitial COM: ({initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f})")
print(f"Final COM: ({final_com[0]:.3f}, {final_com[1]:.3f}, {final_com[2]:.3f})")
print(f"XZ Displacement: {displacement:.3f}m")
print(f"Fitness (approx): {displacement / 0.01 / 5.0:.2f}")  # displacement / body_length / time
print("="*70)
