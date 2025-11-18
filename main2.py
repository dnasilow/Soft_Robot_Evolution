import numpy as np
import torch
import os
import sys
import json
from datetime import datetime
import argparse

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.evolution.genomes import DirectVoxelGenome, CPPNGenome
from src.evolution.controllers import CPGController, NeuralController, HybridController
from src.evolution.evolutionary_algorithm import EvolutionaryAlgorithm
from src.visualization.viewer import RobotViewer
from src.visualization.progress_monitor import EvolutionProgressMonitor
from src.visualization.video_recorder import record_final_robot_video

class BatchEvaluator:
    """Batch robot evaluation with EXACT 10-cycle simulation"""
    
    def __init__(self, num_environments=30, actuation_cycles=10, device_id=0, actuation_freq=1.0):
        self.num_environments = num_environments
        self.actuation_cycles = actuation_cycles  # EXACTLY 10 cycles
        self.actuation_freq = actuation_freq  # 1 Hz actuation frequency
        
        # Calculate simulation parameters for EXACT cycle count
        self.cycle_duration = 1.0 / actuation_freq  # 1.0 seconds per cycle
        self.simulation_time = actuation_cycles * self.cycle_duration  # EXACTLY 10.0 seconds
        
        # Choose timestep that gives integer steps per cycle
        self.timestep = 0.0005  # 0.5ms timestep
        self.steps_per_cycle = int(self.cycle_duration / self.timestep)  # 2000 steps per cycle
        self.num_steps = self.steps_per_cycle * actuation_cycles  # EXACTLY 20000 steps
        
        # Verify exact timing
        actual_sim_time = self.num_steps * self.timestep
        
        print(f"EXACT 10-CYCLE SIMULATION SETUP:")
        print(f"  Actuation frequency: {actuation_freq} Hz")
        print(f"  Cycle duration: {self.cycle_duration} s")
        print(f"  Number of cycles: {actuation_cycles}")
        print(f"  Timestep: {self.timestep} s")
        print(f"  Steps per cycle: {self.steps_per_cycle}")
        print(f"  Total steps: {self.num_steps}")
        print(f"  Expected sim time: {self.simulation_time} s")
        print(f"  Actual sim time: {actual_sim_time} s")
        print(f"  Timing error: {abs(self.simulation_time - actual_sim_time)} s")
        
        if abs(self.simulation_time - actual_sim_time) > 1e-10:
            print("WARNING: Simulation timing is not exact!")
        else:
            print("✓ Simulation timing is EXACT")
        
        # Initialize physics engines with correct timestep
        self.physics_engines = []
        for i in range(num_environments):
            engine = CUDAPhysicsEngine(
                max_nodes=1000, 
                max_springs=5000, 
                actuation_frequency=actuation_freq
            )
            self.physics_engines.append(engine)
        
        print(f"Initialized {num_environments} parallel physics environments")

    def evaluate_batch(self, robots, controllers):
        """Evaluate robots for EXACTLY 10 actuation cycles"""
        batch_size = len(robots)
        fitness_scores = np.zeros(batch_size)
        
        # Process in chunks that fit in GPU memory
        chunk_size = min(batch_size, self.num_environments)
        
        for chunk_start in range(0, batch_size, chunk_size):
            chunk_end = min(chunk_start + chunk_size, batch_size)
            chunk_robots = robots[chunk_start:chunk_end]
            chunk_controllers = controllers[chunk_start:chunk_end]
            
            print(f"Processing robots {chunk_start} to {chunk_end} for EXACTLY {self.actuation_cycles} cycles...")
            
            # Reset physics engines
            for i, (robot, controller) in enumerate(zip(chunk_robots, chunk_controllers)):
                self.physics_engines[i].reset()
                self.physics_engines[i].add_robot(robot)
            
            # Get initial positions
            initial_positions = []
            for i in range(len(chunk_robots)):
                positions = self.physics_engines[i].get_positions()
                if len(positions) > 0:
                    com = chunk_robots[i].get_center_of_mass(positions)
                    if np.any(np.isnan(com)):
                        print(f"Warning: Robot {i} has NaN initial COM, using origin")
                        com = np.zeros(3)
                else:
                    com = np.zeros(3)
                initial_positions.append(com)
                print(f"  Robot {i} initial COM: {com}")
            
            # Store previous COM for velocity calculation
            prev_com = [None] * len(chunk_robots)
            
            # Simulate for EXACTLY the calculated number of steps
            print(f"Running simulation for EXACTLY {self.num_steps} steps ({self.actuation_cycles} cycles)...")
            
            for step in range(self.num_steps):
                # Progress indicator every cycle (not every 100 steps)
                if step % self.steps_per_cycle == 0:
                    cycle_num = step // self.steps_per_cycle
                    print(f"  Cycle {cycle_num + 1}/{self.actuation_cycles}")
                
                # Get control signals
                for i in range(len(chunk_robots)):
                    if chunk_controllers[i] is not None:
                        # Simple sensor data: COM position and velocity
                        positions = self.physics_engines[i].get_positions()
                        if len(positions) > 0:
                            com = chunk_robots[i].get_center_of_mass(positions)
                            
                            # Check for NaN
                            if np.any(np.isnan(com)):
                                com = prev_com[i] if prev_com[i] is not None else np.zeros(3)
                        else:
                            com = np.zeros(3)
                        
                        # Estimate velocity (simple finite difference)
                        if step > 0 and prev_com[i] is not None:
                            velocity = (com - prev_com[i]) / self.timestep
                        else:
                            velocity = np.zeros(3)
                        
                        sensor_data = np.concatenate([com, velocity, np.zeros(6)])  # 12D
                        
                        # Get control signal
                        control = chunk_controllers[i].step(self.timestep, sensor_data)
                        
                        # Apply to physics engine
                        self.physics_engines[i].set_actuator_signals(control)
                
                # Physics step with EXACT timestep
                for i in range(len(chunk_robots)):
                    self.physics_engines[i].step(self.timestep)
                
                # Store previous COM for velocity calculation
                for i in range(len(chunk_robots)):
                    positions = self.physics_engines[i].get_positions()
                    if len(positions) > 0:
                        com = chunk_robots[i].get_center_of_mass(positions)
                        if not np.any(np.isnan(com)):
                            prev_com[i] = com
            
            print("✓ Completed EXACTLY 10 actuation cycles")
            
            # Calculate fitness
            print("Calculating fitness scores...")
            for i in range(len(chunk_robots)):
                positions = self.physics_engines[i].get_positions()
                if len(positions) > 0:
                    final_com = chunk_robots[i].get_center_of_mass(positions)
                    
                    # Check for NaN
                    if np.any(np.isnan(final_com)):
                        print(f"  Robot {i}: final COM is NaN, using initial position")
                        final_com = initial_positions[i]
                else:
                    final_com = initial_positions[i]
                
                print(f"  Robot {i} final COM: {final_com}")
                
                # Calculate total displacement (3D distance, not just X-axis)
                displacement = np.linalg.norm(final_com - initial_positions[i])
                
                # Handle NaN displacement
                if np.isnan(displacement):
                    displacement = 0.0
                
                # Normalize by body length (use largest dimension as per Lipson)
                body_size = chunk_robots[i].get_bounding_box_size()
                body_length = max(np.max(body_size), 0.01)  # Avoid division by zero
                
                # Fitness: body-lengths per second (Lipson's exact metric)
                fitness = displacement / (body_length * self.simulation_time)
                
                # Handle NaN and infinity
                if np.isnan(fitness) or np.isinf(fitness):
                    fitness = 0.0  # Default to 0 if calculation fails
                
                # Add small bonus for just existing (encourages evolution)
                fitness += 0.0001
                
                fitness_scores[chunk_start + i] = fitness
                
                print(f"  Robot {chunk_start + i}: displacement={displacement:.4f}m, "
                      f"body_length={body_length:.4f}m, fitness={fitness:.4f} BL/s")
        
        print(f"Evaluation complete. Fitness range: [{np.min(fitness_scores):.4f}, {np.max(fitness_scores):.4f}]")
        return fitness_scores

