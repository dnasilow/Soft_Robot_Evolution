"""Test critical damping implementation - quick validation"""
import numpy as np
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

print("=" * 60)
print("CRITICAL DAMPING TEST")
print("=" * 60)

# Create simple 3-cube structure
voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
voxel_grid[2, 1, 1] = 3
voxel_grid[3, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=1.0)
print(f"\nRobot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Mass: {sum(n['mass'] for n in robot.nodes):.1f} kg")

# Initialize physics
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.0001)
physics.add_robot(robot)

# Drop from 5m height by modifying the internal GPU array directly
initial_positions = physics.get_positions()
initial_positions[:, 1] += 5.0
# Copy back to GPU
import cupy as cp
physics.d_positions[:len(initial_positions)] = cp.array(initial_positions)

print("\nSimulating 3-second drop test...")
print("Measuring width oscillation to check for jello wobble\n")

# Track oscillation
widths = []
times = []
max_y_positions = []

# Run for 3 seconds (30000 steps at dt=0.0001)
for step in range(30000):
    physics.step(0.0001)

    if step % 2000 == 0:  # Record every 0.2s
        pos = physics.get_positions()
        time = step * 0.0001
        times.append(time)
        max_y_positions.append(np.max(pos[:, 1]))

        # Measure width (X-axis extent)
        width = np.max(pos[:, 0]) - np.min(pos[:, 0])
        widths.append(width)

        # Get COM
        com = robot.get_center_of_mass(pos)

        if step % 10000 == 0:  # Print every 1.0s
            print(f"t={time:.1f}s: Y={com[1]:.2f}m, Width={width:.3f}m, Max_Y={max_y_positions[-1]:.2f}m")

print("\n" + "=" * 60)
print("OSCILLATION ANALYSIS")
print("=" * 60)

# Find post-bounce behavior (after t=1s)
post_bounce_start = 5  # Index for t=1.0s
if len(widths) > post_bounce_start:
    post_bounce_widths = np.array(widths[post_bounce_start:])
    width_mean = np.mean(post_bounce_widths)
    width_std = np.std(post_bounce_widths)
    width_range = np.max(post_bounce_widths) - np.min(post_bounce_widths)

    print(f"\nPost-bounce width statistics (t > 1.0s):")
    print(f"  Mean width: {width_mean:.3f}m")
    print(f"  Std deviation: {width_std:.3f}m")
    print(f"  Oscillation range: {width_range:.3f}m ({width_range*100:.1f}cm)")

    # Expected width for 3 cubes in a row: 3 voxels × 1m = 3m
    print(f"\n  Expected width (rest): 3.000m")
    print(f"  Deviation from rest: {abs(width_mean - 3.0)*100:.1f}cm")

    # Check if jello wobble is reduced
    if width_range < 0.10:
        print(f"\n✓ EXCELLENT: Oscillation < 10cm (very stable)")
    elif width_range < 0.18:
        print(f"\n✓ GOOD: Oscillation < 18cm (better than previous 27cm)")
    elif width_range < 0.27:
        print(f"\n⚠ MODERATE: Oscillation < 27cm (similar to damping=7.5)")
    else:
        print(f"\n✗ POOR: Oscillation > 27cm (worse than before)")

# Terminal velocity estimate
if len(max_y_positions) > 10:
    # Check velocity near end
    late_y = np.array(max_y_positions[-10:])
    late_times = np.array(times[-10:])

    if len(late_times) > 1:
        velocities = np.diff(late_y) / np.diff(late_times)
        avg_velocity = np.mean(np.abs(velocities))
        print(f"\nTerminal velocity (estimated): {avg_velocity:.2f} m/s")
        print(f"  Expected with damping=0.5: 19.6 m/s")
        print(f"  Previous with damping=7.5: 1.31 m/s")

print("\n" + "=" * 60)
