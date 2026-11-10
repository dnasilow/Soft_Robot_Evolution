"""TRUE parallel GPU batch evaluator - all robots in ONE physics engine"""
import numpy as np
import cupy as cp
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine

class TrueParallelBatchEvaluator:
    """Evaluates multiple robots in parallel on GPU by combining into one physics array"""

    def __init__(self, actuation_cycles=5, actuation_freq=1.0, timestep=0.001):
        self.actuation_cycles = actuation_cycles
        self.actuation_freq = actuation_freq
        self.timestep = timestep

        # Calculate simulation parameters
        self.cycle_duration = 1.0 / actuation_freq
        self.simulation_time = actuation_cycles * self.cycle_duration
        self.steps_per_cycle = int(self.cycle_duration / timestep)
        self.total_steps = self.steps_per_cycle * actuation_cycles

        print(f"True Parallel Evaluator: {self.total_steps} steps, {timestep}s timestep")

    def evaluate_batch(self, robots, controllers):
        """Evaluate ALL robots in parallel on ONE GPU array"""
        batch_size = len(robots)
        print(f"\nEvaluating {batch_size} robots in TRUE PARALLEL on GPU...")

        # Strategy: Create ONE large physics engine with ALL robots
        # Each robot gets its own node/spring range in the arrays

        # Calculate total size needed
        total_nodes = sum(len(r.nodes) for r in robots)
        total_springs = sum(len(r.springs) for r in robots)

        print(f"  Total nodes: {total_nodes}, Total springs: {total_springs}")

        if total_nodes > 10000 or total_springs > 50000:
            print(f"  WARNING: Large batch, may exceed GPU memory")

        # Create combined physics engine
        physics = OptimizedCUDAPhysicsEngine(
            max_nodes=total_nodes + 100,
            max_springs=total_springs + 500,
            default_timestep=self.timestep,
            actuation_frequency=self.actuation_freq
        )

        # Add ALL robots to the SAME physics engine
        robot_node_ranges = []  # Track which nodes belong to which robot
        robot_initial_coms = []

        current_node_offset = 0

        for i, robot in enumerate(robots):
            physics.add_robot(robot)

            # Track this robot's node range
            num_nodes = len(robot.nodes)
            node_range = (current_node_offset, current_node_offset + num_nodes)
            robot_node_ranges.append(node_range)
            current_node_offset += num_nodes

            # Get initial COM
            robot_positions = physics.get_positions()[node_range[0]:node_range[1]]
            initial_com = robot.get_center_of_mass(robot_positions)
            robot_initial_coms.append(initial_com)

        print(f"  Added {batch_size} robots to single physics engine")

        # Run simulation (ALL robots simulated together!)
        print(f"  Running {self.total_steps} physics steps...")

        for step in range(self.total_steps):
            # Update controllers if needed
            if step % max(1, self.steps_per_cycle // 10) == 0:
                for i, (robot, controller) in enumerate(zip(robots, controllers)):
                    if controller is not None:
                        start_idx, end_idx = robot_node_ranges[i]
                        robot_positions = physics.get_positions()[start_idx:end_idx]
                        com = robot.get_center_of_mass(robot_positions)

                        if not np.any(np.isnan(com)):
                            sensor_data = np.concatenate([com, np.zeros(9)])
                            control = controller.step(self.timestep, sensor_data)
                            # Set actuator signals for this robot's actuators
                            physics.set_actuator_signals(control)

            # ONE physics step updates ALL robots simultaneously! ✓
            physics.step(self.timestep)

            # Progress reporting
            if step % (self.steps_per_cycle * 2) == 0:
                cycle = step // self.steps_per_cycle
                print(f"    Cycle {cycle}/{self.actuation_cycles}")

        # Calculate fitness for each robot
        fitness_scores = []

        all_positions = physics.get_positions()

        for i, robot in enumerate(robots):
            start_idx, end_idx = robot_node_ranges[i]
            robot_positions = all_positions[start_idx:end_idx]

            final_com = robot.get_center_of_mass(robot_positions)
            initial_com = robot_initial_coms[i]

            # Fitness = horizontal displacement / (body_length * time)
            displacement = np.linalg.norm(final_com[:2] - initial_com[:2])  # XZ plane
            body_size = robot.get_bounding_box_size()
            body_length = max(body_size[0], 0.001)

            fitness = displacement / (body_length * self.simulation_time)

            # Clamp to valid range
            if np.isnan(fitness) or np.isinf(fitness):
                fitness = 0.0

            fitness = max(0.0, min(fitness, 1000.0))  # Prevent extreme values
            fitness += 0.0001  # Small existence bonus

            fitness_scores.append(fitness)

        print(f"  Fitness range: [{np.min(fitness_scores):.4f}, {np.max(fitness_scores):.4f}]")

        return np.array(fitness_scores)
