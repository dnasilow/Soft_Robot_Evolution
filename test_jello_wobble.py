"""Test jello wobble reduction with increased spring damping"""
import numpy as np
import cupy as cp
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

print("="*60)
print("JELLO WOBBLE TEST - Increased Spring Damping")
print("="*60)

# Create 3-cube horizontal structure (same as previous tests)
voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
voxel_grid[2, 1, 1] = 3
voxel_grid[3, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=1.0)
print(f"\nRobot: 3 cubes, {len(robot.nodes)} nodes, {len(robot.springs)} springs")
print(f"Mass: {sum(n['mass'] for n in robot.nodes):.1f} kg")
print(f"Spring damping (material 3): 10.0 (previously 0.4)")
print(f"Global velocity damping: 7.5 s^-1")

# Initialize
physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(robot)

# Drop from 5m
initial_pos = physics.get_positions()
initial_pos[:, 1] += 5.0
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print("\nSimulating 4s drop (4000 steps at dt=0.001s)...")
print("Tracking width oscillation to measure jello wobble\n")

widths = []
times = []

for step in range(4000):
    physics.step(0.001)

    if step % 200 == 0:  # Every 0.2s
        pos = physics.get_positions()
        time = step * 0.001

        # Width measurement
        width = np.max(pos[:, 0]) - np.min(pos[:, 0])
        widths.append(width)
        times.append(time)

        com = robot.get_center_of_mass(pos)

        if step % 1000 == 0:  # Print every 1s
            print(f"t={time:.1f}s: COM_Y={com[1]:.2f}m, Width={width:.3f}m")

print("\n" + "="*60)
print("RESULTS")
print("="*60)

# Analyze post-bounce oscillation (after t=1.5s)
post_bounce_idx = 8  # t=1.6s
if len(widths) > post_bounce_idx:
    post_widths = np.array(widths[post_bounce_idx:])
    mean_width = np.mean(post_widths)
    width_range = np.max(post_widths) - np.min(post_widths)

    print(f"\nWidth oscillation (t > 1.5s):")
    print(f"  Mean: {mean_width:.3f}m")
    print(f"  Range: {width_range:.3f}m ({width_range*100:.1f}cm)")
    print(f"  Expected rest width: 3.000m")

    print(f"\nComparison to previous results:")
    print(f"  Previous (damping=0.4, global=7.5): 18cm oscillation")
    print(f"  Previous (damping=0.4, global=5.0): 27cm oscillation")
    print(f"  Current (damping=10.0, global=7.5): {width_range*100:.1f}cm oscillation")

    if width_range < 0.10:
        print(f"\n  STATUS: EXCELLENT - Jello wobble reduced by >45%!")
    elif width_range < 0.15:
        print(f"\n  STATUS: GOOD - Noticeable improvement")
    elif width_range < 0.18:
        print(f"\n  STATUS: MODERATE - Similar to previous best")
    else:
        print(f"\n  STATUS: NO IMPROVEMENT")

print("\n" + "="*60)
