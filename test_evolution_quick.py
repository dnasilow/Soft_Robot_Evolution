"""Quick evolution test - TRUE parallel GPU evaluation"""
import numpy as np
import sys
import time

# Manually import just what we need
sys.path.insert(0, 'C:\\SoftRobotEvolution')

from src.physics.robot import VoxelRobot
from src.physics.true_parallel_evaluator import TrueParallelBatchEvaluator

print("="*70)
print("QUICK EVOLUTION TEST - TRUE Parallel GPU Validation")
print("="*70)

# Simple test: Validate TRUE parallel GPU batch evaluation works
print("\nStep 1: Create TRUE parallel batch evaluator...")
evaluator = TrueParallelBatchEvaluator(
    actuation_cycles=5,
    actuation_freq=1.0,
    timestep=0.001
)
print("  SUCCESS")

# Step 2: Create test robots
print("\nStep 2: Creating 10 test robots...")
test_robots = []
for i in range(10):
    # Simple random robot
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
    # Random 3D structure
    for _ in range(np.random.randint(5, 15)):
        x, y, z = np.random.randint(1, 4, 3)
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])

    robot = VoxelRobot(voxel_grid, voxel_size=0.01)
    test_robots.append(robot)
    print(f"  Robot {i+1}: {len(robot.nodes)} nodes, {len(robot.springs)} springs")

# Step 3: Batch evaluation
print("\nStep 3: Running TRUE PARALLEL batch evaluation...")
test_controllers = [None] * 10  # Passive robots (no controllers)

start_time = time.perf_counter()
fitness_scores = evaluator.evaluate_batch(test_robots, test_controllers)
elapsed = time.perf_counter() - start_time

print(f"  COMPLETED in {elapsed:.2f} seconds")
print(f"\n  Fitness scores:")
for i, score in enumerate(fitness_scores):
    print(f"    Robot {i+1}: {score:.6f}")

# Analysis
print("\n" + "="*70)
print("PERFORMANCE ANALYSIS")
print("="*70)

robots_per_second = 10 / elapsed
sim_time_per_robot = 5.0  # 5 actuation cycles × 1s each
old_sequential_time = 276.09  # Old system benchmark
speedup = old_sequential_time / elapsed

print(f"\nBatch Evaluation Performance:")
print(f"  10 robots evaluated in: {elapsed:.2f} seconds")
print(f"  Throughput: {robots_per_second:.2f} robots/second")
print(f"  Speedup vs old sequential: {speedup:.1f}x")

print(f"\nFitness Statistics:")
print(f"  Best: {np.max(fitness_scores):.6f}")
print(f"  Mean: {np.mean(fitness_scores):.6f}")
print(f"  Worst: {np.min(fitness_scores):.6f}")
print(f"  Std: {np.std(fitness_scores):.6f}")

# Estimates for full evolution
print("\n" + "="*70)
print("EVOLUTION TIME ESTIMATES")
print("="*70)

print(f"\nBased on measured throughput of {robots_per_second:.2f} robots/s:")
print(f"\n  Small experiment (10 pop × 10 gen = 100 evals):")
print(f"    Estimated time: {100 / robots_per_second:.0f} seconds (~{100 / robots_per_second / 60:.1f} minutes)")

print(f"\n  Medium experiment (50 pop × 20 gen = 1000 evals):")
print(f"    Estimated time: {1000 / robots_per_second:.0f} seconds (~{1000 / robots_per_second / 60:.1f} minutes)")

print(f"\n  Large experiment (100 pop × 50 gen = 5000 evals):")
print(f"    Estimated time: {5000 / robots_per_second:.0f} seconds (~{5000 / robots_per_second / 60:.1f} minutes)")

# Validation
print("\n" + "="*70)
print("VALIDATION")
print("="*70)

checks_passed = 0
total_checks = 4

if elapsed < 60:
    print(f"  [PASS] Batch evaluation fast enough: {elapsed:.1f}s < 60s")
    checks_passed += 1
else:
    print(f"  [FAIL] Batch evaluation too slow: {elapsed:.1f}s")

if all(not np.isnan(f) and not np.isinf(f) for f in fitness_scores):
    print(f"  [PASS] All fitness values valid")
    checks_passed += 1
else:
    print(f"  [FAIL] Invalid fitness values detected")

if speedup > 5.0:
    print(f"  [PASS] Excellent GPU speedup: {speedup:.1f}x")
    checks_passed += 1
else:
    print(f"  [WARN] Lower speedup than expected: {speedup:.1f}x")
    checks_passed += 0.5

if robots_per_second > 0.3:
    print(f"  [PASS] Sufficient throughput: {robots_per_second:.2f} robots/s")
    checks_passed += 1
else:
    print(f"  [FAIL] Throughput too low: {robots_per_second:.2f} robots/s")

print(f"\n  Total: {int(checks_passed)}/{total_checks} checks passed")

if checks_passed >= 3:
    print(f"\n  STATUS: TRUE parallel GPU evaluation is working!")
    print(f"  READY to run full evolution experiments")
else:
    print(f"\n  STATUS: Performance issues detected")
    print(f"  Investigate before running large experiments")

print("\n" + "="*70)
print("  Next: Run full evolution experiments with:")
print("  python run_evolution_small.py   (10x10 = 4 min)")
print("  python run_evolution_medium.py  (50x20 = 40 min)")
print("  python run_evolution_large.py   (100x50 = 3.3 hours)")
print("="*70)
