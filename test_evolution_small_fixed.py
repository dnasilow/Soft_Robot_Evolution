"""Small-scale evolution test using existing infrastructure"""
import numpy as np
import time
from src.evolution.evolutionary_algorithm import EvolutionaryAlgorithm
from src.evolution.genomes import OptimizedCPPNGenome
from src.evolution.controllers import CPGController
from src.physics.robot import TurboChargedBatchEvaluator

print("="*70)
print("SMALL-SCALE EVOLUTION TEST")
print("="*70)
print("\nValidating evolution pipeline with existing infrastructure")
print("Parameters:")
print("  Population: 10 robots")
print("  Generations: 5")
print("  Simulation: 5 actuation cycles")
print("="*70)

# Create evaluator
print(f"\nInitializing batch evaluator...")
evaluator = TurboChargedBatchEvaluator(
    num_environments=30,
    actuation_cycles=5,
    actuation_freq=1.0
)

# Create evolutionary algorithm
print(f"Initializing evolutionary algorithm...")
evolution = EvolutionaryAlgorithm(
    population_size=10,
    genome_class=OptimizedCPPNGenome,
    controller_class=CPGController,
    evaluator=evaluator,
    selection_method='tournament'
)

# Set evolution parameters
evolution.mutation_rate = 0.15
evolution.crossover_rate = 0.5
evolution.elitism_size = 2

print(f"\n  Population size: {evolution.population_size}")
print(f"  Elitism size: {evolution.elitism_size}")
print(f"  Mutation rate: {evolution.mutation_rate}")
print(f"  Crossover rate: {evolution.crossover_rate}")

# Run evolution
print(f"\nRunning 5 generations of evolution...")
print(f"{'Gen':<5} {'Best':<12} {'Mean':<12} {'Std':<10} {'Time':<8}")
print("-" * 55)

overall_start = time.perf_counter()
generation_times = []

for gen in range(5):
    gen_start = time.perf_counter()

    # Evolve one generation
    evolution.evolve_one_generation()

    gen_time = time.perf_counter() - gen_start
    generation_times.append(gen_time)

    # Get statistics
    fitness_values = [ind.fitness for ind in evolution.population]
    best_fitness = np.max(fitness_values)
    mean_fitness = np.mean(fitness_values)
    std_fitness = np.std(fitness_values)

    print(f"{gen+1:<5} {best_fitness:<12.4f} {mean_fitness:<12.4f} {std_fitness:<10.4f} {gen_time:<8.1f}s")

overall_time = time.perf_counter() - overall_start

print("\n" + "="*70)
print("RESULTS")
print("="*70)

# Performance metrics
avg_gen_time = np.mean(generation_times)
total_evals = evolution.population_size * 5
robots_per_second = total_evals / overall_time

print(f"\nPerformance:")
print(f"  Total runtime: {overall_time:.1f}s ({overall_time/60:.1f} min)")
print(f"  Avg time/generation: {avg_gen_time:.1f}s")
print(f"  Total evaluations: {total_evals}")
print(f"  Throughput: {robots_per_second:.2f} robots/second")

# Fitness progression
initial_fitness = evolution.history['best_fitness'][0]
final_fitness = evolution.history['best_fitness'][-1]
improvement = final_fitness - initial_fitness
percent_change = (improvement / max(abs(initial_fitness), 1e-9)) * 100

print(f"\nFitness Evolution:")
print(f"  Initial best: {initial_fitness:.4f}")
print(f"  Final best: {final_fitness:.4f}")
print(f"  Change: {improvement:+.4f} ({percent_change:+.1f}%)")

if improvement > 0.01:
    print(f"  STATUS: IMPROVING - Evolution working!")
elif abs(improvement) < 0.01:
    print(f"  STATUS: STABLE - May need more generations")
else:
    print(f"  STATUS: DECLINING - Check fitness function")

# Best individual analysis
best_ind = max(evolution.population, key=lambda x: x.fitness)
print(f"\nBest Individual:")
print(f"  Fitness: {best_ind.fitness:.4f}")
print(f"  Age: {best_ind.age} generations")

if hasattr(best_ind, 'base_fitness'):
    print(f"  Base fitness: {best_ind.base_fitness:.4f}")
    print(f"  Diversity bonus: {best_ind.diversity_bonus:.4f}")

# Validation
print("\n" + "="*70)
print("VALIDATION")
print("="*70)

checks_passed = 0
total_checks = 5

# Check 1: Completed successfully
print(f"  [PASS] Completed {5} generations without crashes")
checks_passed += 1

# Check 2: Runtime reasonable
if overall_time < 300:
    print(f"  [PASS] Runtime acceptable: {overall_time:.1f}s < 300s")
    checks_passed += 1
else:
    print(f"  [FAIL] Runtime too slow: {overall_time:.1f}s")

# Check 3: Valid fitness
all_valid = all(not np.isnan(f) and not np.isinf(f) for f in evolution.history['best_fitness'])
if all_valid:
    print(f"  [PASS] All fitness values valid")
    checks_passed += 1
else:
    print(f"  [FAIL] NaN/Inf fitness detected")

# Check 4: Population diversity
unique_count = len(set(id(ind.genome) for ind in evolution.population))
if unique_count >= evolution.population_size * 0.8:
    print(f"  [PASS] Good diversity: {unique_count}/{evolution.population_size} unique genomes")
    checks_passed += 1
else:
    print(f"  [WARN] Low diversity: {unique_count}/{evolution.population_size}")

# Check 5: Throughput
if robots_per_second > 1.0:
    print(f"  [PASS] Good throughput: {robots_per_second:.2f} robots/s")
    checks_passed += 1
else:
    print(f"  [WARN] Low throughput: {robots_per_second:.2f} robots/s")

print(f"\n  Total: {checks_passed}/{total_checks} checks passed")

# Recommendations
print("\n" + "="*70)
print("NEXT STEPS")
print("="*70)

if checks_passed >= 4:
    print(f"\n  STATUS: READY for larger experiments!")
    print(f"\n  Recommended scaling:")
    print(f"    Population: 50 robots")
    print(f"    Generations: 20-50")
    print(f"    Expected time: {50 * 20 / robots_per_second / 60:.0f}-{50 * 50 / robots_per_second / 60:.0f} minutes")
    print(f"\n  Run: python main.py (if you have it configured)")
else:
    print(f"\n  STATUS: Issues detected")
    print(f"  - Fix performance/stability before scaling")
    print(f"  - Check GPU utilization")
    print(f"  - Verify fitness function")

print("="*70)
