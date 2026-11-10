"""LARGE Evolution Experiment: 100×50 (~3.3 hours)"""
import numpy as np
import time
import pickle
import json
from pathlib import Path
from src.physics.robot import VoxelRobot
from src.physics.true_parallel_evaluator import TrueParallelBatchEvaluator
from src.evolution.genome_config import *

# ==================== CONFIGURATION ====================
POPULATION_SIZE = 100
GENERATIONS = 50
MUTATION_RATE = 0.2
ELITE_SIZE = 10
CROSSOVER_RATE = 0.8
ACTUATION_CYCLES = 5      # 5 seconds simulation
ACTUATION_FREQ = 1.0      # 1 Hz
TIMESTEP = 0.001

EXPERIMENT_NAME = f"large_{POPULATION_SIZE}x{GENERATIONS}"
RESULTS_DIR = Path("results") / EXPERIMENT_NAME
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*70)
print("LARGE EVOLUTION EXPERIMENT")
print("="*70)
print(f"\nParameters:")
print(f"  Population: {POPULATION_SIZE}")
print(f"  Generations: {GENERATIONS}")
print(f"  Total evaluations: {POPULATION_SIZE * GENERATIONS}")
print(f"  Mutation rate: {MUTATION_RATE}")
print(f"  Elite size: {ELITE_SIZE}")
print(f"  Crossover rate: {CROSSOVER_RATE}")
print(f"  Simulation: {ACTUATION_CYCLES} cycles @ {ACTUATION_FREQ} Hz")
print(f"\nEstimated runtime: ~3.3 hours (199 minutes)")
print(f"Results will be saved to: {RESULTS_DIR}")
print("="*70)

# ==================== GENOME FUNCTIONS ====================
def create_random_robot():
    """Create a random voxel robot"""
    voxel_grid = create_empty_grid()
    num_voxels = get_num_voxels()
    for _ in range(num_voxels):
        x, y, z = get_random_interior_position()
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])
    return voxel_grid

def mutate_genome(voxel_grid, mutation_rate=MUTATION_RATE):
    """Mutate a voxel genome"""
    mutated = voxel_grid.copy()

    if np.random.random() < mutation_rate:
        num_mutations = np.random.randint(1, 5)
        for _ in range(num_mutations):
            if np.random.random() < 0.5:
                x, y, z = get_random_interior_position()
                mutated[x, y, z] = np.random.choice([1, 2, 3, 4])
            else:
                occupied = np.argwhere(mutated != 0)
                if len(occupied) > 2:
                    idx = occupied[np.random.randint(len(occupied))]
                    mutated[tuple(idx)] = 0

    return mutated

def crossover(parent1, parent2):
    """3D crossover between two genomes"""
    child = np.zeros_like(parent1)
    split_axis = np.random.randint(0, 3)
    split_point = np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX)

    for x in range(VOXEL_GRID_SHAPE[0]):
        for y in range(VOXEL_GRID_SHAPE[1]):
            for z in range(VOXEL_GRID_SHAPE[2]):
                coords = [x, y, z]
                if coords[split_axis] < split_point:
                    child[x, y, z] = parent1[x, y, z]
                else:
                    child[x, y, z] = parent2[x, y, z]

    if np.sum(child != 0) < 3:
        child = parent1.copy()

    return child

# ==================== INITIALIZATION ====================
print(f"\nInitializing TRUE parallel evaluator...")
evaluator = TrueParallelBatchEvaluator(
    actuation_cycles=ACTUATION_CYCLES,
    actuation_freq=ACTUATION_FREQ,
    timestep=TIMESTEP
)

print(f"Creating initial population ({POPULATION_SIZE} robots)...")
population = [create_random_robot() for _ in range(POPULATION_SIZE)]

# ==================== EVOLUTION LOOP ====================
print(f"\n" + "="*70)
print("RUNNING EVOLUTION")
print("="*70)
print(f"{'Gen':<5} {'Best':<12} {'Mean':<12} {'Worst':<12} {'Time':<10}")
print("-" * 60)

best_fitness_history = []
mean_fitness_history = []
worst_fitness_history = []
generation_times = []
best_genomes = []

overall_start = time.perf_counter()

