"""Validate CUDA GPU acceleration is working and measure speedup"""
import numpy as np
import cupy as cp
import time
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

print("="*70)
print("CUDA GPU VALIDATION & BENCHMARK")
print("="*70)

# Create test robot (single cube)
voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
voxel_grid[1, 1, 1] = 3

robot = VoxelRobot(voxel_grid, voxel_size=1.0)
print(f"\nTest robot: {len(robot.nodes)} nodes, {len(robot.springs)} springs")

# Test 1: Verify GPU is being used
print("\n" + "="*70)
print("TEST 1: GPU DEVICE VERIFICATION")
print("="*70)

try:
    gpu = cp.cuda.Device(0)
    gpu_name = gpu.attributes.get('Name', 'Unknown')
    mem_info = gpu.mem_info
    total_mem_gb = mem_info[1] / 1e9
    free_mem_gb = mem_info[0] / 1e9

    print(f"\nGPU Device: {gpu_name}")
    print(f"Total Memory: {total_mem_gb:.2f} GB")
    print(f"Free Memory: {free_mem_gb:.2f} GB")
    print(f"CUDA Available: YES")

    # Test CuPy array creation
    test_array = cp.array([1, 2, 3])
    assert cp.get_array_module(test_array) == cp
    print(f"CuPy Arrays: Working on GPU")

    print("\n  STATUS: GPU is active and ready!")

except Exception as e:
    print(f"\n  ERROR: GPU not available: {e}")
    print("  Evolution will run on CPU (MUCH slower)")
    exit(1)

# Test 2: Physics simulation benchmark
print("\n" + "="*70)
print("TEST 2: PHYSICS SIMULATION BENCHMARK")
print("="*70)

physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
physics.add_robot(robot)

# Drop from 2m
initial_pos = physics.get_positions()
initial_pos[:, 1] += 2.0
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

print(f"\nRunning 1000 physics steps (1 second simulation)...")
print(f"Measuring GPU computation time...\n")

# Warmup (compile kernels)
for _ in range(10):
    physics.step(0.001)

# Reset
physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)
physics.d_velocities.fill(0)

# Benchmark
cp.cuda.Stream.null.synchronize()  # Ensure GPU is ready
start_time = time.perf_counter()

for step in range(1000):
    physics.step(0.001)

cp.cuda.Stream.null.synchronize()  # Wait for GPU to finish
elapsed = time.perf_counter() - start_time

steps_per_second = 1000 / elapsed
ms_per_step = elapsed * 1000 / 1000

print(f"Results:")
print(f"  Total time: {elapsed:.3f} seconds")
print(f"  Throughput: {steps_per_second:.0f} steps/second")
print(f"  Per-step: {ms_per_step:.2f} ms")

if steps_per_second > 5000:
    print(f"\n  STATUS: EXCELLENT - GPU acceleration working perfectly!")
elif steps_per_second > 1000:
    print(f"\n  STATUS: GOOD - GPU acceleration active")
else:
    print(f"\n  WARNING: Slow performance, may be running on CPU")

# Test 3: Batch evaluation benchmark
print("\n" + "="*70)
print("TEST 3: BATCH EVALUATION BENCHMARK")
print("="*70)

from src.physics.robot import TurboChargedBatchEvaluator

print(f"\nCreating batch evaluator for 10 robots...")
evaluator = TurboChargedBatchEvaluator(
    num_environments=30,
    actuation_cycles=5,
    actuation_freq=1.0
)

# Create 10 identical test robots
test_robots = [robot for _ in range(10)]
test_controllers = [None] * 10  # No controllers for passive robots

print(f"Evaluating 10 robots (5 second simulation each)...")
start_time = time.perf_counter()

fitness_scores = evaluator.evaluate_batch(test_robots, test_controllers)

elapsed = time.perf_counter() - start_time

robots_per_second = 10 / elapsed
total_sim_time = 10 * 5.0  # 10 robots × 5 seconds
speedup = total_sim_time / elapsed

print(f"\nResults:")
print(f"  Batch evaluation time: {elapsed:.2f} seconds")
print(f"  Robots/second: {robots_per_second:.2f}")
print(f"  Speedup vs sequential: {speedup:.1f}x")
print(f"  Fitness scores: min={np.min(fitness_scores):.4f}, max={np.max(fitness_scores):.4f}")

if speedup > 5:
    print(f"\n  STATUS: EXCELLENT - Batch processing highly efficient!")
elif speedup > 2:
    print(f"\n  STATUS: GOOD - Batch processing working")
else:
    print(f"\n  WARNING: Low speedup, check GPU utilization")

# Final summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

print(f"\nEstimated evolution performance:")
print(f"  10 robots × 10 generations = 100 evaluations")
print(f"  Expected time: {100 / robots_per_second:.1f} seconds ({100 / robots_per_second / 60:.1f} minutes)")
print(f"")
print(f"  50 robots × 20 generations = 1000 evaluations")
print(f"  Expected time: {1000 / robots_per_second:.1f} seconds ({1000 / robots_per_second / 60:.1f} minutes)")
print(f"")
print(f"  100 robots × 50 generations = 5000 evaluations")
print(f"  Expected time: {5000 / robots_per_second:.1f} seconds ({5000 / robots_per_second / 60:.1f} minutes)")

print(f"\n  GPU: Ready for evolution experiments!")
print("="*70)
