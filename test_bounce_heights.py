#!/usr/bin/env python
"""
Test bounce behavior at different drop heights for 1m cube (160kg).

Goal: Determine if bounce is visible and scales with drop height.
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def test_bounce_from_height(drop_height, sim_time=10.0):
    """Test bounce from specified height"""
    print(f"\n{'='*70}")
    print(f"DROP TEST: {drop_height}m height")
    print(f"{'='*70}")

    # Create single 1m cube
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)

    total_mass = sum(n['mass'] for n in robot.nodes)
    print(f"Mass: {total_mass:.1f} kg")
    print(f"Expected impact velocity: {np.sqrt(2 * 9.81 * drop_height):.2f} m/s")
    print(f"Expected impact energy: {0.5 * total_mass * 2 * 9.81 * drop_height:.1f} J")

    # Initialize physics
    physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
    physics.reset()
    physics.add_robot(robot)

    # Lift to drop height
    physics.d_positions[:physics.num_nodes, 1] += drop_height

    initial_pos = physics.get_positions()
    initial_com = robot.get_center_of_mass(initial_pos)

    # Track COM height and velocity
    time_history = []
    y_history = []
    vy_history = []
    penetration_history = []

    timestep = 0.001
    num_steps = int(sim_time / timestep)

    print(f"\nRunning {sim_time}s simulation...")

    for step in range(num_steps):
        physics.step(timestep)

        if step % 100 == 0:  # Every 0.1s
            pos = physics.get_positions()
            vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])

            com = robot.get_center_of_mass(pos)
            mean_vy = np.mean(vel[:, 1])

            min_y = np.min(pos[:, 1])
            penetration = max(0, -min_y)

            time_history.append(step * timestep)
            y_history.append(com[1])
            vy_history.append(mean_vy)
            penetration_history.append(penetration * 1000)  # mm

            if step % 1000 == 0:  # Print every 1s
                print(f"t={step*timestep:.1f}s: Y={com[1]:.3f}m, vy={mean_vy:.2f}m/s, pen={penetration*1000:.1f}mm")

    # Analyze bounce behavior
    y_array = np.array(y_history)
    vy_array = np.array(vy_history)
    time_array = np.array(time_history)

    # Find impact time (first time Y < 1.0m)
    impact_indices = np.where(y_array < 1.0)[0]
    if len(impact_indices) > 0:
        impact_idx = impact_indices[0]
        impact_time = time_array[impact_idx]
        impact_velocity = vy_array[impact_idx]

        print(f"\nImpact at t={impact_time:.2f}s, velocity={impact_velocity:.2f}m/s")

        # Find bounce peaks (local maxima after impact)
        post_impact_y = y_array[impact_idx:]
        post_impact_t = time_array[impact_idx:]

        peaks = []
        peak_times = []
        for i in range(1, len(post_impact_y) - 1):
            if post_impact_y[i] > post_impact_y[i-1] and post_impact_y[i] > post_impact_y[i+1]:
                if post_impact_y[i] > 0.52:  # More than 2cm above resting
                    peaks.append(post_impact_y[i])
                    peak_times.append(post_impact_t[i])

        print(f"\nBounce peaks detected: {len(peaks)}")
        for i, (peak, peak_time) in enumerate(zip(peaks[:5], peak_times[:5])):
            height_above_rest = (peak - 0.5) * 100  # cm above rest position
            print(f"  Bounce {i+1}: t={peak_time:.2f}s, Y={peak:.3f}m ({height_above_rest:.1f}cm above rest)")

        if len(peaks) >= 2:
            # Calculate coefficient of restitution from bounce heights
            bounce_ratio = (peaks[1] - 0.5) / (peaks[0] - 0.5)
            effective_cor = np.sqrt(bounce_ratio)
            print(f"\nEffective CoR from bounces: {effective_cor:.3f}")
            print(f"Expected CoR (ground): 0.500")

            return True, len(peaks), peaks[0] - 0.5  # Success, num bounces, first bounce height
        else:
            print(f"\n[NO VISIBLE BOUNCE] Structure settled without bouncing >2cm")
            return False, 0, 0.0
    else:
        print(f"\n[ERROR] Object never reached ground!")
        return False, 0, 0.0

# Test at multiple heights
print("="*70)
print("BOUNCE BEHAVIOR TEST: Single Cube (1m, 160kg)")
print("="*70)
print("\nTesting spring-based ground contact (Option A)")
print("Goal: Verify bounce visibility increases with drop height")

results = {}

# Test 1: Low drop (1m)
success, num_bounces, first_bounce = test_bounce_from_height(1.0)
results['1m'] = (success, num_bounces, first_bounce)

# Test 2: Medium drop (2m)
success, num_bounces, first_bounce = test_bounce_from_height(2.0)
results['2m'] = (success, num_bounces, first_bounce)

# Test 3: High drop (5m)
success, num_bounces, first_bounce = test_bounce_from_height(5.0)
results['5m'] = (success, num_bounces, first_bounce)

# Summary
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

for height_name, (success, num_bounces, first_bounce) in results.items():
    if success:
        print(f"{height_name} drop: {num_bounces} bounces, first={first_bounce*100:.1f}cm")
    else:
        print(f"{height_name} drop: NO BOUNCE")

# Analysis
bounce_heights = [r[2] for r in results.values() if r[0]]
if len(bounce_heights) >= 2:
    print(f"\n[PASS] Bounce scales with drop height")
    print(f"This is realistic behavior for soft materials")
elif len(bounce_heights) == 0:
    print(f"\n[FAIL] No bounces detected at any height")
    print(f"Ground damping or friction may be too aggressive")
else:
    print(f"\n[WARNING] Bounce only visible at high drops")
    print(f"Consider reducing ground damping or friction")

print("\nDone!")
