"""
Fitness evaluation functions for soft robot evolution.

Evaluates robot performance based on locomotion distance, energy efficiency,
structural integrity, and gait stability.
"""

import numpy as np
import cupy as cp
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot


class FitnessEvaluator:
    """
    Evaluates soft robot fitness based on multiple performance metrics.

    Primary fitness: Horizontal locomotion distance (X-Z plane)
    Secondary metrics: Energy efficiency, structural integrity, gait stability
    """

    def __init__(self,
                 sim_time: float = 10.0,
                 timestep: float = 0.0001,
                 enable_detailed_metrics: bool = False):
        """
        Initialize fitness evaluator.

        Args:
            sim_time: Simulation duration in seconds
            timestep: Physics timestep (default: 0.0001s = 0.1ms)
            enable_detailed_metrics: If True, compute energy/stability metrics (slower)
        """
        self.sim_time = sim_time
        self.timestep = timestep
        self.enable_detailed_metrics = enable_detailed_metrics

        # Physics engine (reused across evaluations for efficiency)
        self.physics_engine = None

    def evaluate_fitness(self,
                        robot: VoxelRobot,
                        actuation_frequency: float = 2.0,
                        actuation_amplitude: float = 0.2) -> Dict[str, float]:
        """
        Evaluate robot fitness through physical simulation.

        Args:
            robot: VoxelRobot instance to evaluate
            actuation_frequency: Frequency of sinusoidal actuation (Hz)
            actuation_amplitude: Actuation amplitude (0.0-1.0, proportion of rest length)

        Returns:
            Dictionary containing:
                - 'fitness': Primary fitness score (horizontal distance in meters)
                - 'distance_horizontal': Horizontal displacement (X-Z plane) in meters
                - 'distance_forward': Forward displacement (X-axis only) in meters
                - 'distance_3d': Total 3D displacement in meters
                - 'final_height': Final center-of-mass Y coordinate (meters)
                - 'efficiency': Distance per actuation cycle (m/cycle) [if enabled]
                - 'stability': Velocity variance (lower = more stable gait) [if enabled]
                - 'integrity': Structural integrity (1.0 = no deformation) [if enabled]
        """
        # Initialize or reset physics engine
        if self.physics_engine is None:
            max_nodes = 500
            max_springs = 2000
            self.physics_engine = CUDAPhysicsEngine(
                max_nodes=max_nodes,
                max_springs=max_springs,
                actuation_frequency=actuation_frequency
            )
        else:
            self.physics_engine.reset()
            self.physics_engine.actuation_frequency = actuation_frequency

        # Add robot to physics
        self.physics_engine.add_robot(robot)

        # Get initial state
        initial_positions = self.physics_engine.get_positions()
        initial_com = robot.get_center_of_mass(initial_positions)

        # Store initial structure dimensions for integrity check
        if self.enable_detailed_metrics:
            initial_dimensions = self._compute_bounding_box(initial_positions)

        # Tracking for detailed metrics
        if self.enable_detailed_metrics:
            velocity_samples = []
            sample_interval = 0.1  # Sample every 0.1 seconds
            last_sample_time = 0.0

        # Run simulation
        sim_time = 0.0
        num_steps = int(self.sim_time / self.timestep)

        for step in range(num_steps):
            self.physics_engine.step(dt=self.timestep)
            sim_time += self.timestep

            # Sample velocities for stability metric
            if self.enable_detailed_metrics and sim_time >= last_sample_time + sample_interval:
                velocities = self.physics_engine.get_velocities()
                mean_velocity = np.mean(velocities, axis=0)
                velocity_samples.append(mean_velocity)
                last_sample_time = sim_time

        # Get final state
        final_positions = self.physics_engine.get_positions()
        final_com = robot.get_center_of_mass(final_positions)

        # Compute displacement
        displacement = final_com - initial_com

        # Primary fitness: Horizontal distance (X-Z plane, ignore vertical)
        distance_horizontal = np.sqrt(displacement[0]**2 + displacement[2]**2)

        # Secondary metrics
        distance_forward = displacement[0]  # X-axis only (can be negative)
        distance_3d = np.linalg.norm(displacement)
        final_height = final_com[1]

        # Prepare results
        results = {
            'fitness': float(distance_horizontal),  # PRIMARY FITNESS
            'distance_horizontal': float(distance_horizontal),
            'distance_forward': float(distance_forward),
            'distance_3d': float(distance_3d),
            'final_height': float(final_height),
        }

        # Detailed metrics (optional, more expensive)
        if self.enable_detailed_metrics:
            # Energy efficiency: distance per actuation cycle
            num_cycles = self.sim_time * actuation_frequency
            efficiency = distance_horizontal / num_cycles if num_cycles > 0 else 0.0
            results['efficiency'] = float(efficiency)

            # Gait stability: variance in velocity
            if len(velocity_samples) > 1:
                velocity_samples = np.array(velocity_samples)
                # Compute variance of horizontal velocity components
                velocity_variance = np.var(velocity_samples[:, 0]) + np.var(velocity_samples[:, 2])
                results['stability'] = float(velocity_variance)
            else:
                results['stability'] = 0.0

            # Structural integrity: measure deformation
            final_dimensions = self._compute_bounding_box(final_positions)
            dimension_changes = np.abs(final_dimensions - initial_dimensions) / (initial_dimensions + 1e-6)
            max_deformation = np.max(dimension_changes)
            integrity = max(0.0, 1.0 - max_deformation)  # 1.0 = no deformation
            results['integrity'] = float(integrity)

        return results

    def _compute_bounding_box(self, positions: np.ndarray) -> np.ndarray:
        """
        Compute bounding box dimensions [X, Y, Z].

        Args:
            positions: Node positions (N x 3)

        Returns:
            Array of [width, height, depth] in meters
        """
        min_pos = np.min(positions, axis=0)
        max_pos = np.max(positions, axis=0)
        return max_pos - min_pos

    def evaluate_batch(self,
                      robots: list,
                      actuation_frequency: float = 2.0,
                      actuation_amplitude: float = 0.2) -> list:
        """
        Evaluate multiple robots sequentially.

        For true parallel evaluation, use BatchFitnessEvaluator.

        Args:
            robots: List of VoxelRobot instances
            actuation_frequency: Actuation frequency (Hz)
            actuation_amplitude: Actuation amplitude (0.0-1.0)

        Returns:
            List of fitness dictionaries (one per robot)
        """
        results = []
        for robot in robots:
            fitness = self.evaluate_fitness(robot, actuation_frequency, actuation_amplitude)
            results.append(fitness)
        return results


