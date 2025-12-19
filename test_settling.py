"""Test that cube settles to equilibrium with damping=1.2"""
import numpy as np
import cupy as cp
from src.physics.robot import VoxelRobot, MATERIALS
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

print("="*60)
print(f"SETTLING TEST - Damping={MATERIALS[3].damping}")
print("="*60)

# Single cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=1.0)
print(f"\nRobot: {len(robot.nodes)} nodes, mass={sum(n['mass'] for n in robot.nodes):.1f}kg")

physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(robot)

# Drop from 2.5m
initial_pos = physics.get_positions()
initial_pos[:, 1] += 2.5
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print("\nRunning 20s simulation to test settling...")
print("Expected: Cube should settle near Y=0.5m with low velocity\n")

y_history = []
v_history = []

for step in range(20000):  # 20s
    physics.step(0.001)

    if step % 1000 == 0:
        pos = physics.get_positions()
        vel = cp.asnumpy(physics.d_velocities[:len(pos)])

        com = robot.get_center_of_mass(pos)
        avg_vel = np.mean(np.linalg.norm(vel, axis=1))

        y_history.append(com[1])
        v_history.append(avg_vel)

        if step % 5000 == 0:
            print(f"t={step*0.001:.0f}s: Y={com[1]:.2f}m, vel={avg_vel:.2f}m/s")

print("\n" + "="*60)
print("SETTLING ANALYSIS")
print("="*60)

# Check last 5 seconds for settling
late_y = np.array(y_history[-5:])
late_v = np.array(v_history[-5:])

y_mean = np.mean(late_y)
y_std = np.std(late_y)
v_mean = np.mean(late_v)

print(f"\nLast 5 seconds (t=15-20s):")
print(f"  Mean Y: {y_mean:.2f}m")
print(f"  Y std dev: {y_std:.3f}m")
print(f"  Mean velocity: {v_mean:.2f}m/s")

print(f"\nExpected equilibrium: Y ≈ 0.5m (cube half-height above ground)")

if y_std < 0.1 and v_mean < 1.0:
    print(f"\n✓ SUCCESS: Cube has settled!")
    print(f"  Position stable (±{y_std*100:.0f}cm)")
    print(f"  Velocity low ({v_mean:.2f}m/s)")
elif v_mean > 5.0:
    print(f"\n✗ FAILURE: Cube still oscillating wildly")
    print(f"  Velocity too high ({v_mean:.2f}m/s)")
else:
    print(f"\n~ PARTIAL: Cube settling slowly")
    print(f"  May need longer simulation time")

print("\n" + "="*60)
