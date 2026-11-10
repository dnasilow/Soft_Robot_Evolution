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


def _make_engine(params):
    """Construct the physics engine (flex or tendon)."""
    kw = dict(
        default_timestep    = params['timestep'],
        actuation_frequency = params['actuation_frequency'],
        actuation_amplitude = params['actuation_amplitude'],
        fitness_mode        = params.get('fitness_mode', 'directed'),
    )
    if params.get('use_flex', False):
        from src.physics.mujoco_flex_physics import MuJoCoFlexPhysics
        return MuJoCoFlexPhysics(wave_phase_n=params.get('wave_phase_n'), **kw)
    # What the score measures (tendon and beam share get_fitness; flex has its own).
    kw.update(direction=params.get('direction', 'forward'),
              divide_by=params.get('divide_by', 'body'),
              workspace_voxels=params.get('workspace_voxels'))
    if params.get('body', 'springs') == 'beam':
        # Voxelyze-style bodies; picks its own stable time step per robot.
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        return MuJoCoBeamPhysics(max_voxels=params.get('max_voxels'),
                                 friction=params.get('friction'),
                                 poisson=params.get('poisson', True),
                                 dt_rule=params.get('dt_rule', 'voxelyze'),
                                 materials=params.get('materials', 'evosoro'),
                                 gravity=params.get('gravity'),
                                 floor_contact=params.get('floor_contact', 'mujoco'),
                                 phase_mode=params.get('phase_mode', 'offset'), **kw)
    # max_voxels is tendon-only (normalises the musclecost penalty); workers re-import
    # genome_config defaults, so the parent's --max-voxels must be threaded explicitly.
    # friction likewise (None = the original floor).
    return MuJoCoTendonPhysics(max_voxels=params.get('max_voxels'),
                               friction=params.get('friction'), **kw)


def _fitness_kw(params):
    """Optional get_fitness overrides; absent keys keep the engine defaults unchanged."""
    kw = {}
    if params.get('early_term_threshold') is not None:
        kw['early_term_threshold'] = params['early_term_threshold']
    if params.get('early_term_fraction') is not None:
        kw['early_term_fraction'] = params['early_term_fraction']
    return kw


