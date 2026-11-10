"""Quick demo of a well-performing robot structure"""
import numpy as np
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine
import cupy as cp

print("="*70)
print("HIGH-PERFORMING ROBOT DEMO")
print("="*70)

# Create a layered structure that tends to perform well
voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)

# Layer 1: Active material (0 degrees) - will expand
voxel_grid[1:4, 1, 1:4] = 1

# Layer 2: Active material (180 degrees) - will contract
voxel_grid[1:4, 2, 1:4] = 2

# Top: Soft passive
voxel_grid[2, 3, 2] = 3

robot = VoxelRobot(voxel_grid, voxel_size=0.01)

print(f"\nRobot structure (layered design):")
print(f"  Nodes: {len(robot.nodes)}")
print(f"  Springs: {len(robot.springs)}")
print(f"  Actuators: {len([s for s in robot.springs if s['is_actuator']])}")

# Count materials
for i in range(1, 5):
    count = np.sum(voxel_grid == i)
    if count > 0:
        names = {1: "Active 0deg", 2: "Active 180deg", 3: "Soft passive", 4: "Stiff passive"}
        print(f"  Material {i} ({names[i]}): {count} voxels")

# Initialize physics
print(f"\nRunning 5-second simulation...")
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(robot)

# Start on ground
initial_pos = physics.get_positions()
initial_pos[:, 1] -= np.min(initial_pos[:, 1]) - 0.005
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

initial_com = robot.get_center_of_mass(initial_pos)

print(f"\nTime  | X-pos   | Y-pos   | Z-pos   | XZ-Dist")
print("-" * 50)

# Simulate
for step in range(5000):
    physics.step(0.001)

    if step % 500 == 0:
        pos = physics.get_positions()
        com = robot.get_center_of_mass(pos)
        xz_dist = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
        print(f"{step*0.001:4.1f}s | {com[0]:7.4f} | {com[1]:7.4f} | {com[2]:7.4f} | {xz_dist:7.4f}m")

# Results
final_pos = physics.get_positions()
final_com = robot.get_center_of_mass(final_pos)
displacement = np.sqrt((final_com[0]-initial_com[0])**2 + (final_com[2]-initial_com[2])**2)

body_size = robot.get_bounding_box_size()
body_length = max(body_size[0], 0.01)
fitness = displacement / (body_length * 5.0)

print(f"\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\nTotal XZ displacement: {displacement:.4f}m")
print(f"Body length: {body_length:.4f}m")
print(f"Estimated fitness: {fitness:.2f}")

if displacement > 0.01:
    print(f"\nRobot moved! The alternating active layers create wave-like motion.")
else:
    print(f"\nRobot barely moved (passive structure).")

print("="*70)
