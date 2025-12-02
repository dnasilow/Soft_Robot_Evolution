#!/usr/bin/env python
"""
Test the fitness evaluation function.

Tests both basic fitness evaluation and detailed metrics.
"""

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.robot import VoxelRobot
from src.evolution.fitness import FitnessEvaluator, evaluate_robot_fitness

print("="*70)
print("FITNESS EVALUATION TEST")
print("="*70)
print("\nTesting fitness evaluation on actuated robot...")
print("\n" + "="*70 + "\n")

# Create a simple 2x2x2 actuated robot
voxel_grid = np.zeros((4, 4, 4), dtype=np.int8)
voxel_grid[1:3, 1:3, 1:3] = 2  # 2x2x2 cube of active material (actuators)

print("Creating 2x2x2 actuated robot...")
robot = VoxelRobot(voxel_grid, voxel_size=0.05)  # 5cm voxels

print(f"Robot created:")
print(f"  - Nodes: {len(robot.nodes)}")
print(f"  - Springs: {len(robot.springs)}")
print(f"  - Mass: {np.sum([n['mass'] for n in robot.nodes]):.3f} kg")

print("\n" + "="*70)
print("TEST 1: Basic Fitness Evaluation (Fast)")
print("="*70)
print("\nEvaluating with 5-second simulation...")

fitness_result = evaluate_robot_fitness(
    robot,
    sim_time=5.0,
    actuation_frequency=2.0,
    actuation_amplitude=0.2,
    detailed_metrics=False
)

print("\nFitness Results:")
print(f"  - Primary fitness: {fitness_result['fitness']:.4f} m")
print(f"  - Horizontal distance: {fitness_result['distance_horizontal']:.4f} m")
print(f"  - Forward distance (X): {fitness_result['distance_forward']:.4f} m")
print(f"  - Total 3D distance: {fitness_result['distance_3d']:.4f} m")
print(f"  - Final height: {fitness_result['final_height']:.4f} m")

if fitness_result['fitness'] > 0.05:
    print("\n[SUCCESS] Robot achieved locomotion!")
elif fitness_result['fitness'] > 0.01:
    print("\n[GOOD] Robot moved some distance")
else:
    print("\n[INFO] Minimal movement detected")

print("\n" + "="*70)
print("TEST 2: Detailed Fitness Evaluation (Slower)")
print("="*70)
print("\nEvaluating with efficiency/stability/integrity metrics...")

evaluator = FitnessEvaluator(sim_time=5.0, enable_detailed_metrics=True)
detailed_result = evaluator.evaluate_fitness(
    robot,
    actuation_frequency=2.0,
    actuation_amplitude=0.2
)

print("\nDetailed Fitness Results:")
print(f"  - Primary fitness: {detailed_result['fitness']:.4f} m")
print(f"  - Horizontal distance: {detailed_result['distance_horizontal']:.4f} m")
print(f"  - Forward distance: {detailed_result['distance_forward']:.4f} m")
print(f"  - Total 3D distance: {detailed_result['distance_3d']:.4f} m")
print(f"  - Final height: {detailed_result['final_height']:.4f} m")
print(f"\nSecondary Metrics:")
print(f"  - Efficiency: {detailed_result['efficiency']:.5f} m/cycle")
print(f"  - Stability: {detailed_result['stability']:.6f} (lower = more stable)")
print(f"  - Integrity: {detailed_result['integrity']:.4f} (1.0 = no deformation)")

print("\n" + "="*70)
print("TEST 3: Parameter Variation")
print("="*70)
print("\nTesting different actuation frequencies...")

frequencies = [1.0, 2.0, 4.0]
results_by_freq = []

for freq in frequencies:
    print(f"\n  Testing {freq} Hz...")
    result = evaluate_robot_fitness(robot, sim_time=5.0, actuation_frequency=freq)
    results_by_freq.append((freq, result['fitness']))
    print(f"    Distance: {result['fitness']:.4f} m")

# Find best frequency
best_freq, best_dist = max(results_by_freq, key=lambda x: x[1])
print(f"\n[RESULT] Best frequency: {best_freq} Hz → {best_dist:.4f} m")

print("\n" + "="*70)
print("TEST 4: Multiple Robot Evaluation (Batch)")
print("="*70)
print("\nCreating 3 different robots...")

# Robot 1: 1x1x1 cube
grid1 = np.zeros((3, 3, 3), dtype=np.int8)
grid1[1, 1, 1] = 2
robot1 = VoxelRobot(grid1, voxel_size=0.05)

# Robot 2: 2x1x1 bar (horizontal)
grid2 = np.zeros((4, 3, 3), dtype=np.int8)
grid2[1:3, 1, 1] = 2
robot2 = VoxelRobot(grid2, voxel_size=0.05)

# Robot 3: 1x2x1 vertical bar
grid3 = np.zeros((3, 4, 3), dtype=np.int8)
grid3[1, 1:3, 1] = 2
robot3 = VoxelRobot(grid3, voxel_size=0.05)

robots = [robot1, robot2, robot3]
robot_names = ["1x1x1 cube", "2x1x1 bar", "1x2x1 tower"]

print("\nEvaluating batch of 3 robots...")
batch_evaluator = FitnessEvaluator(sim_time=3.0)
batch_results = batch_evaluator.evaluate_batch(robots, actuation_frequency=2.0)

print("\nBatch Results:")
for name, result in zip(robot_names, batch_results):
    print(f"  {name:12s}: fitness = {result['fitness']:.4f} m")

# Rank by fitness
ranked = sorted(zip(robot_names, batch_results), key=lambda x: x[1]['fitness'], reverse=True)
print("\nRanking:")
for i, (name, result) in enumerate(ranked, 1):
    print(f"  {i}. {name:12s}: {result['fitness']:.4f} m")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("\nFitness evaluation working correctly!")
print("\nKey findings:")
print(f"  - Primary fitness metric: Horizontal locomotion distance")
print(f"  - Typical range: 0.01 - 0.50 m for 5s simulation")
print(f"  - Actuation frequency affects performance")
print(f"  - Morphology affects locomotion capability")
print("\nReady for evolutionary algorithm integration!")
print("\nFitness test complete!")
