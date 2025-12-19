"""Small-scale evolution test to validate end-to-end pipeline"""
import numpy as np
import time
from src.evolution.simple_evolution import SimpleEvolution
from src.physics.robot import VoxelRobot

print("="*70)
print("SMALL-SCALE EVOLUTION TEST")
print("="*70)
print("\nPurpose: Validate evolution pipeline before full-scale experiments")
print("Parameters:")
print("  Population: 10 robots")
print("  Generations: 5")
print("  Simulation time: 5 seconds per robot")
print("  Expected runtime: 1-2 minutes")
print("="*70)

# Evolution parameters
config = {
    'population_size': 10,
    'generations': 5,
    'mutation_rate': 0.1,
    'elite_size': 2,
    'voxel_grid_size': (5, 5, 5),
    'simulation_time': 5.0,
    'actuation_frequency': 1.0,
    'timestep': 0.001
}

print(f"\nInitializing evolution engine...")
start_init = time.perf_counter()

evolution = SimpleEvolution(
    population_size=config['population_size'],
    voxel_grid_size=config['voxel_grid_size'],
    mutation_rate=config['mutation_rate'],
    elite_size=config['elite_size'],
    simulation_time=config['simulation_time'],
    actuation_frequency=config['actuation_frequency'],
    timestep=config['timestep']
)

init_time = time.perf_counter() - start_init
print(f"  Initialization: {init_time:.2f} seconds")

# Run evolution
print(f"\nRunning evolution...")
print(f"{'Gen':<5} {'Best':<10} {'Mean':<10} {'Worst':<10} {'Time':<10}")
print("-" * 50)

generation_times = []
best_fitness_history = []
mean_fitness_history = []

overall_start = time.perf_counter()

for gen in range(config['generations']):
    gen_start = time.perf_counter()

    # Run one generation
    evolution.evolve_one_generation()

    gen_time = time.perf_counter() - gen_start
    generation_times.append(gen_time)

    # Get fitness statistics
    fitness_scores = evolution.get_fitness_scores()
    best_fitness = np.max(fitness_scores)
    mean_fitness = np.mean(fitness_scores)
    worst_fitness = np.min(fitness_scores)

    best_fitness_history.append(best_fitness)
    mean_fitness_history.append(mean_fitness)

    print(f"{gen+1:<5} {best_fitness:<10.4f} {mean_fitness:<10.4f} {worst_fitness:<10.4f} {gen_time:<10.1f}s")

overall_time = time.perf_counter() - overall_start

print("\n" + "="*70)
print("EVOLUTION RESULTS")
print("="*70)

# Performance metrics
avg_gen_time = np.mean(generation_times)
total_evaluations = config['population_size'] * config['generations']
robots_per_second = total_evaluations / overall_time

print(f"\nPerformance:")
print(f"  Total runtime: {overall_time:.1f} seconds ({overall_time/60:.1f} minutes)")
print(f"  Average time per generation: {avg_gen_time:.1f} seconds")
print(f"  Total robot evaluations: {total_evaluations}")
print(f"  Throughput: {robots_per_second:.2f} robots/second")

# Fitness progression
fitness_improvement = best_fitness_history[-1] - best_fitness_history[0]
percent_improvement = (fitness_improvement / max(abs(best_fitness_history[0]), 1e-9)) * 100

print(f"\nFitness progression:")
print(f"  Initial best: {best_fitness_history[0]:.4f}")
print(f"  Final best: {best_fitness_history[-1]:.4f}")
print(f"  Improvement: {fitness_improvement:+.4f} ({percent_improvement:+.1f}%)")
print(f"  Trend: ", end="")

if fitness_improvement > 0.01:
    print("IMPROVING (evolution working!)")
elif fitness_improvement > -0.01:
    print("STABLE (may need more generations)")
else:
    print("DECLINING (check fitness function)")

# Best robot analysis
best_idx = np.argmax(evolution.get_fitness_scores())
best_genome = evolution.population[best_idx]
best_robot = VoxelRobot(best_genome, voxel_size=0.01)

num_voxels = np.sum(best_genome != 0)
voxel_types = {i: np.sum(best_genome == i) for i in range(1, 5) if np.any(best_genome == i)}

print(f"\nBest robot (Generation {config['generations']}):")
print(f"  Fitness: {best_fitness_history[-1]:.4f}")
print(f"  Voxels: {num_voxels}")
print(f"  Voxel composition: {voxel_types}")
print(f"  Nodes: {len(best_robot.nodes)}")
print(f"  Springs: {len(best_robot.springs)}")

# Validation checks
print("\n" + "="*70)
print("VALIDATION")
print("="*70)

checks_passed = 0
checks_total = 5

# Check 1: Runtime reasonable
if overall_time < 300:  # Less than 5 minutes
    print(f"  [PASS] Runtime reasonable: {overall_time:.1f}s < 300s")
    checks_passed += 1
else:
    print(f"  [FAIL] Runtime too slow: {overall_time:.1f}s > 300s")

# Check 2: No crashes
print(f"  [PASS] No crashes during evolution")
checks_passed += 1

# Check 3: Fitness values valid
if all(not np.isnan(f) and not np.isinf(f) for f in best_fitness_history):
    print(f"  [PASS] All fitness values valid (no NaN/Inf)")
    checks_passed += 1
else:
    print(f"  [FAIL] Invalid fitness values detected")

# Check 4: Population diversity
unique_genomes = len(set(tuple(g.flatten()) for g in evolution.population))
if unique_genomes > config['population_size'] * 0.5:
    print(f"  [PASS] Population diversity maintained: {unique_genomes}/{config['population_size']} unique")
    checks_passed += 1
else:
    print(f"  [WARN] Low diversity: {unique_genomes}/{config['population_size']} unique genomes")

# Check 5: GPU utilization
if robots_per_second > 2.0:
    print(f"  [PASS] GPU utilization good: {robots_per_second:.2f} robots/s")
    checks_passed += 1
else:
    print(f"  [WARN] Low GPU utilization: {robots_per_second:.2f} robots/s")

print(f"\n  Checks passed: {checks_passed}/{checks_total}")

if checks_passed >= 4:
    print(f"\n  STATUS: READY for full-scale evolution!")
    print(f"\n  Recommended next step:")
    print(f"    - Population: 50-100 robots")
    print(f"    - Generations: 20-50")
    print(f"    - Expected time: {50 * 20 / robots_per_second / 60:.0f}-{100 * 50 / robots_per_second / 60:.0f} minutes")
else:
    print(f"\n  STATUS: Issues detected, investigate before scaling up")

print("="*70)
