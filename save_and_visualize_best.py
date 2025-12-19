"""Save robots from test, then visualize the best one"""
import numpy as np
import pickle
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

print("="*70)
print("RECREATE AND VISUALIZE BEST ROBOT")
print("="*70)

# Robot #6 had these specs from your output:
# Created 50 nodes, 308 springs, 140 actuators
# Fitness: 279.659924

# Let's recreate robots with the same seed
print("\nRecreating robots from test_evolution_quick.py...")
np.random.seed(None)  # Reset to get different robots each time

# Try different seeds to find one with 50 nodes, 308 springs
found = False
seed = 0
target_robot = None

while not found and seed < 1000:
    np.random.seed(seed)

    for robot_num in range(10):
        voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
        for _ in range(np.random.randint(5, 15)):
            x, y, z = np.random.randint(1, 4, 3)
            voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])

        robot = VoxelRobot(voxel_grid, voxel_size=0.01)

        # Check if this matches Robot #6 specs
        if len(robot.nodes) == 50 and len(robot.springs) == 308:
            print(f"\n✓ Found matching robot! (seed={seed}, robot_num={robot_num})")
            print(f"  Nodes: {len(robot.nodes)}")
            print(f"  Springs: {len(robot.springs)}")
            actuator_count = len([s for s in robot.springs if s['is_actuator']])
            print(f"  Actuators: {actuator_count}")

            if actuator_count == 140:
                found = True
                target_robot = robot
                target_grid = voxel_grid.copy()
                print(f"  ✓ Perfect match!")
                break

    seed += 1

if not found:
    print(f"\n⚠ Couldn't find exact match. Creating a similar high-performing robot...")
    # Create a robot with good structure
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
    # Create a layered structure (tends to perform well)
    voxel_grid[1:4, 1, 1:4] = 1  # Bottom layer (active)
    voxel_grid[1:4, 2, 1:4] = 2  # Middle layer (active opposite phase)
    voxel_grid[2, 3, 2] = 3      # Top (soft passive)

    target_robot = VoxelRobot(voxel_grid, voxel_size=0.01)
    target_grid = voxel_grid

# Save the robot
print(f"\nSaving robot structure...")
with open('best_robot.pkl', 'wb') as f:
    pickle.dump(target_grid, f)
print(f"  Saved to: best_robot.pkl")

# Analyze structure
print(f"\nRobot structure:")
voxel_types = {}
for i in range(1, 5):
    count = np.sum(target_grid == i)
    if count > 0:
        voxel_types[i] = count
        material_names = {
            1: "Active 0° (green)",
            2: "Active 180° (red)",
            3: "Soft passive (cyan)",
            4: "Stiff passive (blue)"
        }
        print(f"  Material {i} - {material_names[i]}: {count} voxels")

# Now run visualization
print(f"\n" + "="*70)
print("STARTING VISUALIZATION")
print("="*70)

# Initialize physics
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(target_robot)

# Set initial position
import cupy as cp
initial_pos = physics.get_positions()
initial_pos[:, 0] -= np.mean(initial_pos[:, 0])  # Center X
initial_pos[:, 2] -= np.mean(initial_pos[:, 2])  # Center Z
initial_pos[:, 1] -= np.min(initial_pos[:, 1]) - 0.005  # Place on ground
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print(f"\nInitial COM: Y={target_robot.get_center_of_mass(initial_pos)[1]:.4f}m")

# Simple text-based simulation (no pygame required)
print(f"\nRunning 5-second simulation (5 actuation cycles)...")
print(f"Time  | COM_X   | COM_Y   | COM_Z   | Displacement")
print("-" * 55)

initial_com = target_robot.get_center_of_mass(initial_pos)

for step in range(5000):
    physics.step(0.001)

    if step % 500 == 0:  # Print every 0.5 seconds
        pos = physics.get_positions()
        com = target_robot.get_center_of_mass(pos)
        displacement = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
        time = step * 0.001
        print(f"{time:4.1f}s | {com[0]:7.4f} | {com[1]:7.4f} | {com[2]:7.4f} | {displacement:7.4f}m")

# Final results
final_pos = physics.get_positions()
final_com = target_robot.get_center_of_mass(final_pos)
total_displacement = np.sqrt((final_com[0]-initial_com[0])**2 + (final_com[2]-initial_com[2])**2)

# Calculate fitness (similar to evolution)
body_size = target_robot.get_bounding_box_size()
body_length = max(body_size[0], 0.01)
fitness = total_displacement / (body_length * 5.0)  # displacement / (body_length * time)

print(f"\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\nInitial COM: ({initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f})")
print(f"Final COM:   ({final_com[0]:.4f}, {final_com[1]:.4f}, {final_com[2]:.4f})")
print(f"\nTotal XZ displacement: {total_displacement:.4f}m")
print(f"Body length: {body_length:.4f}m")
print(f"Estimated fitness: {fitness:.2f}")
print(f"\n(Robot #6 actual fitness: 279.66)")

if fitness > 100:
    print(f"\n✓ Good performance! Robot moved >100 body lengths")
elif fitness > 50:
    print(f"\n~ Moderate performance")
else:
    print(f"\n⚠ Low performance - robot didn't move much")

print(f"\n" + "="*70)
print("To visualize with 3D graphics, install pygame and run:")
print("  python test_visual_cube.py")
print("Or modify this script to use InteractiveViewer")
print("="*70)
