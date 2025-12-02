#!/usr/bin/env python
"""Simple evolution test - 2 generations with visual playback of best robot"""

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.evolution.evolutionary_algorithm import EvolutionaryAlgorithm
from src.evolution.genomes import DirectVoxelGenome
from src.evolution.controllers import CPGController
from src.physics.robot import TurboChargedBatchEvaluator
from src.physics.cuda_physics import CUDAPhysicsEngine
from src.visualization.viewer import RobotViewer

print("="*70)
print("SIMPLE EVOLUTION TEST")
print("="*70)
print("\nRunning 2 generations with 5 robots per generation")
print("This will test:")
print("  - Genome -> Robot conversion")
print("  - Fitness evaluation")
print("  - Selection and reproduction")
print("  - GPU batch processing")
print("\n" + "="*70 + "\n")

# Create evaluator
evaluator = TurboChargedBatchEvaluator(
    num_environments=5,      # Batch size (same as population)
    actuation_cycles=3,      # 3 actuation cycles (3 seconds at 1Hz)
    actuation_freq=1.0       # 1 Hz actuation frequency
)

# Create evolution algorithm
evo = EvolutionaryAlgorithm(
    population_size=5,
    genome_class=DirectVoxelGenome,
    controller_class=CPGController,
    evaluator=evaluator,
    selection_method='tournament'
)

print("Evolution initialized:")
print(f"  - Population: {evo.population_size}")
print(f"  - Genome: DirectVoxelGenome")
print(f"  - Controller: CPGController")
print(f"  - Selection: tournament")
print("\nStarting evolution...")
print("-" * 70)

# Run 2 generations
try:
    for gen in range(2):
        print(f"\nGeneration {gen + 1}/2...")
        evo.step()

        # Print stats
        if evo.history['best_fitness']:
            best = evo.history['best_fitness'][-1]
            mean = evo.history['mean_fitness'][-1]
            print(f"  Best fitness: {best:.4f}")
            print(f"  Mean fitness: {mean:.4f}")

    print("\n" + "="*70)
    print("Evolution completed successfully!")
    print("="*70)
except Exception as e:
    print(f"\nERROR during evolution: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Get best robot
print("\nFinding best robot from final generation...")
if hasattr(evo, 'best_individual') and evo.best_individual:
    best_individual = evo.best_individual
    best_genome = best_individual.genome
    best_controller = best_individual.controller
    best_fitness = best_individual.fitness
else:
    # Fallback: get from population
    best_individual = evo.population[0]
    best_genome = best_individual.genome
    best_controller = best_individual.controller
    best_fitness = best_individual.fitness

print(f"\nBest robot fitness: {best_fitness:.4f}")

# Create robot from best genome
print("\nCreating robot from best genome...")
best_robot = best_genome.develop()

# Count voxels and actuators
voxel_grid = best_genome.develop_voxel_grid()
num_voxels = np.sum(voxel_grid != 0)
num_actuators = np.sum(best_genome.develop_actuator_grid())

print(f"Best robot structure:")
print(f"  - Total voxels: {num_voxels}")
print(f"  - Nodes: {len(best_robot.nodes)}")
print(f"  - Springs: {len(best_robot.springs)}")
print(f"  - Actuators: {num_actuators}")

# Visualize best robot
print("\n" + "="*70)
print("VISUALIZING BEST ROBOT")
print("="*70)
print("\nStarting 5-second simulation with visualization...")
print("Controls:")
print("  - Left-drag mouse: Rotate view")
print("  - Scroll wheel: Zoom")
print("  - R: Reset camera")
print("  - ESC: Exit")
print("\n" + "="*70 + "\n")

# Initialize physics for best robot
physics_engine = CUDAPhysicsEngine(max_nodes=500, max_springs=2000)
physics_engine.reset()
physics_engine.add_robot(best_robot)

# Get controller signals
controller = best_genome.develop_controller(len(best_robot.springs))
initial_signals = controller.get_signals(np.zeros(12))  # 12 sensor inputs (dummy)
physics_engine.set_actuator_signals(initial_signals)

# Create viewer
viewer = RobotViewer(width=1280, height=720)

# Track metrics
timestep = 0.001
sim_time = 0.0
max_sim_time = 5.0
physics_steps_per_frame = 5

initial_pos = physics_engine.get_positions()
initial_com = best_robot.get_center_of_mass(initial_pos)

print(f"Initial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")

running = True
last_print = 0.0
while running and sim_time < max_sim_time:
    # Run physics
    for _ in range(physics_steps_per_frame):
        physics_engine.step(timestep)
        sim_time += timestep

    # Get current state
    positions = physics_engine.get_positions()
    springs = best_robot.get_springs()
    com = best_robot.get_center_of_mass(positions)

    # Print progress
    if sim_time - last_print >= 1.0:
        distance = np.linalg.norm(com[:2] - initial_com[:2])  # XZ distance
        print(f"t={sim_time:.1f}s: COM=[{com[0]:.3f}, {com[1]:.3f}, {com[2]:.3f}], distance={distance:.3f}m")
        last_print = sim_time

    # Render
    if not viewer.render(positions, springs):
        running = False
        break

    viewer.clock.tick(60)

# Final stats
final_pos = physics_engine.get_positions()
final_com = best_robot.get_center_of_mass(final_pos)
final_distance = np.linalg.norm(final_com[:2] - initial_com[:2])

print("\n" + "="*70)
print("SIMULATION COMPLETE")
print("="*70)
print(f"Initial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")
print(f"Final COM:   [{final_com[0]:.3f}, {final_com[1]:.3f}, {final_com[2]:.3f}]")
print(f"Distance traveled: {final_distance:.4f} m")
print(f"Fitness score: {best_fitness:.4f}")

print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)

if final_distance > 0.1:
    print("[SUCCESS] Robot moved! Evolution is working!")
elif final_distance > 0.01:
    print("[OK] Robot moved slightly - evolution started working")
else:
    print("[INFO] Robot didn't move much - may need more generations")

print("\nEvolution test complete!")
