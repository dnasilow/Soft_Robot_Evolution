"""
MuJoCo Tendon Evaluator

Bridges the EvolutionaryAlgorithm (which calls evaluate_batch(robots, controllers))
and MuJoCoTendonPhysics.

API contract
------------
evaluate_batch(genomes, controllers) -> np.ndarray of fitness values

  genomes:     list of voxel grids (each is a 3-D np.ndarray)
  controllers: list of CPGController instances (or None per entry)
               - None  → create a fresh CPGController sized for this robot
               - wrong num_actuators → replace with a fresh one silently

Parallelism
-----------
Pass n_workers > 1 to evaluate_batch to use multiprocessing.Pool.
Each worker spawns its own MuJoCoTendonPhysics instance (MuJoCo is
process-safe but not thread-safe).  The _eval_worker function must
stay at module level for pickling on Windows (spawn mode).
"""
import os
import numpy as np
from multiprocessing import Pool
from typing import List, Optional

from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
from src.physics.mujoco_tendon_converter import count_active_tendons


# ------------------------------------------------------------------
# Module-level worker (must be top-level for Windows spawn pickling)
# ------------------------------------------------------------------
def _eval_worker(args):
    """Evaluate one robot in a worker process."""
    genome, controller, params = args
    try:
        engine = MuJoCoTendonPhysics(
            default_timestep    = params['timestep'],
            actuation_frequency = params['actuation_frequency'],
            actuation_amplitude = params['actuation_amplitude'],
        )
        engine.load_robot(
            genome,
            voxel_size     = params['voxel_size'],
            initial_height = params['initial_height'],
        )
        controller = _reconcile_controller(controller, engine.num_active_tendons)
        if controller is not None:
            engine.set_controller(controller)
        return engine.get_fitness(
            simulation_time = params['simulation_time'],
            settle_time     = params['settle_time'],
        )
    except Exception:
        return 0.0


class MuJoCoTendonEvaluator:
    """
    MuJoCo evaluator using the tendon-based physics engine.

    n_workers=1  → sequential (original behaviour, one reused engine)
    n_workers>1  → multiprocessing.Pool with that many worker processes;
                   each worker creates its own engine instance.
    """

    def __init__(
        self,
        simulation_time:     float = 5.0,
        settle_time:         float = 0.5,
        timestep:            float = 0.0005,
        actuation_frequency: float = 10.0,
        actuation_amplitude: float = 0.08,
        voxel_size:          float = 0.01,
        initial_height:      float = 0.0,
        n_workers:           int   = 1,
    ):
        self.simulation_time = simulation_time
        self.settle_time     = settle_time
        self.voxel_size      = voxel_size
        self.initial_height  = initial_height
        self.n_workers       = max(1, n_workers)

        # Params dict passed to every worker (plain Python types → picklable)
        self._params = {
            'timestep':            timestep,
            'actuation_frequency': actuation_frequency,
            'actuation_amplitude': actuation_amplitude,
            'voxel_size':          voxel_size,
            'initial_height':      initial_height,
            'simulation_time':     simulation_time,
            'settle_time':         settle_time,
        }

        # Sequential engine — used when n_workers==1 and by evaluate_single
        self.engine = MuJoCoTendonPhysics(
            default_timestep    = timestep,
            actuation_frequency = actuation_frequency,
            actuation_amplitude = actuation_amplitude,
        )

    # ------------------------------------------------------------------
    def evaluate_batch(
        self,
        genomes:     List[np.ndarray],
        controllers: Optional[List] = None,
    ) -> np.ndarray:
        """
        Evaluate a list of voxel-grid genomes.

        Args:
            genomes:     list of 3-D numpy arrays (voxel material IDs)
            controllers: matching list of CPGController / None.
                         Pass None for the whole list to use open-loop actuation.

        Returns:
            1-D numpy array of fitness values (horizontal distance in metres).
        """
        if controllers is None:
            controllers = [None] * len(genomes)

        # ── Parallel path ──────────────────────────────────────────────
        if self.n_workers > 1:
            args = [(g, c, self._params) for g, c in zip(genomes, controllers)]
            with Pool(self.n_workers) as pool:
                fitnesses = pool.map(_eval_worker, args, chunksize=1)
            return np.array(fitnesses, dtype=float)

        # ── Sequential path ────────────────────────────────────────────
        fitnesses = []
        for i, (genome, controller) in enumerate(zip(genomes, controllers)):
            try:
                self.engine.load_robot(
                    genome,
                    voxel_size     = self.voxel_size,
                    initial_height = self.initial_height,
                )
                controller = _reconcile_controller(
                    controller, self.engine.num_active_tendons
                )
                if controller is not None:
                    self.engine.set_controller(controller)
                fitness = self.engine.get_fitness(
                    simulation_time = self.simulation_time,
                    settle_time     = self.settle_time,
                )
                fitnesses.append(fitness)
            except Exception as exc:
                print(f"  [Evaluator] Robot {i} failed: {exc}")
                fitnesses.append(0.0)

        return np.array(fitnesses, dtype=float)

    # ------------------------------------------------------------------
    def evaluate_single(self, genome: np.ndarray, controller=None) -> float:
        """Convenience wrapper for evaluating one robot."""
        return float(self.evaluate_batch([genome], [controller])[0])


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------
def _reconcile_controller(controller, num_active: int):
    """
    Return a controller that matches num_active.
    - None → None if num_active==0, else fresh CPGController
    - wrong size → fresh CPGController
    """
    if num_active == 0:
        return None

    try:
        from src.evolution.controllers import CPGController
    except ImportError:
        return None

    if controller is None:
        return CPGController(num_active)

    if controller.num_actuators != num_active:
        return CPGController(num_active)

    return controller
