"""Test TRUE parallel GPU evaluation"""
import numpy as np
import time
import pickle
from src.physics.robot import VoxelRobot
from src.physics.true_parallel_evaluator import TrueParallelBatchEvaluator

print("="*70)
print("TRUE PARALLEL GPU EVALUATION TEST")
print("="*70)

# Create evaluator with TRUE parallelism
evaluator = TrueParallelBatchEvaluator(
    actuation_cycles=5,
    actuation_freq=1.0,
    timestep=0.001
)

# Create 10 test robots
print(f"\nCreating 10 random test robots...")
test_robots = []

np.random.seed(42)  # Reproducible

for i in range(10):
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
    # Random structure
    for _ in range(np.random.randint(5, 12)):
        x, y, z = np.random.randint(1, 4, 3)
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])

    robot = VoxelRobot(voxel_grid, voxel_size=0.01)
    test_robots.append(robot)
    print(f"  Robot {i+1}: {len(robot.nodes)} nodes, {len(robot.springs)} springs")

# No controllers (passive robots for testing)
test_controllers = [None] * 10

# Benchmark
print(f"\n" + "="*70)
print("RUNNING BENCHMARK")
print("="*70)

start_time = time.perf_counter()
fitness_scores = evaluator.evaluate_batch(test_robots, test_controllers)
elapsed = time.perf_counter() - start_time

# Results
print(f"\n" + "="*70)
print("RESULTS")
print("="*70)

robots_per_second = 10 / elapsed
speedup_vs_old = elapsed / 276.09  # Old system took 276 seconds

print(f"\nPerformance:")
print(f"  Evaluation time: {elapsed:.2f} seconds")
print(f"  Throughput: {robots_per_second:.2f} robots/second")
print(f"  Speedup vs old system: {1/speedup_vs_old:.1f}x")

print(f"\nFitness scores:")
for i, score in enumerate(fitness_scores):
    print(f"  Robot {i+1}: {score:.4f}")

print(f"\nStatistics:")
print(f"  Best: {np.max(fitness_scores):.4f}")
print(f"  Mean: {np.mean(fitness_scores):.4f}")
print(f"  Worst: {np.min(fitness_scores):.4f}")

# Save best robot
best_idx = np.argmax(fitness_scores)
best_robot = test_robots[best_idx]
best_genome = best_robot.voxel_grid

print(f"\n" + "="*70)
print("SAVING BEST ROBOT")
print("="*70)
print(f"\nBest robot: #{best_idx+1}")
print(f"  Fitness: {fitness_scores[best_idx]:.4f}")
print(f"  Nodes: {len(best_robot.nodes)}")
print(f"  Springs: {len(best_robot.springs)}")

with open('best_robot.pkl', 'wb') as f:
    pickle.dump(best_genome, f)

print(f"\n  Saved to: best_robot.pkl")
print(f"\n  Visualize with: python visualize_saved_robot.py")

# Validation
print(f"\n" + "="*70)
print("VALIDATION")
print("="*70)

checks_passed = 0
total_checks = 4

if elapsed < 60:
    print(f"  [PASS] Fast evaluation: {elapsed:.1f}s < 60s")
    checks_passed += 1
else:
    print(f"  [FAIL] Too slow: {elapsed:.1f}s")

if robots_per_second > 0.1:
    print(f"  [PASS] Good throughput: {robots_per_second:.2f} robots/s")
    checks_passed += 1
else:
    print(f"  [FAIL] Low throughput: {robots_per_second:.2f} robots/s")

if speedup_vs_old < 1.0:
    speedup_factor = 1 / speedup_vs_old
    print(f"  [PASS] Speedup achieved: {speedup_factor:.1f}x faster!")
    checks_passed += 1
else:
    print(f"  [FAIL] No speedup vs old system")

if all(not np.isnan(f) and not np.isinf(f) for f in fitness_scores):
    print(f"  [PASS] All fitness values valid")
    checks_passed += 1
else:
    print(f"  [FAIL] Invalid fitness values")

print(f"\n  Total: {checks_passed}/{total_checks} checks passed")

# Evolution time estimates
print(f"\n" + "="*70)
print("EVOLUTION TIME ESTIMATES")
print("="*70)

print(f"\nBased on {robots_per_second:.2f} robots/second:")
print(f"\n  10 pop × 10 gen = 100 evals:")
print(f"    Time: {100 / robots_per_second / 60:.1f} minutes")

print(f"\n  50 pop × 20 gen = 1000 evals:")
print(f"    Time: {1000 / robots_per_second / 60:.1f} minutes")

print(f"\n  100 pop × 50 gen = 5000 evals:")
print(f"    Time: {5000 / robots_per_second / 60:.1f} minutes")

if checks_passed >= 3:
    print(f"\n  STATUS: TRUE parallel evaluation working!")
    print(f"  Ready for evolution experiments")
else:
    print(f"\n  STATUS: Issues detected, investigate")

print("="*70)
