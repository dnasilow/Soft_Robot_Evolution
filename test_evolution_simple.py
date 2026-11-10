"""Simple evolution test - 2 generations with TRUE parallel evaluation"""
import numpy as np
import sys
import os
import time
import pickle

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.robot import VoxelRobot
from src.physics.true_parallel_evaluator import TrueParallelBatchEvaluator

print("="*70)
print("SIMPLE EVOLUTION TEST - TRUE Parallel GPU")
print("="*70)
print("\nRunning 2 generations with 5 robots per generation")
print("This will test:")
print("  - Random robot generation")
print("  - Fitness evaluation (TRUE parallel)")
print("  - Selection and reproduction")
print("  - Best robot saving")
print("\n" + "="*70 + "\n")

# Create evaluator with TRUE parallel processing
evaluator = TrueParallelBatchEvaluator(
    actuation_cycles=3,      # 3 actuation cycles (3 seconds at 1Hz)
    actuation_freq=1.0,      # 1 Hz actuation frequency
    timestep=0.001
)

# Simple evolution parameters
POPULATION_SIZE = 5
GENERATIONS = 2
MUTATION_RATE = 0.3
ELITE_SIZE = 1

def create_random_robot():
    """Create a random voxel robot"""
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
    num_voxels = np.random.randint(5, 15)
    for _ in range(num_voxels):
        x, y, z = np.random.randint(1, 4, 3)
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])
    return voxel_grid

def mutate_genome(voxel_grid):
    """Mutate a voxel genome"""
    mutated = voxel_grid.copy()

    # Random mutations
    num_mutations = np.random.randint(1, 4)
    for _ in range(num_mutations):
        if np.random.random() < 0.5:
            # Add voxel
            x, y, z = np.random.randint(1, 4, 3)
            mutated[x, y, z] = np.random.choice([1, 2, 3, 4])
        else:
            # Remove voxel
            occupied = np.argwhere(mutated != 0)
            if len(occupied) > 0:
                idx = occupied[np.random.randint(len(occupied))]
                mutated[tuple(idx)] = 0

    return mutated

# Initialize population
print("Initializing population...")
population = [create_random_robot() for _ in range(POPULATION_SIZE)]

best_fitness_history = []
mean_fitness_history = []

for gen in range(GENERATIONS):
    gen_start = time.perf_counter()

    print(f"\n{'='*70}")
    print(f"Generation {gen + 1}/{GENERATIONS}")
    print(f"{'='*70}")

    # Convert genomes to robots
    robots = []
    for i, genome in enumerate(population):
        robot = VoxelRobot(genome, voxel_size=0.01)
        robots.append(robot)
        print(f"  Robot {i+1}: {len(robot.nodes)} nodes, {len(robot.springs)} springs")

    # Evaluate fitness
    print(f"\nEvaluating fitness (TRUE parallel)...")
    controllers = [None] * POPULATION_SIZE  # Passive robots
    fitness_scores = evaluator.evaluate_batch(robots, controllers)

    best_fitness = np.max(fitness_scores)
    mean_fitness = np.mean(fitness_scores)
    worst_fitness = np.min(fitness_scores)

    best_fitness_history.append(best_fitness)
    mean_fitness_history.append(mean_fitness)

    gen_time = time.perf_counter() - gen_start

    print(f"\nResults:")
    print(f"  Best fitness: {best_fitness:.4f}")
    print(f"  Mean fitness: {mean_fitness:.4f}")
    print(f"  Worst fitness: {worst_fitness:.4f}")
    print(f"  Generation time: {gen_time:.1f}s")

    # Selection and reproduction (simple elitism + mutation)
    if gen < GENERATIONS - 1:
        # Sort by fitness
        sorted_indices = np.argsort(fitness_scores)[::-1]

        # Keep elite
        new_population = [population[i].copy() for i in sorted_indices[:ELITE_SIZE]]

        # Fill rest with mutated copies of best individuals
        while len(new_population) < POPULATION_SIZE:
            parent_idx = sorted_indices[np.random.randint(0, min(3, POPULATION_SIZE))]
            child = mutate_genome(population[parent_idx])
            new_population.append(child)

        population = new_population
        print(f"\n  Created new generation (elite={ELITE_SIZE}, mutated={POPULATION_SIZE-ELITE_SIZE})")

# Final summary
print("\n" + "="*70)
print("EVOLUTION COMPLETE")
print("="*70)

# Save best robot
best_idx = np.argmax(fitness_scores)
best_genome = population[best_idx]
best_fitness = fitness_scores[best_idx]

with open('best_robot.pkl', 'wb') as f:
    pickle.dump(best_genome, f)

print(f"\nBest robot:")
print(f"  Fitness: {best_fitness:.4f}")
print(f"  Voxels: {np.sum(best_genome != 0)}")
print(f"  Saved to: best_robot.pkl")

print(f"\nFitness progression:")
for i, (best, mean) in enumerate(zip(best_fitness_history, mean_fitness_history)):
    print(f"  Gen {i+1}: Best={best:.4f}, Mean={mean:.4f}")

improvement = best_fitness_history[-1] - best_fitness_history[0]
print(f"\nImprovement: {improvement:+.4f}")

if improvement > 0.01:
    print(f"  Status: IMPROVING - Evolution working!")
elif improvement > -0.01:
    print(f"  Status: STABLE - May need more generations")
else:
    print(f"  Status: DECLINING - Check fitness function")

print(f"\n" + "="*70)
print("Visualize best robot with:")
print("  python visualize_saved_robot.py")
print("="*70)
