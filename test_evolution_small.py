"""Small-scale evolution test - 10 robots × 5 generations with TRUE parallel"""
import numpy as np
import time
import pickle
from src.physics.robot import VoxelRobot
from src.physics.true_parallel_evaluator import TrueParallelBatchEvaluator

print("="*70)
print("SMALL-SCALE EVOLUTION TEST - TRUE Parallel GPU")
print("="*70)
print("\nPurpose: Validate evolution pipeline before full-scale experiments")
print("Parameters:")
print("  Population: 10 robots")
print("  Generations: 5")
print("  Simulation time: 5 seconds per robot")
print("  Expected runtime: ~2 minutes")
print("="*70)

# Evolution parameters
POPULATION_SIZE = 10
GENERATIONS = 5
MUTATION_RATE = 0.3
ELITE_SIZE = 2
ACTUATION_CYCLES = 5
ACTUATION_FREQ = 1.0
TIMESTEP = 0.001

def create_random_robot():
    """Create a random voxel robot"""
    voxel_grid = np.zeros((5, 5, 5), dtype=np.int8)
    num_voxels = np.random.randint(6, 15)
    for _ in range(num_voxels):
        x, y, z = np.random.randint(1, 4, 3)
        voxel_grid[x, y, z] = np.random.choice([1, 2, 3, 4])
    return voxel_grid

def mutate_genome(voxel_grid, mutation_rate=0.3):
    """Mutate a voxel genome"""
    mutated = voxel_grid.copy()

    if np.random.random() < mutation_rate:
        num_mutations = np.random.randint(1, 5)
        for _ in range(num_mutations):
            if np.random.random() < 0.5:
                # Add/modify voxel
                x, y, z = np.random.randint(1, 4, 3)
                mutated[x, y, z] = np.random.choice([1, 2, 3, 4])
            else:
                # Remove voxel
                occupied = np.argwhere(mutated != 0)
                if len(occupied) > 2:  # Keep at least 2 voxels
                    idx = occupied[np.random.randint(len(occupied))]
                    mutated[tuple(idx)] = 0

    return mutated

def crossover(parent1, parent2):
    """Simple crossover between two genomes"""
    child = np.zeros_like(parent1)

    # Random 3D split
    split_axis = np.random.randint(0, 3)
    split_point = np.random.randint(1, 4)

    for x in range(5):
        for y in range(5):
            for z in range(5):
                coords = [x, y, z]
                if coords[split_axis] < split_point:
                    child[x, y, z] = parent1[x, y, z]
                else:
                    child[x, y, z] = parent2[x, y, z]

    # Ensure child has at least some voxels
    if np.sum(child != 0) < 3:
        child = parent1.copy()

    return child

print(f"\nInitializing TRUE parallel evaluator...")
evaluator = TrueParallelBatchEvaluator(
    actuation_cycles=ACTUATION_CYCLES,
    actuation_freq=ACTUATION_FREQ,
    timestep=TIMESTEP
)

print(f"Initializing population ({POPULATION_SIZE} robots)...")
population = [create_random_robot() for _ in range(POPULATION_SIZE)]

print(f"\nRunning evolution...")
print(f"{'Gen':<5} {'Best':<10} {'Mean':<10} {'Worst':<10} {'Time':<10}")
print("-" * 50)

best_fitness_history = []
mean_fitness_history = []
generation_times = []

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

    best_fitness_history.append(best_fitness)
    mean_fitness_history.append(mean_fitness)

    gen_time = time.perf_counter() - gen_start
    generation_times.append(gen_time)

    print(f"{gen+1:<5} {best_fitness:<10.4f} {mean_fitness:<10.4f} {worst_fitness:<10.4f} {gen_time:<10.1f}s")

    # Selection and reproduction
    if gen < GENERATIONS - 1:
        sorted_indices = np.argsort(fitness_scores)[::-1]

        # Elite selection
        new_population = [population[i].copy() for i in sorted_indices[:ELITE_SIZE]]

        # Fill rest with crossover + mutation
        while len(new_population) < POPULATION_SIZE:
            # Tournament selection
            parent1_idx = sorted_indices[np.random.randint(0, min(5, POPULATION_SIZE))]
            parent2_idx = sorted_indices[np.random.randint(0, min(5, POPULATION_SIZE))]

            # Crossover
            if np.random.random() < 0.7:
                child = crossover(population[parent1_idx], population[parent2_idx])
            else:
                child = population[parent1_idx].copy()

            # Mutation
            child = mutate_genome(child, MUTATION_RATE)

            new_population.append(child)

        population = new_population

overall_time = time.perf_counter() - overall_start

print("\n" + "="*70)
print("EVOLUTION RESULTS")
print("="*70)

# Performance metrics
avg_gen_time = np.mean(generation_times)
total_evaluations = POPULATION_SIZE * GENERATIONS
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
best_idx = np.argmax(fitness_scores)
best_genome = population[best_idx]
best_robot = VoxelRobot(best_genome, voxel_size=0.01)

num_voxels = np.sum(best_genome != 0)
voxel_types = {i: np.sum(best_genome == i) for i in range(1, 5) if np.any(best_genome == i)}

print(f"\nBest robot (Generation {GENERATIONS}):")
print(f"  Fitness: {best_fitness_history[-1]:.4f}")
print(f"  Voxels: {num_voxels}")
print(f"  Voxel composition: {voxel_types}")
print(f"  Nodes: {len(best_robot.nodes)}")
print(f"  Springs: {len(best_robot.springs)}")

# Save best robot
with open('best_robot.pkl', 'wb') as f:
    pickle.dump(best_genome, f)
print(f"\n  Saved to: best_robot.pkl")

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
unique_genomes = len(set(tuple(g.flatten()) for g in population))
if unique_genomes > POPULATION_SIZE * 0.5:
    print(f"  [PASS] Population diversity maintained: {unique_genomes}/{POPULATION_SIZE} unique")
    checks_passed += 1
else:
    print(f"  [WARN] Low diversity: {unique_genomes}/{POPULATION_SIZE} unique genomes")

# Check 5: GPU utilization
if robots_per_second > 0.3:
    print(f"  [PASS] GPU utilization good: {robots_per_second:.2f} robots/s")
    checks_passed += 1
else:
    print(f"  [WARN] Low GPU utilization: {robots_per_second:.2f} robots/s")

print(f"\n  Checks passed: {checks_passed}/{checks_total}")

if checks_passed >= 4:
    print(f"\n  STATUS: READY for full-scale evolution!")
    print(f"\n  Recommended next step:")
    print(f"    - Small: 10×10 = ~{100 / robots_per_second / 60:.0f} min")
    print(f"    - Medium: 50×20 = ~{1000 / robots_per_second / 60:.0f} min")
    print(f"    - Large: 100×50 = ~{5000 / robots_per_second / 60:.0f} min")
else:
    print(f"\n  STATUS: Issues detected, investigate before scaling up")

print(f"\n" + "="*70)
print("Visualize best robot with:")
print("  python visualize_saved_robot.py")
print("="*70)
