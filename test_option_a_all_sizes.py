#!/usr/bin/env python
"""
Test Option A (spring-based ground contact) across all object sizes.

Tests:
1. Small cube (5cm, 0.028kg) - previously floated
2. Single cube (1m, 160kg) - should work better with oscillation
3. Three cubes (3m, 480kg) - should maintain good behavior
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def test_robot(name, voxel_size, drop_height, sim_time=10.0):
    """Test a robot configuration"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")

    # Create single voxel
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=voxel_size)

    total_mass = sum(n['mass'] for n in robot.nodes)
    print(f"Robot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")
    print(f"Voxel size: {voxel_size}m, Total mass: {total_mass:.3f} kg")
    print(f"Gravity force: {total_mass * 9.81:.2f} N")

    # Initialize physics
    physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
    physics.reset()
    physics.add_robot(robot)

    # Lift to drop height
    physics.d_positions[:physics.num_nodes, 1] += drop_height

    initial_pos = physics.get_positions()
    initial_com = robot.get_center_of_mass(initial_pos)
    print(f"Drop height: {drop_height}m, Initial COM: Y={initial_com[1]:.4f}m")

    # Track metrics
    y_history = []
    vy_history = []
    penetration_history = []

    timestep = 0.001
    num_steps = int(sim_time / timestep)

    print(f"\nRunning {sim_time}s simulation (timestep={timestep}s)...")

    for step in range(num_steps):
        physics.step(timestep)

        if step % 1000 == 0:  # Every 1 second
            pos = physics.get_positions()
            vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])

            com = robot.get_center_of_mass(pos)
            mean_vy = np.mean(vel[:, 1])

            # Check ground penetration
            min_y = np.min(pos[:, 1])
            max_penetration = max(0, -min_y)  # Positive if below ground

            y_history.append(com[1])
            vy_history.append(mean_vy)
            penetration_history.append(max_penetration)

            time = step * timestep
            status = "falling" if com[1] > 0.6 else "settled"
            print(f"t={time:.1f}s: Y={com[1]:.4f}m, vy={mean_vy:.3f}m/s, penetration={max_penetration*1000:.2f}mm [{status}]")

    # Final analysis
    final_pos = physics.get_positions()
    final_com = robot.get_center_of_mass(final_pos)

    print(f"\n{'='*80}")
    print(f"RESULTS: {name}")
    print(f"{'='*80}")
    print(f"Initial COM Y: {initial_com[1]:.4f}m")
    print(f"Final COM Y: {final_com[1]:.4f}m")
    print(f"Net displacement: {final_com[1] - initial_com[1]:.4f}m")

    # Analyze settling behavior (last 5 seconds)
    settle_start = len(y_history) // 2
    y_settled = np.array(y_history[settle_start:])
    oscillation_range = np.max(y_settled) - np.min(y_settled)

    print(f"\nOscillation (last 5s): {oscillation_range*1000:.2f}mm")

    max_penetration = max(penetration_history)
    avg_penetration_settled = np.mean(penetration_history[settle_start:])
    print(f"Max ground penetration: {max_penetration*1000:.2f}mm")
    print(f"Avg penetration (settled): {avg_penetration_settled*1000:.2f}mm")

    # Check for floating bug
    if final_com[1] > initial_com[1] + 0.1:
        print(f"\n[X] [FLOATING BUG] Object rose {final_com[1] - initial_com[1]:.3f}m!")
        return False

    # Check for realistic behavior
    if oscillation_range < 0.001:  # < 1mm
        print(f"\n[!]  [NO OSCILLATION] Structure is too damped (<1mm range)")
        return False

    if max_penetration > 0.02:  # > 2cm
        print(f"\n[!]  [DEEP PENETRATION] Ground too soft (>{max_penetration*100:.1f}cm)")
        return False

    if oscillation_range > 0.2:  # > 20cm
        print(f"\n[!]  [EXCESSIVE BOUNCE] Structure too bouncy (>{oscillation_range*100:.1f}cm)")
        return False

    print(f"\n[OK] [PASS] Realistic physics behavior")
    return True

# Run all tests
print("="*80)
print("OPTION A VALIDATION: Spring-based Ground Contact")
print("="*80)
print("\nTesting across all object sizes to verify physics correctness...")

results = {}

# Test 1: Small cube (previously floated)
results['small'] = test_robot(
    name="Small Cube (5cm)",
    voxel_size=0.05,
    drop_height=1.0,
    sim_time=10.0
)

# Test 2: Single cube (reference case)
results['single'] = test_robot(
    name="Single Cube (1m)",
    voxel_size=1.0,
    drop_height=2.0,
    sim_time=10.0
)

# Test 3: Three cubes (large structure)
print(f"\n{'='*80}")
print(f"TEST: Three Cubes (3×1m)")
print(f"{'='*80}")

voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
voxel_grid[2, 1, 1] = 3
voxel_grid[3, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

total_mass = sum(n['mass'] for n in robot.nodes)
print(f"Robot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Total mass: {total_mass:.1f} kg")

physics = CUDAPhysicsEngine(max_nodes=200, max_springs=500)
physics.reset()
physics.add_robot(robot)
physics.d_positions[:physics.num_nodes, 1] += 2.0

initial_pos = physics.get_positions()
initial_com = robot.get_center_of_mass(initial_pos)

y_history = []
timestep = 0.001

print(f"\nRunning 10s simulation...")
for step in range(10000):
    physics.step(timestep)

    if step % 1000 == 0:
        pos = physics.get_positions()
        com = robot.get_center_of_mass(pos)
        y_history.append(com[1])

        vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])
        mean_vy = np.mean(vel[:, 1])

        min_y = np.min(pos[:, 1])
        penetration = max(0, -min_y) * 1000

        time = step * timestep
        print(f"t={time:.1f}s: Y={com[1]:.3f}m, vy={mean_vy:.2f}m/s, pen={penetration:.1f}mm")

final_pos = physics.get_positions()
final_com = robot.get_center_of_mass(final_pos)

y_array = np.array(y_history)
oscillation = np.max(y_array[5:]) - np.min(y_array[5:])

print(f"\nFinal COM Y: {final_com[1]:.3f}m")
print(f"Oscillation (last 5s): {oscillation*1000:.1f}mm")

if final_com[1] < initial_com[1] and oscillation > 0.001 and oscillation < 0.2:
    print(f"[OK] [PASS] Three cubes behave correctly")
    results['three'] = True
else:
    print(f"[X] [FAIL] Three cubes show issues")
    results['three'] = False

# Final summary
print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Small cube (5cm, 0.028kg): {'[OK] PASS' if results['small'] else '[X] FAIL'}")
print(f"Single cube (1m, 160kg): {'[OK] PASS' if results['single'] else '[X] FAIL'}")
print(f"Three cubes (3m, 480kg): {'[OK] PASS' if results['three'] else '[X] FAIL'}")

if all(results.values()):
    print(f"\n[OK] Option A: ALL TESTS PASSED")
    print(f"Spring-based ground contact works correctly for all object sizes!")
else:
    print(f"\n[!]  Option A: SOME TESTS FAILED")
    print(f"May need to adjust parameters or try Option B (friction reduction)")

print("\nDone!")
