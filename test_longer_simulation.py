# test_longer_simulation.py - Run longer simulation to see equilibrium

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def test_equilibrium():
    """Run longer simulation to see if robot reaches equilibrium"""
    print("="*60)
    print("LONGER SIMULATION TEST - Finding Equilibrium")
    print("="*60)

    # Create robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3  # Single passive voxel
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)

    # Initialize physics
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)

    # Get initial state
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)

    print(f"\nInitial COM Y: {initial_com[1]:.4f} m")
    print(f"Robot mass: 160 kg")
    print(f"Gravity force: {160 * 9.81:.1f} N")
    print(f"\nRunning 1000 steps (1 second simulation)...\n")

    # Track positions over time
    times = []
    y_positions = []
    velocities = []

    timestep = 0.001
    num_steps = 1000  # 1 second

    for step in range(num_steps):
        # Record state every 10 steps
        if step % 100 == 0:
            pos = physics_engine.get_positions()
            com = robot.get_center_of_mass(pos)

            import cupy as cp
            vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
            avg_vel_y = np.mean(vel[:, 1])

            times.append(step * timestep)
            y_positions.append(com[1])
            velocities.append(avg_vel_y)

            print(f"t={step*timestep:.2f}s: Y={com[1]:.4f}m, vel={avg_vel_y:.3f}m/s, fall={initial_com[1]-com[1]:.4f}m")

        physics_engine.step(timestep)

    # Final state
    final_positions = physics_engine.get_positions()
    final_com = robot.get_center_of_mass(final_positions)

    print(f"\n{'='*60}")
    print("FINAL RESULTS:")
    print(f"Initial Y: {initial_com[1]:.4f} m")
    print(f"Final Y: {final_com[1]:.4f} m")
    print(f"Total fall: {initial_com[1] - final_com[1]:.4f} m")
    print(f"Expected free fall (1s): {0.5 * 9.81 * 1.0**2:.4f} m")

    if abs((initial_com[1] - final_com[1]) - 4.905) < 0.1:
        print(f"\n❌ Robot fell like free fall - springs NOT working!")
    elif (initial_com[1] - final_com[1]) < 0.1:
        print(f"\n✅ Robot settled quickly - springs ARE working!")
    else:
        print(f"\n⚠️ Robot fell {initial_com[1] - final_com[1]:.4f}m - check if reasonable")

if __name__ == "__main__":
    test_equilibrium()
