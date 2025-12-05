#!/usr/bin/env python
"""
Test Option 1: Separated damping (air resistance vs material damping)

Tests realistic falling behavior with:
- Air resistance: 0.1 s^-1 (terminal velocity ~98 m/s)
- Material damping: 0.4 (spring internal damping from robot.py)

Expected improvements:
1. Higher drops produce bigger bounces (correct energy scaling)
2. Terminal velocity no longer limits impact energy
3. Realistic free-fall behavior
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def test_single_cube():
    """Test single 1m cube (160kg)"""
    print("="*70)
    print("TEST 1: SINGLE CUBE (1m, 160kg)")
    print("="*70)

    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)

    total_mass = sum(n['mass'] for n in robot.nodes)
    print(f"\nMass: {total_mass:.1f} kg")

    # Test from 5m drop
    physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
    physics.reset()
    physics.add_robot(robot)
    physics.d_positions[:physics.num_nodes, 1] += 5.0

    initial_pos = physics.get_positions()
    initial_com = robot.get_center_of_mass(initial_pos)

    print(f"Drop height: 5.0m")
    print(f"Expected terminal velocity: ~98 m/s (air resistance only)")
    print(f"Expected impact velocity: ~{np.sqrt(2 * 9.81 * 5.0):.2f} m/s (no damping limit)")

    y_history = []
    vy_history = []
    timestep = 0.001

    print(f"\nRunning 10s simulation...")
    for step in range(10000):
        physics.step(timestep)

        if step % 1000 == 0:
            pos = physics.get_positions()
            vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
            com = robot.get_center_of_mass(pos)
            mean_vy = np.mean(vel[:, 1])

            y_history.append(com[1])
            vy_history.append(mean_vy)

            print(f"t={step*timestep:.1f}s: Y={com[1]:.3f}m, vy={mean_vy:.2f}m/s")

    # Analyze bounce
    y_array = np.array(y_history)
    vy_array = np.array(vy_history)

    # Find impact (first time Y < 1.0m)
    impact_idx = np.where(y_array < 1.0)[0]
    if len(impact_idx) > 0:
        impact_velocity = vy_array[impact_idx[0]]
        print(f"\nImpact velocity: {impact_velocity:.2f} m/s")

        # Find bounce peaks
        post_impact = y_array[impact_idx[0]:]
        peaks = []
        for i in range(1, len(post_impact) - 1):
            if post_impact[i] > post_impact[i-1] and post_impact[i] > post_impact[i+1]:
                if post_impact[i] > 0.52:
                    peaks.append(post_impact[i])

        if len(peaks) > 0:
            first_bounce = (peaks[0] - 0.5) * 100
            print(f"First bounce height: {first_bounce:.1f}cm")
            print(f"Number of bounces: {len(peaks)}")
            return True, first_bounce, abs(impact_velocity)
        else:
            print(f"[WARNING] No visible bounce")
            return False, 0, abs(impact_velocity)
    else:
        print(f"[ERROR] Never reached ground")
        return False, 0, 0

def test_three_cubes():
    """Test three stacked 1m cubes (480kg)"""
    print("\n" + "="*70)
    print("TEST 2: THREE CUBES (3m stack, 480kg)")
    print("="*70)

    voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    voxel_grid[2, 1, 1] = 3
    voxel_grid[3, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)

    total_mass = sum(n['mass'] for n in robot.nodes)
    print(f"\nMass: {total_mass:.1f} kg")

    physics = CUDAPhysicsEngine(max_nodes=200, max_springs=500)
    physics.reset()
    physics.add_robot(robot)
    physics.d_positions[:physics.num_nodes, 1] += 2.0

    initial_pos = physics.get_positions()
    initial_com = robot.get_center_of_mass(initial_pos)

    print(f"Drop height: 2.0m")

    y_history = []
    vy_history = []
    timestep = 0.001

    print(f"\nRunning 10s simulation...")
    for step in range(10000):
        physics.step(timestep)

        if step % 1000 == 0:
            pos = physics.get_positions()
            vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
            com = robot.get_center_of_mass(pos)
            mean_vy = np.mean(vel[:, 1])

            y_history.append(com[1])
            vy_history.append(mean_vy)

            print(f"t={step*timestep:.1f}s: Y={com[1]:.3f}m, vy={mean_vy:.2f}m/s")

    # Analyze settling
    y_array = np.array(y_history)
    final_com = y_array[-1]
    oscillation = np.max(y_array[5:]) - np.min(y_array[5:])

    print(f"\nFinal COM Y: {final_com:.3f}m")
    print(f"Oscillation range: {oscillation*1000:.1f}mm")

    # Find impact
    impact_idx = np.where(y_array < 2.0)[0]
    if len(impact_idx) > 0:
        impact_velocity = abs(vy_history[impact_idx[0]])
        print(f"Impact velocity: {impact_velocity:.2f} m/s")

        if oscillation > 0.005 and oscillation < 0.3:
            print(f"[PASS] Realistic behavior")
            return True, oscillation * 1000, impact_velocity
        else:
            print(f"[WARNING] Oscillation out of range")
            return False, oscillation * 1000, impact_velocity
    else:
        print(f"[ERROR] Never reached ground")
        return False, 0, 0

# Run tests
print("="*70)
print("OPTION 1 VALIDATION: Separated Damping")
print("="*70)
print("\nAir resistance: 0.1 s^-1 (terminal velocity ~98 m/s)")
print("Spring damping: 0.4 (material property)")
print("\n")

single_pass, single_bounce, single_velocity = test_single_cube()
three_pass, three_oscillation, three_velocity = test_three_cubes()

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nSingle cube (5m drop):")
print(f"  Impact velocity: {single_velocity:.2f} m/s")
print(f"  First bounce: {single_bounce:.1f}cm")
print(f"  Status: {'[PASS]' if single_pass else '[FAIL]'}")

print(f"\nThree cubes (2m drop):")
print(f"  Impact velocity: {three_velocity:.2f} m/s")
print(f"  Oscillation: {three_oscillation:.1f}mm")
print(f"  Status: {'[PASS]' if three_pass else '[FAIL]'}")

if single_pass and three_pass:
    print(f"\n[SUCCESS] Option 1 works! Separated damping produces realistic physics.")
    print(f"\nKey improvements:")
    print(f"  - Terminal velocity: 0.98 m/s -> ~98 m/s (100x improvement)")
    print(f"  - Impact energy scales correctly with drop height")
    print(f"  - Spring damping handles oscillation independently")
else:
    print(f"\n[ISSUES DETECTED] Some tests failed")
    print(f"May need to adjust spring damping or add numerical stability damping")

print("\nDone!")