# ------------------------------------------------------------------
# Module-level worker (must be top-level for Windows spawn pickling)
# ------------------------------------------------------------------
def _eval_worker(args):
    """Evaluate one robot in a worker process."""
    genome, controller, gait_param, params = args
    want_desc = params.get('return_descriptors', False)
    try:
        engine = _make_engine(params)
        engine.load_robot(
            genome,
            voxel_size     = params['voxel_size'],
            initial_height = params['initial_height'],
            gait_params    = gait_param,
        )
        # Flex v1 is open-loop only; skip controller attach entirely for flex.
        # When attach_controller is False (A1: Cheney-faithful open-loop), leave the
        # engine controller-free so apply_actuation() drives each active tendon with the
        # material-derived base phase at the global actuation frequency.
        if params.get('attach_controller', True) and not params.get('use_flex', False):
            controller = _reconcile_controller(controller, engine.num_active_tendons)
            if controller is not None:
                engine.set_controller(controller)
        return engine.get_fitness(
            simulation_time    = params['simulation_time'],
            settle_time        = params['settle_time'],
            return_descriptors = want_desc,
            **_fitness_kw(params),
        )
    except Exception:
        return (0.0, (0.0, 0.0)) if want_desc else 0.0


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
        attach_controller:   bool  = True,
        use_flex:            bool  = False,
        fitness_mode:        str   = "directed",
        wave_phase_n              = None,
        max_voxels:          int   = None,
        friction:            dict  = None,   # floor friction spec (see MuJoCoTendonPhysics)
        early_term_threshold: float = None,  # BL needed at the check point (None = 0.05)
        early_term_fraction:  float = None,  # check point as a fraction of the window (None = 0.2)
        body:                str   = "springs",  # springs (tendon model) | beam (Voxelyze bonds)
        poisson:             bool  = True,   # beam only: Voxelyze volumetric coupling
        dt_rule:             str   = "voxelyze",   # beam only: voxelyze | ours
        materials:           str   = "evosoro",    # beam only: evosoro | cheney2013
        gravity:             float = None,         # beam only: m/s^2 (None = the preset's own)
        floor_contact:       str   = "mujoco",     # beam only: mujoco | voxelyze penalty floor
        phase_mode:          str   = "offset",     # beam only: control CPPN offsets vs replaces
        direction:           str   = "forward",    # score: +X component | any-direction 3D
        divide_by:           str   = "body",       # score unit: own body length | fixed workspace
        workspace_voxels:    int   = None,         # workspace width in voxels (divide_by='workspace')
    ):
        self.simulation_time   = simulation_time
        self.settle_time       = settle_time
        self.voxel_size        = voxel_size
        self.initial_height    = initial_height
        self.n_workers         = max(1, n_workers)
        self.attach_controller = attach_controller
        self.use_flex          = use_flex
        self._pool             = None   # persistent worker pool (created lazily)

        # Params dict passed to every worker (plain Python types → picklable)
        self._params = {
            'timestep':            timestep,
            'actuation_frequency': actuation_frequency,
            'actuation_amplitude': actuation_amplitude,
            'voxel_size':          voxel_size,
            'initial_height':      initial_height,
            'simulation_time':     simulation_time,
            'settle_time':         settle_time,
            'attach_controller':   attach_controller,
            'use_flex':            use_flex,
            'fitness_mode':        fitness_mode,
            'wave_phase_n':        wave_phase_n,
            'max_voxels':          max_voxels,
            'friction':            friction,
            'early_term_threshold': early_term_threshold,
            'early_term_fraction':  early_term_fraction,
            'body':                body,
            'poisson':             poisson,
            'dt_rule':             dt_rule,
            'materials':           materials,
            'gravity':             gravity,
            'floor_contact':       floor_contact,
            'phase_mode':          phase_mode,
            'direction':           direction,
            'divide_by':           divide_by,
            'workspace_voxels':    workspace_voxels,
        }

        # Sequential engine — used when n_workers==1 and by evaluate_single
        self.engine = _make_engine(self._params)

    # ------------------------------------------------------------------
    def evaluate_batch(
        self,
        genomes:     List[np.ndarray],
        controllers: Optional[List] = None,
        with_descriptors: bool = False,
        gait_params: Optional[List] = None,
    ):
        """
        Evaluate a list of voxel-grid genomes.

        Args:
            genomes:     list of 3-D numpy arrays (voxel material IDs)
            controllers: matching list of CPGController / None.
                         Pass None for the whole list to use open-loop actuation.
            with_descriptors: if True, also return per-robot gait descriptors
                         (mean COM height, bounce) for MAP-Elites.

        Returns:
            1-D numpy array of fitness values (forward body-lengths), or
            (fitnesses, descriptors) when with_descriptors=True.
        """
        if controllers is None:
            controllers = [None] * len(genomes)
        if gait_params is None:
            gait_params = [None] * len(genomes)

        params = dict(self._params)
        params['return_descriptors'] = with_descriptors

        # ── Parallel path (one persistent pool — see _get_pool) ────────────
        if self.n_workers > 1:
            args = [(g, c, gp, params) for g, c, gp in zip(genomes, controllers, gait_params)]
            pool = self._get_pool()
            results = pool.map(_eval_worker, args, chunksize=1)
            if with_descriptors:
                fits  = np.array([r[0] for r in results], dtype=float)
                descs = [r[1] for r in results]
                return fits, descs
            return np.array(results, dtype=float)

        # ── Sequential path ────────────────────────────────────────────
        fitnesses, descs = [], []
        for i, (genome, controller, gp) in enumerate(zip(genomes, controllers, gait_params)):
            try:
                self.engine.load_robot(
                    genome,
                    voxel_size     = self.voxel_size,
                    initial_height = self.initial_height,
                    gait_params    = gp,
                )
                if self.attach_controller and not self.use_flex:
                    controller = _reconcile_controller(
                        controller, self.engine.num_active_tendons
                    )
                    if controller is not None:
                        self.engine.set_controller(controller)
                else:
                    self.engine.set_controller(None)
                res = self.engine.get_fitness(
                    simulation_time    = self.simulation_time,
                    settle_time        = self.settle_time,
                    return_descriptors = with_descriptors,
                    **_fitness_kw(self._params),
                )
                if with_descriptors:
                    fitnesses.append(res[0]); descs.append(res[1])
                else:
                    fitnesses.append(res)
            except Exception as exc:
                print(f"  [Evaluator] Robot {i} failed: {exc}")
                fitnesses.append(0.0); descs.append((0.0, 0.0))

        if with_descriptors:
            return np.array(fitnesses, dtype=float), descs
        return np.array(fitnesses, dtype=float)

    # ------------------------------------------------------------------
    def evaluate_single(self, genome: np.ndarray, controller=None) -> float:
        """Convenience wrapper for evaluating one robot."""
        return float(self.evaluate_batch([genome], [controller])[0])

    # ------------------------------------------------------------------
    # Persistent pool lifecycle
    # ------------------------------------------------------------------
    def _get_pool(self) -> Pool:
        """Create the worker pool on first use, then reuse it for the whole run."""
        if self._pool is None:
            self._pool = Pool(self.n_workers)
        return self._pool

    def close(self) -> None:
        """Shut the persistent worker pool down. Safe to call multiple times."""
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None

    def __del__(self):
        # Best-effort cleanup if the caller forgets to close().
        try:
            self.close()
        except Exception:
            pass


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
