"""Quick diagnostic test for critical damping"""
import numpy as np
import cupy as cp
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

# Create single cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=1.0)
print(f"Robot: {len(robot.nodes)} nodes, {len(robot.springs)} springs, {sum(n['mass'] for n in robot.nodes):.1f}kg")

# Initialize physics with LARGER timestep for speed
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)  # 10x larger!
physics.add_robot(robot)

# Drop from 2m
initial_pos = physics.get_positions()
initial_pos[:, 1] += 2.0
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print("\nRunning 2s simulation with dt=0.001s (2000 steps)...")

for step in range(2000):
    physics.step(0.001)

    if step % 200 == 0:
        pos = physics.get_positions()
        com = robot.get_center_of_mass(pos)
        max_y = np.max(pos[:, 1])

        # Check for explosion
        if np.any(np.isnan(pos)) or np.max(np.abs(pos)) > 100:
            print(f"\n✗ EXPLOSION at t={step*0.001:.2f}s!")
            print("  Critical damping may be too weak with low global damping")
            exit(1)

        print(f"t={step*0.001:.1f}s: COM_Y={com[1]:.2f}m, Max_Y={max_y:.2f}m")

print("\n✓ SUCCESS: No explosion!")
print("Critical damping implementation is stable")
