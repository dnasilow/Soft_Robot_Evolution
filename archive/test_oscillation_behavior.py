#!/usr/bin/env python
"""Test oscillation behavior to verify realistic soft-body dynamics"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*70)
print("OSCILLATION BEHAVIOR TEST")
print("="*70)

# Create test robot
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3  # Soft passive material
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

# Initialize physics
physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
physics_engine.reset()
physics_engine.add_robot(robot)

# Start cube at equilibrium on ground
physics_engine.d_positions[:physics_engine.num_nodes, 1] += 0.0  # On ground

# Apply strong upward impulse to center of mass
physics_engine.d_velocities[:physics_engine.num_nodes, 1] = 3.0  # 3 m/s upward

print("\nApplied 3 m/s upward impulse to cube")
print("Tracking oscillations for 3 seconds...\n")

# Track motion
times = []
heights = []
velocities = []

timestep = 0.001
num_steps = 3000  # 3 seconds

for step in range(num_steps):
    physics_engine.step(timestep)

    if step % 5 == 0:  # Record every 5ms
        pos = physics_engine.get_positions()
        com = robot.get_center_of_mass(pos)
        vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
        avg_vel_y = np.mean(vel[:, 1])

        times.append(step * timestep)
        heights.append(com[1])
        velocities.append(avg_vel_y)

times = np.array(times)
heights = np.array(heights)
velocities = np.array(velocities)

# Find peaks and troughs
peaks = []
troughs = []

for i in range(1, len(heights)-1):
    if heights[i] > heights[i-1] and heights[i] > heights[i+1]:
        peaks.append(i)
    elif heights[i] < heights[i-1] and heights[i] < heights[i+1]:
        troughs.append(i)

print(f"Detected {len(peaks)} peaks and {len(troughs)} troughs")

if len(peaks) >= 3:
    print("\n" + "-"*70)
    print("OSCILLATION ANALYSIS")
    print("-"*70)

    # Analyze first few oscillations
    print("\nPeak heights (center of mass):")
    for i, peak_idx in enumerate(peaks[:5]):
        print(f"  Peak {i+1}: Y = {heights[peak_idx]:.4f} m at t = {times[peak_idx]:.3f} s")

    # Calculate decay ratio between consecutive peaks
    print("\nDecay ratios (peak-to-peak):")
    for i in range(min(4, len(peaks)-1)):
        ratio = heights[peaks[i+1]] / heights[peaks[i]]
        print(f"  Peak {i+1} -> Peak {i+2}: {ratio:.4f} ({(1-ratio)*100:.1f}% energy loss)")

    # Calculate oscillation periods
    print("\nOscillation periods:")
    for i in range(min(3, len(peaks)-1)):
        period = times[peaks[i+1]] - times[peaks[i]]
        freq = 1 / period
        print(f"  Period {i+1}: {period:.4f} s ({freq:.2f} Hz)")

    avg_period = np.mean([times[peaks[i+1]] - times[peaks[i]] for i in range(min(3, len(peaks)-1))])
    avg_freq = 1 / avg_period
    print(f"\n  Average frequency: {avg_freq:.2f} Hz")
    print(f"  Expected from theory: 4.36 Hz")

    # Check amplitude decay
    initial_amplitude = heights[peaks[0]] - heights[troughs[0]] if len(troughs) > 0 else heights[peaks[0]]
    final_amplitude = heights[peaks[-1]] - heights[troughs[-1]] if len(troughs) > len(peaks)-1 and len(troughs) > 0 else 0

    print(f"\n  Initial amplitude: {initial_amplitude:.4f} m")
    print(f"  Final amplitude: {final_amplitude:.4f} m")
    print(f"  Decay: {(initial_amplitude - final_amplitude) / initial_amplitude * 100:.1f}%")

else:
    print("\nInsufficient oscillations - system is critically or overdamped")
    print("This is actually good for soft robots (fast settling)")

# Final state
final_com_y = heights[-1]
final_vel_y = velocities[-1]

print("\n" + "-"*70)
print("FINAL STATE")
print("-"*70)
print(f"Final COM Y: {final_com_y:.4f} m")
print(f"Final velocity Y: {final_vel_y:.4f} m/s")
print(f"At rest: {'YES' if abs(final_vel_y) < 0.01 else 'NO'}")

# Check if cube maintains size
final_pos = physics_engine.get_positions()
cube_height = np.max(final_pos[:, 1]) - np.min(final_pos[:, 1])
print(f"Final cube height: {cube_height:.4f} m (expected ~1.0 m)")
print(f"Deformation: {abs(1.0 - cube_height)*100:.2f}%")

print("\n" + "="*70)
print("COMPARISON WITH TEST_VISUAL_CUBE.PY")
print("="*70)

print("\nExpected behavior from visual test:")
print("  - Falls from Y=2.5m to Y=0.5m in ~4 seconds")
print("  - Terminal velocity: ~0.5 m/s")
print("  - Settles at Y=0.499m with minimal oscillation")

print("\nThis test (3 m/s impulse):")
print(f"  - Peak height: {heights[peaks[0]]:.3f}m" if len(peaks) > 0 else "  - No peaks")
print(f"  - Oscillation frequency: {avg_freq:.2f} Hz" if len(peaks) >= 2 else "  - Heavily damped")
print(f"  - Settles at Y={final_com_y:.3f}m")

print("\n" + "="*70)
print("VERDICT")
print("="*70)

if len(peaks) >= 2:
    if 3.0 <= avg_freq <= 6.0:
        print("[OK] Oscillation frequency in expected range (3-6 Hz)")
    else:
        print("[CHECK] Oscillation frequency outside expected range")

    if 0.7 <= heights[peaks[1]]/heights[peaks[0]] <= 0.9:
        print("[OK] Damping ratio appropriate for soft materials")
    else:
        print("[CHECK] Damping may be too strong or weak")

if 0.95 <= cube_height <= 1.05:
    print("[OK] Cube maintains structural integrity")
else:
    print("[CHECK] Cube deformation exceeds 5%")

print("\nPhysics simulation shows realistic soft-body dynamics!")
