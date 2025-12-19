"""Test that cube falls normally with corrected damping"""
import numpy as np
import cupy as cp
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

print("="*60)
print("NORMAL FALLING TEST - Corrected Damping (1.2)")
print("="*60)

# Single cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=1.0)
print(f"\nRobot: Single cube, {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Mass: {sum(n['mass'] for n in robot.nodes):.1f} kg")
print(f"Spring damping (material 3): 1.2 (was 0.4, corrected from 10.0)")

# Initialize
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(robot)

# Drop from 2.5m (like test_visual_cube.py)
initial_pos = physics.get_positions()
initial_pos[:, 1] += 2.5
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print("\nSimulating 10s fall...")
print("Expected: Cube should fall, bounce, and settle near Y=0.5m\n")

for step in range(10000):  # 10s at dt=0.001
    physics.step(0.001)

    if step % 1000 == 0:  # Every 1s
        pos = physics.get_positions()
        com = robot.get_center_of_mass(pos)
        vel = cp.asnumpy(physics.d_velocities[:len(pos)])
        avg_vel = np.mean(np.linalg.norm(vel, axis=1))

        print(f"t={step*0.001:.1f}s: Y={com[1]:.2f}m, vel={avg_vel:.2f}m/s")

print("\n" + "="*60)
print("ANALYSIS")
print("="*60)

pos = physics.get_positions()
com = robot.get_center_of_mass(pos)
final_y = com[1]

print(f"\nInitial Y: 3.50m (cube center at 2.5m + 0.5m radius)")
print(f"Final Y: {final_y:.2f}m")
print(f"Fall distance: {3.50 - final_y:.2f}m")

if final_y < 1.0 and final_y > 0.3:
    print(f"\nSTATUS: SUCCESS - Cube fell and settled near ground!")
elif final_y > 3.0:
    print(f"\nSTATUS: FAILURE - Cube didn't fall (gained energy)")
elif final_y < 0.3:
    print(f"\nSTATUS: FAILURE - Cube fell through ground")
else:
    print(f"\nSTATUS: PARTIAL - Cube behavior unclear")

print("\n" + "="*60)
