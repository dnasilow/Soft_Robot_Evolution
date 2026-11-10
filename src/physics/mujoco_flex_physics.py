"""
MuJoCo FLEX (deformable) physics engine  [B5 reformulation]

Drop-in alternative to MuJoCoTendonPhysics with the SAME public interface
(load_robot / step / get_position / get_fitness / num_active_tendons /
set_controller), so the existing evaluator can use it behind a --flex flag.

Why: the tendon model spends ~99% of its step time on intra-robot self-collision
(~7,800 contacts / 300-voxel robot). Flex represents the body as a continuum —
internal cohesion is cheap FEM edges, not contacts — giving ~70x raw / ~140x
effective throughput (see B5_SPIKE_RESULTS.md). This is a FRESH baseline: flex
fitness values are not comparable to tendon-model numbers.

Actuation: open-loop only (v1). Materials 1/2 -> muscle x-edges at phase 0 / pi,
driven by sin(omega*t + base_phase) at the global actuation frequency.
"""
import numpy as np
import mujoco

from src.physics.mujoco_flex_converter import build_flex_spec


class MuJoCoFlexPhysics:
    """Deformable (flex) soft-robot physics engine — tendon-model-compatible API."""

    def __init__(
        self,
        default_timestep: float = 0.0005,
        actuation_frequency: float = 10.0,
        actuation_amplitude: float = 0.20,
        young: float = 1.0e4,
        poisson: float = 0.2,
        muscle_kp: float = 600.0,
        feet: bool = True,          # grip feet on bottom nodes (ground ratcheting)
        multi_axis: bool = True,    # x forward + z lift/plant muscles
        fitness_mode: str = "directed",
        wave_phase_n=None,          # None -> 2-phase material gait; int -> traveling wave
    ):
        self.feet = feet
        self.multi_axis = multi_axis
        self.fitness_mode = fitness_mode   # directed | forward | efficiency | stable
        self.wave_phase_n = wave_phase_n
        self.default_timestep    = default_timestep
        self.actuation_frequency = actuation_frequency
        self.actuation_amplitude = actuation_amplitude
        self.young               = young
        self.poisson             = poisson
        self.muscle_kp           = muscle_kp
        self.voxel_size          = 0.01

        self.model = None
        self.data  = None
        self.current_time = 0.0
        self.rest_lengths = None
        self._base_phases = None
        self.build_info   = {}

    # ------------------------------------------------------------------
    def load_robot(self, voxel_grid, voxel_size=0.01, initial_height=0.0, gait_params=None):
        spec, base_phases, info = build_flex_spec(
            voxel_grid, voxel_size=voxel_size, initial_height=initial_height,
            young=self.young, poisson=self.poisson, muscle_kp=self.muscle_kp,
            timestep=self.default_timestep,
            feet=self.feet, multi_axis=self.multi_axis,
            wave_phase_n=self.wave_phase_n, gait_params=gait_params,
        )
        self.voxel_size   = voxel_size
        self.model        = spec.compile()
        self.data         = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        # step-count math must use the model's actual timestep
        self.default_timestep = float(self.model.opt.timestep)
        self.rest_lengths = np.array(self.data.actuator_length, copy=True)
        self._base_phases = base_phases
        self.build_info   = info
        self.current_time = 0.0

    # ------------------------------------------------------------------
    @property
    def num_active_tendons(self) -> int:
        return int(self.model.nu) if self.model is not None else 0

    def set_controller(self, controller) -> None:
        """Flex v1 is open-loop only; a CPG controller is ignored (kept API-compatible)."""
        # Intentionally a no-op: apply_actuation() always drives open-loop.
        return None

    # ------------------------------------------------------------------
    def apply_actuation(self) -> None:
        if self.rest_lengths is None or self.model.nu == 0:
            return
        omega  = 2.0 * np.pi * self.actuation_frequency
        signal = self.actuation_amplitude * np.sin(omega * self.current_time + self._base_phases)
        self.data.ctrl[:] = self.rest_lengths * (1.0 + signal)

    def step(self) -> None:
        if self.model is None:
            return
        self.apply_actuation()
        mujoco.mj_step(self.model, self.data)
        self.current_time += self.default_timestep

    def get_position(self) -> np.ndarray:
        if self.data is None:
            return np.zeros(3)
        return np.mean(self.data.xpos[1:self.model.nbody], axis=0)

    # ------------------------------------------------------------------
    def get_fitness(
        self,
        simulation_time:      float = 5.0,
        settle_time:          float = 0.5,
        early_term_fraction:  float = 0.2,
        early_term_threshold: float = 0.05,
        return_descriptors:   bool  = False,
    ):
        """Identical metric to MuJoCoTendonPhysics.get_fitness (directed +X body-lengths
        x ground-fraction), computed over the flex node bodies."""
        nbody = self.model.nbody

        init_xpos   = np.array(self.data.xpos[1:nbody], copy=True)
        extents     = init_xpos.max(axis=0) - init_xpos.min(axis=0)
        body_length = max(float(extents.max()) + self.voxel_size, self.voxel_size)

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
        heights        = []

        def _result(fit):
            if not return_descriptors:
                return fit
            if heights:
                h  = np.asarray(heights, dtype=float)
                d1 = float(h.mean()) / body_length
                d2 = float(h.std())  / body_length
            else:
                d1 = d2 = 0.0
            return fit, (d1, d2)

        energy = 0.0

        def _shape(fbl, gf, steps):
            base = max(0.0, fbl)
            mode = self.fitness_mode
            if mode == "forward":
                return base
            if mode == "efficiency":
                mean_force = (energy / max(steps, 1)) / max(int(self.model.nu), 1)
                return base * gf / (1.0 + 0.001 * mean_force)
            if mode == "stable":
                bounce = (float(np.std(heights)) / body_length) if heights else 0.0
                return base * gf / (1.0 + 5.0 * bounce)
            return base * gf

        for step_idx in range(measure_steps):
            self.step()
            energy += float(np.sum(np.abs(self.data.actuator_force)))
            com_z = float(np.mean(self.data.xpos[1:nbody, 2]))
            heights.append(com_z)
            if com_z < ground_threshold:
                grounded_steps += 1
            if step_idx + 1 == check_step:
                forward_bl = (float(self.get_position()[0]) - initial_x) / body_length
                if forward_bl < early_term_threshold:
                    ground_fraction = grounded_steps / (step_idx + 1)
                    return _result(_shape(forward_bl, ground_fraction, step_idx + 1))

        ground_fraction = grounded_steps / measure_steps
        forward_bl      = (float(self.get_position()[0]) - initial_x) / body_length
        return _result(_shape(forward_bl, ground_fraction, measure_steps))
