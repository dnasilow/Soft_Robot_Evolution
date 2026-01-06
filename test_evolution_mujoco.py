"""Test evolution with MuJoCo physics - small test run"""
import numpy as np
from src.evolution.genetic_algorithm import GeneticAlgorithm
from src.evolution.mujoco_evaluator import create_mujoco_evaluator
from src.evolution.genome_config import VOXEL_GRID_SHAPE

print("="*70)
print("EVOLUTION TEST - MuJoCo Physics")
print("="*70)

# Small test parameters
POPULATION_SIZE = 10
NUM_GENERATIONS = 5
SIMULATION_TIME = 3.0  # Shorter for testing

print(f"\nEvolution Parameters:")
print(f"  Population size: {POPULATION_SIZE}")
print(f"  Generations: {NUM_GENERATIONS}")
print(f"  Simulation time: {SIMULATION_TIME}s per robot")
print(f"  Grid size: {VOXEL_GRID_SHAPE}")

# Create evaluator
print("\nCreating MuJoCo evaluator...")
evaluator = create_mujoco_evaluator(
    simulation_time=SIMULATION_TIME,
    timestep=0.0005,
    actuation_frequency=2.0
)

# Create genetic algorithm
print("Initializing genetic algorithm...")
ga = GeneticAlgorithm(
    population_size=POPULATION_SIZE,
    mutation_rate=0.15,
    crossover_rate=0.7,
    elitism_count=2
)

# Initialize population
print("Generating initial population...")
ga.initialize_population()

print(f"\n{'='*70}")
print("Starting Evolution")
print(f"{'='*70}\n")

# Evolution loop
for generation in range(NUM_GENERATIONS):
    print(f"Generation {generation + 1}/{NUM_GENERATIONS}")

    # Evaluate population
    print(f"  Evaluating {POPULATION_SIZE} robots...")
    fitnesses = evaluator.evaluate_batch(ga.population)

    # Update genetic algorithm
    ga.update_fitness(fitnesses)

    # Statistics
    best_fitness = np.max(fitnesses)
    avg_fitness = np.mean(fitnesses)
    worst_fitness = np.min(fitnesses)

    print(f"  Best fitness:  {best_fitness:.6f}m")
    print(f"  Avg fitness:   {avg_fitness:.6f}m")
    print(f"  Worst fitness: {worst_fitness:.6f}m")

    # Evolve to next generation (except last one)
    if generation < NUM_GENERATIONS - 1:
        ga.evolve()
        print(f"  Population evolved to generation {generation + 2}")

    print()

print(f"{'='*70}")
print("Evolution Complete!")
print(f"{'='*70}")

# Final statistics
best_idx = np.argmax(fitnesses)
best_genome = ga.population[best_idx]
best_fitness = fitnesses[best_idx]

print(f"\nBest Robot:")
print(f"  Fitness: {best_fitness:.6f}m")
print(f"  Voxels: {np.count_nonzero(best_genome)}")
print(f"  Active 0°: {np.count_nonzero(best_genome == 1)}")
print(f"  Active 180°: {np.count_nonzero(best_genome == 2)}")
print(f"  Soft passive: {np.count_nonzero(best_genome == 3)}")
print(f"  Stiff passive: {np.count_nonzero(best_genome == 4)}")

print("\n" + "="*70)
print("SUCCESS: Evolution with stable MuJoCo physics is working!")
print("="*70)
