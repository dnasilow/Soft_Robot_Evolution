"""
MuJoCo Physics Engine with Tendon-Based Actuation

Actuation mechanism
-------------------
- Every adjacent voxel pair has a spatial tendon + position actuator
- force = kp * (ctrl - current_length)   [per-tendon kp from material types]
- Active tendons:   ctrl = rest * (1 + amplitude * signal)
    - Without controller: signal = sin(omega*t + base_phase)
    - With CPGController:  signal = cpg.step(dt)[active_tendon_index]
- Passive tendons:  ctrl = rest  (holds shape)

Settled measurement
-------------------
get_fitness() runs 0.5 s of actuation before recording start position,
so initial-contact noise is excluded from the locomotion score.
"""
import numpy as np
import mujoco
from typing import Optional, List, Dict
from src.physics.mujoco_tendon_converter import voxel_to_tendon_xml


class MuJoCoTendonPhysics:
    """Tendon-based soft robot physics engine."""

    def __init__(
        self,
        default_timestep: float = 0.0005,
        actuation_frequency: float = 10.0,
        actuation_amplitude: float = 0.20,
    ):
        self.default_timestep    = default_timestep
        self.actuation_frequency = actuation_frequency
        self.actuation_amplitude = actuation_amplitude

        self.model: Optional[mujoco.MjModel] = None
        self.data:  Optional[mujoco.MjData]  = None
        self.current_time = 0.0

        # Populated by load_robot()
        self.tendon_info:   List[Dict]           = []
        self.rest_lengths:  Optional[np.ndarray] = None

        # Precomputed arrays (set in _precompute_actuation_arrays)
        self._active_mask:  Optional[np.ndarray] = None   # bool (n_tendons,)
        self._base_phases:  Optional[np.ndarray] = None   # float (n_tendons,)
        self._active_idx:   Optional[np.ndarray] = None   # int indices of active tendons

        # Optional CPGController (set via set_controller())
        self._controller = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_robot(
        self,
        voxel_grid: np.ndarray,
        voxel_size: float = 0.01,
        initial_height: float = 0.0,
    ) -> None:
        """Load robot from voxel grid, record rest lengths, precompute arrays."""
        xml, self.tendon_info = voxel_to_tendon_xml(voxel_grid, voxel_size, initial_height)
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data  = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        self.rest_lengths = np.array(self.data.ten_length, copy=True)
        self.current_time = 0.0
        self._controller  = None
        self._precompute_actuation_arrays()

    def _precompute_actuation_arrays(self) -> None:
        """Build numpy arrays used by the vectorised apply_actuation()."""
        n = len(self.tendon_info)
        active_mask = np.zeros(n, dtype=bool)
        base_phases = np.zeros(n, dtype=float)

        for k, info in enumerate(self.tendon_info):
            if info['is_active']:
                active_mask[k] = True
                base_phases[k] = info['base_phase']

        self._active_mask = active_mask
        self._base_phases = base_phases
        self._active_idx  = np.where(active_mask)[0]

    # ------------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------------
    def set_controller(self, controller) -> None:
        """
        Attach a CPGController (or None to remove it).
        The controller must have num_actuators == number of active tendons.
        """
        if controller is not None:
            expected = int(np.sum(self._active_mask))
            if controller.num_actuators != expected:
                raise ValueError(
                    f"Controller has {controller.num_actuators} actuators but "
                    f"robot has {expected} active tendons."
                )
        self._controller = controller

    @property
    def num_active_tendons(self) -> int:
        """Number of tendons connected to at least one active voxel."""
        if self._active_mask is None:
            return 0
        return int(np.sum(self._active_mask))

    # ------------------------------------------------------------------
    # Actuation (vectorised — no Python loop per step)
    # ------------------------------------------------------------------
    def apply_actuation(self) -> None:
        """Set ctrl for every tendon actuator. O(n) numpy, no Python loop."""
        if self.rest_lengths is None:
            return

        ctrl = self.rest_lengths.copy()   # start from rest

        if self._controller is not None:
            # CPGController path: one signal per active tendon
            signals = self._controller.step(self.default_timestep)   # (n_active,)
            signals = np.clip(signals, -1.0, 1.0)
            ctrl[self._active_idx] *= (1.0 + self.actuation_amplitude * signals)
        else:
            # Hardcoded sinusoidal path (used during testing / no controller)
            if self._active_mask.any():
                omega = 2.0 * np.pi * self.actuation_frequency
                t_sig = self.actuation_amplitude * np.sin(
                    omega * self.current_time + self._base_phases
                )
                ctrl = np.where(self._active_mask, self.rest_lengths * (1.0 + t_sig), ctrl)

        self.data.ctrl[:] = ctrl

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------
    def step(self) -> None:
        """Advance simulation by one timestep."""
        if self.model is None:
            return
        self.apply_actuation()
        mujoco.mj_step(self.model, self.data)
        self.current_time += self.default_timestep

    # ------------------------------------------------------------------
    # Position / fitness
    # ------------------------------------------------------------------
    def get_position(self) -> np.ndarray:
        """Centre-of-mass of all voxel bodies (excludes worldbody at index 0)."""
        if self.data is None:
            return np.zeros(3)
        return np.mean(self.data.xpos[1:self.model.nbody], axis=0)

    def get_fitness(
        self,
        simulation_time: float = 5.0,
        settle_time:     float = 0.5,
    ) -> float:
        """
        Run simulation and return horizontal distance (X-Y plane) travelled.

        Args:
            simulation_time: Duration to measure after settling (seconds)
            settle_time:     Settling period before measurement starts (seconds)
                             Actuation runs during settling so the robot reaches
                             its oscillating steady-state before we record position.
        """
        # Settle — run actuation but don't count this movement
        settle_steps = int(settle_time / self.default_timestep)
        for _ in range(settle_steps):
            self.step()

        # Record position after settling
        initial_pos = self.get_position()

        # Measure
        measure_steps = int(simulation_time / self.default_timestep)
        for _ in range(measure_steps):
            self.step()

        final_pos = self.get_position()

        # Horizontal displacement (Z is vertical in MuJoCo Z-up)
        return float(np.sqrt(
            (final_pos[0] - initial_pos[0]) ** 2 +
            (final_pos[1] - initial_pos[1]) ** 2
        ))