def run_experiment(args):
    """Main experiment runner"""
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("results", f"experiment_{args.name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save experiment configuration
    config = vars(args)
    with open(os.path.join(output_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    
    # Initialize components
    print("Initializing experiment...")
    
    # Choose genome type
    if args.encoding == "direct":
        genome_class = DirectVoxelGenome
    else:
        genome_class = CPPNGenome
    
    # Choose controller type
    controller_classes = {
        "cpg": CPGController,
        "neural": NeuralController,
        "hybrid": HybridController
    }
    controller_class = controller_classes[args.controller]
    
    # FIXED: Create evaluator with correct parameters
    evaluator = BatchEvaluator(
        num_environments=args.batch_size,
        actuation_cycles=args.actuation_cycles,  # ✅ CORRECT parameter name
        actuation_freq=args.actuation_freq
    )
    
    # Create evolutionary algorithm
    evolution = EvolutionaryAlgorithm(
        population_size=args.population,
        genome_class=genome_class,
        controller_class=controller_class,
        evaluator=evaluator,
        selection_method=args.selection
    )
    
    # Create visualizations
    viewer = None
    monitor = None
    if args.visualize and args.realtime:  # Add --realtime flag
        viewer = RobotViewer()
        monitor = EvolutionProgressMonitor(save_plots=True)
    elif args.visualize:  # Just plotting, no real-time
        monitor = EvolutionProgressMonitor(save_plots=True)
    
    # Evolution loop
    print(f"Starting evolution for {args.generations} generations...")
    
    for generation in range(args.generations):
        # Evolution step
        evolution.step()
        
        # Get statistics
        best_fitness = evolution.history['best_fitness'][-1]
        mean_fitness = evolution.history['mean_fitness'][-1]
        diversity = evolution.history['diversity'][-1]
        
        # Update monitor (this just stores data and prints to console)
        if args.visualize:
            if evolution.best_individual and hasattr(evolution.best_individual, 'genome'):
                best_robot_data = {
                    'voxels': evolution.best_individual.genome.voxels if hasattr(evolution.best_individual.genome, 'voxels') else None
                }
            else:
                best_robot_data = None
            monitor.update(generation, best_fitness, mean_fitness, diversity, best_robot_data)
        else:
            # Print progress even without visualization
            print(f"Generation {generation}: Best={best_fitness:.4f}, Mean={mean_fitness:.4f}, Diversity={diversity:.4f}")

        # Save checkpoint
        if generation % args.checkpoint_interval == 0:
            evolution.save_checkpoint(output_dir)
            
            # Also save progress plot
            if args.visualize:
                plot_path = os.path.join(output_dir, f'progress_gen_{generation}.png')
                monitor.create_summary_plot(plot_path)
        
        # Check early stopping
        if len(evolution.history['best_fitness']) > 50:
            recent_improvement = (evolution.history['best_fitness'][-1] - 
                                evolution.history['best_fitness'][-50])
            if recent_improvement < 0.001:
                print("Early stopping: No significant improvement")
                break
    
    # Save final results
    print("Saving final results...")
    evolution.save_checkpoint(output_dir)
    
    # Create final progress plot
    if args.visualize:
        final_plot_path = os.path.join(output_dir, 'final_progress.png')
        monitor.create_summary_plot(final_plot_path)

    # Generate report
    generate_report(evolution, output_dir)
    
    # FINAL ROBOT VISUALIZATION/RECORDING
    if args.visualize and evolution.best_individual:
        print("\n" + "="*60)
        
        if args.realtime:
            # Real-time visualization (slower)
            print("VISUALIZING FINAL BEST ROBOT (REAL-TIME)")
            print("="*60)
            visualize_final_robot(viewer, evolution.best_individual, 
                                evaluator.physics_engines[0], simulation_time=10.0)
        else:
            # Video recording (faster, better for long runs)
            print("RECORDING FINAL BEST ROBOT VIDEO")
            print("="*60)
            
            # Import the video recorder
            from src.visualization.video_recorder import record_final_robot_video
            
            video_path = record_final_robot_video(
                evolution.best_individual,
                evaluator.physics_engines[0],
                output_dir,
                simulation_time=args.video_length
            )
            
            print(f"\n✓ Video saved to: {video_path}")
            print(f"✓ You can watch it anytime without re-running the evolution!")
    
    print(f"Experiment complete! Results saved to {output_dir}")

def visualize_final_robot(viewer, best_individual, physics_engine, simulation_time=10.0):
    """Visualize the final best robot"""
    
    # Get robot and controller
    robot = best_individual.genome.to_phenotype()
    controller = best_individual.controller
    
    print(f"Final Best Robot Stats:")
    print(f"  Fitness: {best_individual.fitness:.4f}")
    print(f"  Nodes: {len(robot.nodes)}")
    print(f"  Springs: {len(robot.springs)}")
    actuators = len([s for s in robot.springs if s['is_actuator']])
    print(f"  Actuators: {actuators}")
    print(f"  Age: {best_individual.age} generations")
    
    # Reset physics engine
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    timestep = 0.0005  # Use same timestep as evaluation
    num_steps = int(simulation_time / timestep)
    
    print(f"\nSimulating for {simulation_time} seconds ({num_steps} steps)...")
    print("Controls: Left-drag to rotate, Scroll to zoom, Close window when done")
    
    # Track trajectory for analysis
    trajectory = []
    
    for step in range(num_steps):
        # Get sensor data
        positions = physics_engine.get_positions()
        if len(positions) > 0:
            com = robot.get_center_of_mass(positions)
            trajectory.append(com.copy())
            sensor_data = np.concatenate([com, np.zeros(9)])  # 12D sensor data
            
            # Get control signal
            if controller:
                control = controller.step(timestep, sensor_data)
                physics_engine.set_actuator_signals(control)
        
        # Physics step
        physics_engine.step(timestep)
        
        # Render every 10 steps (about 50 FPS with 0.0005 timestep)
        if step % 10 == 0:
            positions = physics_engine.get_positions()
            springs = robot.get_springs()
            
            if not viewer.render(positions, springs):
                print("Visualization stopped by user")
                break
            
            # Print progress every 2 seconds
            if step % 4000 == 0:  # 4000 steps = 2 seconds
                elapsed_time = step * timestep
                current_pos = robot.get_center_of_mass(positions)
                print(f"  Time: {elapsed_time:.1f}s, Position: [{current_pos[0]:.3f}, {current_pos[1]:.3f}, {current_pos[2]:.3f}]")
    
    # Print final trajectory analysis
    if len(trajectory) > 1:
        trajectory = np.array(trajectory)
        total_distance = np.linalg.norm(trajectory[-1] - trajectory[0])
        path_length = np.sum(np.linalg.norm(np.diff(trajectory, axis=0), axis=1))
        
        print(f"\nFinal Robot Performance:")
        print(f"  Starting position: [{trajectory[0][0]:.3f}, {trajectory[0][1]:.3f}, {trajectory[0][2]:.3f}]")
        print(f"  Final position: [{trajectory[-1][0]:.3f}, {trajectory[-1][1]:.3f}, {trajectory[-1][2]:.3f}]")
        print(f"  Total displacement: {total_distance:.4f} m")
        print(f"  Path length: {path_length:.4f} m")
        print(f"  Average speed: {path_length/simulation_time:.4f} m/s")
        print(f"  Efficiency (straight-line): {total_distance/path_length:.3f}")
        
        # Check if robot moved significantly
        if total_distance > 0.01:  # Moved more than 1cm
            print(f"  ✓ Robot shows locomotion!")
        else:
            print(f"  ✗ Robot barely moved - may need controller tuning")
    
    print("\nVisualization complete!")

def generate_report(evolution, output_dir):
    """Generate experiment report"""
    import matplotlib.pyplot as plt
    
    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Fitness evolution
    ax = axes[0, 0]
    ax.plot(evolution.history['best_fitness'], 'b-', label='Best')
    ax.plot(evolution.history['mean_fitness'], 'g--', label='Mean')
    ax.set_xlabel('Generation')
    ax.set_ylabel('Fitness (BL/s)')
    ax.set_title('Fitness Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Diversity
    ax = axes[0, 1]
    ax.plot(evolution.history['diversity'], 'r-')
    ax.set_xlabel('Generation')
    ax.set_ylabel('Population Diversity')
    ax.set_title('Genetic Diversity')
    ax.grid(True, alpha=0.3)
    
    # Best fitness distribution
    ax = axes[1, 0]
    final_fitness = [ind.fitness for ind in evolution.population]
    # Filter out infinite values for histogram
    finite_fitness = [f for f in final_fitness if np.isfinite(f)]
    if len(finite_fitness) > 0:
        ax.hist(finite_fitness, bins=20, alpha=0.7, color='blue')
        ax.set_xlabel('Fitness')
        ax.set_ylabel('Count')
        ax.set_title(f'Final Population Fitness Distribution\n({len(final_fitness)-len(finite_fitness)} infinite values excluded)')
    else:
        ax.text(0.5, 0.5, 'No finite fitness values', ha='center', va='center')
        ax.set_title('Final Population Fitness Distribution')
    
    # Best robot visualization
    ax = axes[1, 1]
    ax.text(0.5, 0.5, f'Best Fitness: {evolution.best_individual.fitness:.4f}\n' +
                       f'Generation: {evolution.generation}\n' +
                       f'Population Size: {evolution.population_size}',
            ha='center', va='center', fontsize=12)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'experiment_summary.png'), dpi=300)
    plt.close()

def verify_pattern_generation():
    """Test to verify we're using real CPPN"""
    print("Testing pattern generation methods:")
    
    # Test old hardcoded method
    print("\n1. Old hardcoded method:")
    old_pattern = np.zeros((10, 10, 10))
    center = np.array([5, 5, 5])
    for x in range(10):
        for y in range(10):
            for z in range(10):
                norm_x = (x - center[0]) / 5
                norm_y = (y - center[1]) / 5
                norm_z = (z - center[2]) / 5
                distance = np.sqrt(norm_x**2 + norm_y**2 + norm_z**2)
                voxel_presence = np.sin(norm_x * 3) * np.cos(norm_y * 3) * np.exp(-distance)
                if voxel_presence > 0.1:
                    old_pattern[x, y, z] = 1
    
    print(f"Old method: {np.sum(old_pattern > 0)} voxels")
    
    # Test new CPPN method
    print("\n2. New CPPN method:")
    genome = DirectVoxelGenome()
    print(f"CPPN method: {np.sum(genome.voxels > 0)} voxels")
    print(f"Material distribution: {np.bincount(genome.voxels.flatten())}")
    
    # Verify CPPN structure
    print(f"\n3. CPPN structure verification:")
    print(f"CPPN inputs: {genome.cppn.num_inputs}")
    print(f"CPPN outputs: {genome.cppn.num_outputs}")
    print(f"CPPN nodes: {len(genome.cppn.nodes)}")
    print(f"CPPN connections: {len(genome.cppn.connections)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evolve Soft Robots - Lipson Replication')
    
    # Experiment parameters
    parser.add_argument('--name', type=str, default='lipson_replication', help='Experiment name')
    parser.add_argument('--generations', type=int, default=1000, help='Number of generations (Lipson: 1000)')
    parser.add_argument('--population', type=int, default=30, help='Population size (Lipson: 30)')
    parser.add_argument('--batch-size', type=int, default=30, help='Batch size for GPU evaluation')
    
    # Evolution parameters  
    parser.add_argument('--encoding', choices=['direct', 'cppn'], default='direct', 
                        help='Genome encoding (direct uses CPPN internally)')
    parser.add_argument('--controller', choices=['cpg', 'neural', 'hybrid'], default='cpg', 
                        help='Controller type')
    parser.add_argument('--selection', choices=['tournament', 'roulette'], default='tournament', 
                        help='Selection method')
    
    # Simulation parameters matching Lipson exactly
    parser.add_argument('--actuation-cycles', type=int, default=10, 
                        help='Actuation cycles per evaluation (Lipson: 10)')
    parser.add_argument('--actuation-freq', type=float, default=1.0, 
                        help='Actuation frequency in Hz (Lipson: ~1Hz)')
    
    # Visualization options
    parser.add_argument('--visualize', action='store_true', 
                        help='Enable visualization (video recording by default)')
    parser.add_argument('--realtime', action='store_true', 
                        help='Use real-time visualization instead of video recording')
    parser.add_argument('--video-length', type=float, default=10.0, 
                        help='Length of recorded video in seconds')
    parser.add_argument('--checkpoint-interval', type=int, default=50, 
                        help='Checkpoint save interval')

    args = parser.parse_args()
    
    # ADDED: Run pattern verification test if requested
    if args.name == 'test_patterns':
        verify_pattern_generation()
        sys.exit(0)
    
    # Set random seeds for reproducibility
    np.random.seed(42)
    torch.manual_seed(42)
    
    # Run experiment
    run_experiment(args)