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
        self.voxel_size          = 0.01   # set per-robot in load_robot; used for body-length norm

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
        self.voxel_size = voxel_size
        xml, self.tendon_info = voxel_to_tendon_xml(voxel_grid, voxel_size, initial_height)
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data  = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        # Only active tendons have position actuators; rest_lengths tracks those.
        self.rest_lengths = np.array(self.data.actuator_length, copy=True)
        self.current_time = 0.0
        self._controller  = None
        self._precompute_actuation_arrays()

    def _precompute_actuation_arrays(self) -> None:
        """Build base-phase array for the open-loop sinusoidal fallback.

        After the passive-spring optimisation, model.nu == num_active_tendons,
        so _base_phases is indexed 0..nu-1 and no active-mask indexing is needed.
        """
        self._base_phases = np.array(
            [info['base_phase'] for info in self.tendon_info if info['is_active']],
            dtype=float,
        )
        # Keep _active_mask/_active_idx as None — no longer used.
        self._active_mask = None
        self._active_idx  = None

    # ------------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------------
    def set_controller(self, controller) -> None:
        """
        Attach a CPGController (or None to remove it).
        The controller must have num_actuators == number of active tendons.
        """
        if controller is not None:
            if controller.num_actuators != self.num_active_tendons:
                raise ValueError(
                    f"Controller has {controller.num_actuators} actuators but "
                    f"robot has {self.num_active_tendons} active tendons."
                )
        self._controller = controller

    @property
    def num_active_tendons(self) -> int:
        """Number of position-actuated (active) tendons == model.nu."""
        if self.model is None:
            return 0
        return int(self.model.nu)

    # ------------------------------------------------------------------
    # Actuation (vectorised — no Python loop per step)
    # ------------------------------------------------------------------
    def apply_actuation(self) -> None:
        """Set ctrl for every active-tendon actuator. O(n) numpy, no Python loop.

        model.nu == num_active_tendons after the passive-spring optimisation,
        so data.ctrl and rest_lengths are both indexed 0..nu-1 with no masking.
        """
        if self.rest_lengths is None or self.model.nu == 0:
            return

        if self._controller is not None:
            signals = self._controller.step(self.default_timestep)   # (nu,)
            signals = np.clip(signals, -1.0, 1.0)
            self.data.ctrl[:] = self.rest_lengths * (1.0 + self.actuation_amplitude * signals)
        else:
            omega = 2.0 * np.pi * self.actuation_frequency
            t_sig = self.actuation_amplitude * np.sin(
                omega * self.current_time + self._base_phases
            )
            self.data.ctrl[:] = self.rest_lengths * (1.0 + t_sig)

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
        simulation_time:      float = 5.0,
        settle_time:          float = 0.5,
        early_term_fraction:  float = 0.2,
        early_term_threshold: float = 0.05,   # body-lengths of forward (+X) progress
        return_descriptors:   bool  = False,  # also return (mean COM height, bounce) for MAP-Elites
    ):
        """
        Run simulation and return FORWARD (+X) distance in BODY LENGTHS, penalised
        by ground_fraction:

            fitness = max(0, forward_displacement / body_length) * ground_fraction

        - **Directed** (+X only): spinning, drift and backward motion score 0, so the
          objective selects for real forward locomotion (more transferable than the
          old undirected net-displacement metric).
        - **Body-length normalised**: comparable across body sizes (Cheney's unit).
          body_length = largest bounding-box extent of the undeformed body + one voxel.
        - **ground_fraction**: fraction of measurement steps the COM stays below 2× its
          *robust resting height* — the median COM-z over the final quarter of settling,
          so a mid-settle bounce no longer inflates the threshold (the old
          `initial_pos[2]*3.0` bug that quietly rewarded jumping).

        Early termination: at `early_term_fraction` of the window, if forward progress
        is below `early_term_threshold` body-lengths the robot is judged non-locomoting
        and the sim aborts with the partial result (short-circuits the non-movers /
        backward-movers that dominate any population).

        NOTE: this is a NEW metric (forward body-lengths) — values are NOT comparable to
        the earlier metres-based runs (0.116–0.1837 m).
        """
        nbody = self.model.nbody

        # Body length from the undeformed layout (positions before any stepping).
        init_xpos   = np.array(self.data.xpos[1:nbody], copy=True)
        extents     = init_xpos.max(axis=0) - init_xpos.min(axis=0)
        body_length = max(float(extents.max()) + self.voxel_size, self.voxel_size)

        # Settle, recording resting COM-z over the final quarter (robust to bounce).
        settle_steps = int(settle_time / self.default_timestep)
        track_from   = int(settle_steps * 0.75)
        heights      = []
        for s in range(settle_steps):
            self.step()
            if s >= track_from:
                heights.append(float(np.mean(self.data.xpos[1:nbody, 2])))
        settled_height   = float(np.median(heights)) if heights \
            else float(np.mean(self.data.xpos[1:nbody, 2]))
        ground_threshold = max(settled_height * 2.0, 0.05)

        initial_x      = float(self.get_position()[0])
        measure_steps  = int(simulation_time / self.default_timestep)
        check_step     = int(measure_steps * early_term_fraction)
        grounded_steps = 0
        heights        = []   # COM-z per step → gait descriptors (height, bounce)

        def _result(fit):
            if not return_descriptors:
                return fit
            if heights:
                h  = np.asarray(heights, dtype=float)
                d1 = float(h.mean()) / body_length   # mean COM height (body-lengths)
                d2 = float(h.std())  / body_length   # vertical bounce amplitude (body-lengths)
            else:
                d1 = d2 = 0.0
            return fit, (d1, d2)

        for step_idx in range(measure_steps):
            self.step()
            com_z = float(np.mean(self.data.xpos[1:nbody, 2]))
            heights.append(com_z)
            if com_z < ground_threshold:
                grounded_steps += 1

            if step_idx + 1 == check_step:
                forward_bl = (float(self.get_position()[0]) - initial_x) / body_length
                if forward_bl < early_term_threshold:
                    ground_fraction = grounded_steps / (step_idx + 1)
                    return _result(max(0.0, forward_bl) * ground_fraction)

        ground_fraction = grounded_steps / measure_steps
        forward_bl      = (float(self.get_position()[0]) - initial_x) / body_length
        return _result(max(0.0, forward_bl) * ground_fraction)
