#!/usr/bin/env python
"""
Measure spring elongation/compression in 3-cube structure.

Shows how much springs deform during simulation.
"""

import numpy as np
import cupy as cp
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

print("="*70)
print("SPRING ELONGATION TEST: 3 Cubes")
print("="*70)

# Create 3 cubes in a line
voxel_grid = np.zeros((5, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3
voxel_grid[2, 1, 1] = 3
voxel_grid[3, 1, 1] = 3
robot = VoxelRobot(voxel_grid, voxel_size=1.0)

print(f"\nRobot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")

# Get rest lengths
springs = robot.springs
rest_lengths = np.array([s['rest_length'] for s in springs])

print(f"Spring rest lengths:")
print(f"  Min: {np.min(rest_lengths):.4f}m")
print(f"  Max: {np.max(rest_lengths):.4f}m")
print(f"  Mean: {np.mean(rest_lengths):.4f}m")

# Initialize physics
physics = CUDAPhysicsEngine(max_nodes=200, max_springs=500)
physics.reset()
physics.add_robot(robot)
physics.d_positions[:physics.num_nodes, 1] += 2.0

# Track spring deformations
max_extensions = []
max_compressions = []

timestep = 0.001
print(f"\nRunning 10s simulation...")

for step in range(10000):
    physics.step(timestep)

    if step % 1000 == 0:
        # Calculate current spring lengths
        pos = physics.get_positions()

        current_lengths = []
        for spring in springs:
            indices = spring['indices']
            n1, n2 = indices[0], indices[1]
            p1 = pos[n1]
            p2 = pos[n2]
            length = np.linalg.norm(p2 - p1)
            current_lengths.append(length)

        current_lengths = np.array(current_lengths)

        # Calculate deformations
        deformations = current_lengths - rest_lengths
        extensions = deformations[deformations > 0]
        compressions = -deformations[deformations < 0]

        max_ext = np.max(extensions) if len(extensions) > 0 else 0
        max_comp = np.max(compressions) if len(compressions) > 0 else 0

        max_extensions.append(max_ext)
        max_compressions.append(max_comp)

        avg_deform = np.mean(np.abs(deformations))

        time = step * timestep
        print(f"t={time:.1f}s: max_ext={max_ext*100:.2f}cm, max_comp={max_comp*100:.2f}cm, avg={avg_deform*100:.2f}cm")

print(f"\n{'='*70}")
print("SPRING DEFORMATION SUMMARY")
print("="*70)

print(f"\nMaximum extensions: {max(max_extensions)*100:.2f}cm")
print(f"Maximum compressions: {max(max_compressions)*100:.2f}cm")

# Analysis
max_overall = max(max(max_extensions), max(max_compressions))
typical_spring_length = np.mean(rest_lengths)
deformation_percent = (max_overall / typical_spring_length) * 100

print(f"\nTypical spring rest length: {typical_spring_length:.4f}m")
print(f"Maximum deformation: {max_overall*100:.2f}cm ({deformation_percent:.1f}% of rest length)")

if deformation_percent < 5:
    print(f"\n[RIGID] Springs barely deform (<5%)")
    print("Structure behaves almost like rigid body")
elif deformation_percent < 15:
    print(f"\n[MODERATE] Springs deform moderately (5-15%)")
    print("Good balance of rigidity and flexibility")
elif deformation_percent < 30:
    print(f"\n[SOFT] Springs deform significantly (15-30%)")
    print("Structure is quite flexible")
else:
    print(f"\n[VERY SOFT] Springs deform excessively (>30%)")
    print("Structure may be too soft/unstable")

print("\nDone!")
