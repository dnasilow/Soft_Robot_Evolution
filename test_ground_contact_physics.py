#!/usr/bin/env python
"""
Deep physics diagnostic: Ground contact behavior analysis.

This test investigates why:
1. No visible bounce despite CoR=0.5
2. Bottom surface (ground contact) doesn't oscillate
3. Top surface oscillates normally

Hypothesis: Ground friction or damping kills spring oscillations at boundary.
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*80)
print("GROUND CONTACT PHYSICS DIAGNOSTIC")
print("="*80)

# Create single 1m cube
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

print(f"\nRobot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Total mass: {sum(n['mass'] for n in robot.nodes):.2f} kg")

# Get node information
node_positions = np.array([n['position'] for n in robot.nodes])
node_masses = np.array([n['mass'] for n in robot.nodes])
print(f"\nNode Y positions (initial):")
print(f"  Min (bottom nodes): {np.min(node_positions[:, 1]):.4f} m")
print(f"  Max (top nodes): {np.max(node_positions[:, 1]):.4f} m")

# Identify bottom and top nodes based on RELATIVE position
y_min = np.min(node_positions[:, 1])
y_max = np.max(node_positions[:, 1])
y_range = y_max - y_min

bottom_node_mask = node_positions[:, 1] < (y_min + 0.1 * y_range)  # Bottom 10%
top_node_mask = node_positions[:, 1] > (y_max - 0.1 * y_range)     # Top 10%
bottom_indices = np.where(bottom_node_mask)[0]
top_indices = np.where(top_node_mask)[0]

print(f"\nBottom nodes (lowest 10%): {len(bottom_indices)} nodes at indices {bottom_indices}")
print(f"Top nodes (highest 10%): {len(top_indices)} nodes at indices {top_indices}")

# Initialize physics and drop from 2m
physics = CUDAPhysicsEngine(max_nodes=50, max_springs=100)
physics.reset()
physics.add_robot(robot)

# Lift to 2m height
physics.d_positions[:physics.num_nodes, 1] += 2.0

print(f"\n" + "="*80)
print("SIMULATION PARAMETERS")
print("="*80)
print(f"Gravity: {physics.gravity:.2f} m/s²")
print(f"Ground CoR: 0.5 (50% velocity retained)")
print(f"Ground friction: 0.8 (20% horizontal velocity loss per contact)")
print(f"Timestep: 0.001 s")
print(f"Simulation: 10 seconds")

# Track bottom vs top node behavior
bottom_y_history = []
top_y_history = []
bottom_vy_history = []
top_vy_history = []
ground_contact_count = []

print(f"\n" + "="*80)
print("RUNNING SIMULATION")
print("="*80)

timestep = 0.001
for step in range(10000):  # 10 seconds
    physics.step(timestep)

    if step % 100 == 0:  # Every 0.1 seconds
        pos = physics.get_positions()
        vel = cp.asnumpy(physics.d_velocities[:physics.num_nodes])

        # Bottom nodes
        bottom_y = np.mean(pos[bottom_indices, 1])
        bottom_vy = np.mean(vel[bottom_indices, 1])
        bottom_y_history.append(bottom_y)
        bottom_vy_history.append(bottom_vy)

        # Top nodes
        top_y = np.mean(pos[top_indices, 1])
        top_vy = np.mean(vel[top_indices, 1])
        top_y_history.append(top_y)
        top_vy_history.append(top_vy)

        # Count nodes in ground contact
        in_contact = np.sum(pos[:, 1] < 0.01)
        ground_contact_count.append(in_contact)

        if step % 1000 == 0:  # Print every second
            time = step * timestep
            print(f"t={time:.1f}s: Bottom Y={bottom_y:.4f}m (vy={bottom_vy:.3f}), "
                  f"Top Y={top_y:.4f}m (vy={top_vy:.3f}), Contact={in_contact} nodes")

print(f"\n" + "="*80)
print("OSCILLATION ANALYSIS")
print("="*80)

# Analyze oscillations after settling (last 5 seconds)
settle_idx = 50  # Start after 5 seconds
bottom_y_settled = np.array(bottom_y_history[settle_idx:])
top_y_settled = np.array(top_y_history[settle_idx:])

bottom_oscillation = np.max(bottom_y_settled) - np.min(bottom_y_settled)
top_oscillation = np.max(top_y_settled) - np.min(top_y_settled)

print(f"\nOscillation amplitude (last 5 seconds):")
print(f"  Bottom nodes: {bottom_oscillation*1000:.2f} mm")
print(f"  Top nodes: {top_oscillation*1000:.2f} mm")
print(f"  Ratio (top/bottom): {top_oscillation/bottom_oscillation if bottom_oscillation > 0 else float('inf'):.1f}x")

if top_oscillation > 5 * bottom_oscillation:
    print(f"\n[ASYMMETRY DETECTED] Top oscillates {top_oscillation/bottom_oscillation:.1f}x more than bottom!")
    print("This indicates ground contact is damping bottom springs excessively.")

# Analyze bounce behavior
bottom_y_array = np.array(bottom_y_history)
bottom_vy_array = np.array(bottom_vy_history)

# Find impact time (when bottom nodes first reach ground)
impact_idx = np.where(bottom_y_array < 0.1)[0]
if len(impact_idx) > 0:
    impact_time = impact_idx[0] * 0.1
    print(f"\n" + "="*80)
    print("BOUNCE ANALYSIS")
    print("="*80)
    print(f"Ground impact at t={impact_time:.2f}s")

    # Find local maxima after impact (bounce peaks)
    post_impact = bottom_y_array[impact_idx[0]:]
    peaks = []
    for i in range(1, len(post_impact)-1):
        if post_impact[i] > post_impact[i-1] and post_impact[i] > post_impact[i+1]:
            if post_impact[i] > 0.01:  # At least 1cm above ground
                peaks.append(post_impact[i])

    if len(peaks) >= 2:
        print(f"\nDetected {len(peaks)} bounce peaks:")
        for i, peak in enumerate(peaks[:5]):  # First 5 bounces
            print(f"  Bounce {i+1}: {peak:.4f} m ({peak*100:.1f} cm)")

        # Calculate actual CoR from bounces
        if len(peaks) >= 2:
            actual_cor = np.sqrt(peaks[1] / peaks[0])
            print(f"\nActual CoR from bounce ratio: {actual_cor:.3f}")
            print(f"Expected CoR: 0.500")
            print(f"Difference: {abs(actual_cor - 0.5)*100:.1f}%")
    else:
        print(f"\n[NO BOUNCE DETECTED] Bottom nodes did not bounce >1cm")
        print(f"Maximum height after impact: {np.max(post_impact)*100:.1f} cm")
        print("\nPossible causes:")
        print("  1. Damping coefficient too high (currently 10 s^-1)")
        print("  2. Ground friction killing vertical spring motion")
        print("  3. Spring damping preventing compression/expansion")
        print("  4. CoR applied incorrectly at ground boundary")
        peaks = []  # Define peaks for later use

print(f"\n" + "="*80)
print("GROUND CONTACT TIME ANALYSIS")
print("="*80)

contact_array = np.array(ground_contact_count)
avg_contact_post_settle = np.mean(contact_array[settle_idx:])
print(f"\nAverage nodes in contact (after settling): {avg_contact_post_settle:.1f}/{len(bottom_indices)}")

if avg_contact_post_settle >= len(bottom_indices) * 0.9:
    print(f"[CONSTANT CONTACT] Bottom nodes remain glued to ground")
    print("This prevents spring oscillation at the boundary.")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

if bottom_oscillation < 0.001:  # < 1mm
    print("\n1. Bottom surface is NOT oscillating (<1mm)")
    print("   → Ground contact is killing spring dynamics")
    print("   → Consider: Remove friction for nodes with Y≈0, or reduce to 0.95")

if top_oscillation > 5 * bottom_oscillation:
    print("\n2. Asymmetric damping detected (top vs bottom)")
    print("   → Springs should oscillate uniformly throughout structure")
    print("   → Issue: Ground friction at line 332-333 in cuda_physics.py")

if len(peaks) < 2:
    print("\n3. No visible bounce despite CoR=0.5")
    print("   → Damping (10 s^-1) may still be too aggressive")
    print("   → Consider: Reduce to 5 s^-1 or implement material-specific damping")

print("\nDone!")
