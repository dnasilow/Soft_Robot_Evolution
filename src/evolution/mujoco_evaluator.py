"""Batch evaluator for evolution using MuJoCo physics"""
import numpy as np
from typing import List, Tuple
from src.physics.mujoco_physics import MuJoCoPhysicsEngine
from src.evolution.genome_config import VOXEL_GRID_SHAPE


class MuJoCoBatchEvaluator:
    """
    Evaluates multiple robots sequentially using MuJoCo physics.

    Note: MuJoCo doesn't support true parallel simulation like CUDA,
    so robots are evaluated one at a time. This is still much faster
    than the broken CuPy implementation because the physics is stable!
    """

    def __init__(self,
                 simulation_time: float = 5.0,
                 timestep: float = 0.0005,
                 actuation_frequency: float = 2.0):
        """
        Initialize batch evaluator.

        Args:
            simulation_time: Simulation time per robot in seconds
            timestep: Physics timestep in seconds
            actuation_frequency: Actuation frequency in Hz
        """
        self.simulation_time = simulation_time
        self.timestep = timestep
        self.actuation_frequency = actuation_frequency

        # Reusable engine instance
        self.engine = MuJoCoPhysicsEngine(
            default_timestep=timestep,
            actuation_frequency=actuation_frequency
        )

    def evaluate_batch(self, genomes: List[np.ndarray]) -> np.ndarray:
        """
        Evaluate a batch of robot genomes.

        Args:
            genomes: List of voxel grids (each is 3D numpy array)

        Returns:
            Array of fitness values (one per genome)
        """
        fitnesses = []

        for i, genome in enumerate(genomes):
            try:
                # Load robot
                self.engine.load_robot(genome, voxel_size=0.01)

                # Evaluate fitness
                fitness = self.engine.get_fitness(simulation_time=self.simulation_time)

                fitnesses.append(fitness)

            except Exception as e:
                # If robot fails to load or simulate, give it zero fitness
                print(f"Warning: Robot {i} failed to evaluate: {e}")
                fitnesses.append(0.0)

        return np.array(fitnesses)

    def evaluate_single(self, genome: np.ndarray) -> float:
        """
        Evaluate a single robot genome.

        Args:
            genome: Voxel grid (3D numpy array)

        Returns:
            Fitness value
        """
        results = self.evaluate_batch([genome])
        return float(results[0])


def create_mujoco_evaluator(simulation_time: float = 5.0,
                            timestep: float = 0.0005,
                            actuation_frequency: float = 2.0) -> MuJoCoBatchEvaluator:
    """
    Factory function to create MuJoCo batch evaluator.

    Args:
        simulation_time: Simulation time per robot in seconds
        timestep: Physics timestep in seconds
        actuation_frequency: Actuation frequency in Hz

    Returns:
        MuJoCoBatchEvaluator instance
    """
    return MuJoCoBatchEvaluator(
        simulation_time=simulation_time,
        timestep=timestep,
        actuation_frequency=actuation_frequency
    )