for gen in range(GENERATIONS):
    gen_start = time.perf_counter()

    # Convert genomes to robots
    robots = [VoxelRobot(genome, voxel_size=0.01) for genome in population]

    # Evaluate fitness (TRUE parallel!)
    controllers = [None] * POPULATION_SIZE
    fitness_scores = evaluator.evaluate_batch(robots, controllers)

    # Statistics
    best_fitness = np.max(fitness_scores)
    mean_fitness = np.mean(fitness_scores)
    worst_fitness = np.min(fitness_scores)

    best_fitness_history.append(float(best_fitness))
    mean_fitness_history.append(float(mean_fitness))
    worst_fitness_history.append(float(worst_fitness))

    gen_time = time.perf_counter() - gen_start
    generation_times.append(gen_time)

    # Save best genome from this generation
    best_idx = np.argmax(fitness_scores)
    best_genomes.append(population[best_idx].copy())

    print(f"{gen+1:<5} {best_fitness:<12.6f} {mean_fitness:<12.6f} {worst_fitness:<12.6f} {gen_time:<10.1f}s")

    # Save generation results
    gen_data = {
        'generation': gen + 1,
        'best_fitness': float(best_fitness),
        'mean_fitness': float(mean_fitness),
        'worst_fitness': float(worst_fitness),
        'fitness_scores': fitness_scores.tolist(),
        'time_seconds': gen_time
    }
    with open(RESULTS_DIR / f"gen_{gen+1:03d}.json", 'w') as f:
        json.dump(gen_data, f, indent=2)

    # Selection and reproduction
    if gen < GENERATIONS - 1:
        sorted_indices = np.argsort(fitness_scores)[::-1]

        # Elite selection
        new_population = [population[i].copy() for i in sorted_indices[:ELITE_SIZE]]

        # Fill rest with crossover + mutation
        while len(new_population) < POPULATION_SIZE:
            parent1_idx = sorted_indices[np.random.randint(0, min(5, POPULATION_SIZE))]
            parent2_idx = sorted_indices[np.random.randint(0, min(5, POPULATION_SIZE))]

            if np.random.random() < CROSSOVER_RATE:
                child = crossover(population[parent1_idx], population[parent2_idx])
            else:
                child = population[parent1_idx].copy()

            child = mutate_genome(child)
            new_population.append(child)

        population = new_population

overall_time = time.perf_counter() - overall_start

# ==================== FINAL RESULTS ====================
print("\n" + "="*70)
print("EVOLUTION COMPLETE")
print("="*70)

avg_gen_time = np.mean(generation_times)
total_evaluations = POPULATION_SIZE * GENERATIONS
robots_per_second = total_evaluations / overall_time

print(f"\nPerformance:")
print(f"  Total runtime: {overall_time:.1f}s ({overall_time/60:.1f} min)")
print(f"  Average time per generation: {avg_gen_time:.1f}s")
print(f"  Total evaluations: {total_evaluations}")
print(f"  Throughput: {robots_per_second:.2f} robots/s")

fitness_improvement = best_fitness_history[-1] - best_fitness_history[0]
percent_improvement = (fitness_improvement / max(abs(best_fitness_history[0]), 1e-9)) * 100

print(f"\nFitness progression:")
print(f"  Initial best: {best_fitness_history[0]:.6f}")
print(f"  Final best: {best_fitness_history[-1]:.6f}")
print(f"  Improvement: {fitness_improvement:+.6f} ({percent_improvement:+.1f}%)")

# Save best robot
best_idx = np.argmax(fitness_scores)
best_genome = population[best_idx]

with open(RESULTS_DIR / 'best_robot.pkl', 'wb') as f:
    pickle.dump(best_genome, f)

with open('best_robot.pkl', 'wb') as f:  # Also save to root for easy access
    pickle.dump(best_genome, f)

print(f"\nBest robot saved to:")
print(f"  {RESULTS_DIR / 'best_robot.pkl'}")
print(f"  best_robot.pkl (root directory)")

# Save summary
summary = {
    'experiment': EXPERIMENT_NAME,
    'parameters': {
        'population_size': POPULATION_SIZE,
        'generations': GENERATIONS,
        'mutation_rate': MUTATION_RATE,
        'elite_size': ELITE_SIZE,
        'crossover_rate': CROSSOVER_RATE,
        'actuation_cycles': ACTUATION_CYCLES,
        'actuation_freq': ACTUATION_FREQ,
        'timestep': TIMESTEP
    },
    'performance': {
        'total_runtime_seconds': overall_time,
        'avg_generation_time_seconds': avg_gen_time,
        'total_evaluations': total_evaluations,
        'throughput_robots_per_second': robots_per_second
    },
    'results': {
        'initial_best_fitness': best_fitness_history[0],
        'final_best_fitness': best_fitness_history[-1],
        'fitness_improvement': fitness_improvement,
        'percent_improvement': percent_improvement,
        'best_fitness_history': best_fitness_history,
        'mean_fitness_history': mean_fitness_history,
        'worst_fitness_history': worst_fitness_history
    }
}

with open(RESULTS_DIR / 'summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\nSummary saved to: {RESULTS_DIR / 'summary.json'}")

print(f"\n" + "="*70)
print("Visualize best robot with:")
print("  python visualize_saved_robot.py")
print("="*70)