class BatchFitnessEvaluator:
    """
    Parallel fitness evaluation for multiple robots using GPU batching.

    This evaluator can simulate multiple robots simultaneously on GPU,
    significantly accelerating evolution by evaluating entire populations in parallel.

    WARNING: This is a more complex implementation requiring careful memory management.
    Use FitnessEvaluator for initial testing, then upgrade to this for production.
    """

    def __init__(self,
                 sim_time: float = 10.0,
                 timestep: float = 0.0001,
                 batch_size: int = 5):
        """
        Initialize batch evaluator.

        Args:
            sim_time: Simulation duration in seconds
            timestep: Physics timestep
            batch_size: Number of robots to evaluate in parallel
        """
        self.sim_time = sim_time
        self.timestep = timestep
        self.batch_size = batch_size

        # TODO: Implement parallel GPU evaluation
        # This requires:
        # 1. Batched GPU memory allocation (separate regions per robot)
        # 2. Batched spring force computation
        # 3. Batched integration
        # 4. Synchronization and result collection

        raise NotImplementedError(
            "Parallel batch evaluation not yet implemented. "
            "Use FitnessEvaluator for sequential evaluation."
        )


def evaluate_robot_fitness(robot: VoxelRobot,
                          sim_time: float = 10.0,
                          actuation_frequency: float = 2.0,
                          actuation_amplitude: float = 0.2,
                          detailed_metrics: bool = False) -> Dict[str, float]:
    """
    Convenience function for single robot evaluation.

    Args:
        robot: VoxelRobot to evaluate
        sim_time: Simulation duration (seconds)
        actuation_frequency: Actuation frequency (Hz)
        actuation_amplitude: Actuation amplitude (0.0-1.0)
        detailed_metrics: Enable efficiency/stability/integrity metrics

    Returns:
        Fitness dictionary with 'fitness' key as primary score
    """
    evaluator = FitnessEvaluator(
        sim_time=sim_time,
        enable_detailed_metrics=detailed_metrics
    )
    return evaluator.evaluate_fitness(robot, actuation_frequency, actuation_amplitude)
