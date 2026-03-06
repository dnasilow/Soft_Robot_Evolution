"""
MuJoCo Physics Engine with Tendon-Based Actuation

Actuation mechanism:
  - Every adjacent voxel pair is connected by a spatial tendon
  - Each tendon has a position actuator: force = kp * (ctrl - current_length)
  - For active voxels: ctrl = rest_length * (1 + amplitude * sin(omega*t + phase))
  - For passive voxels: ctrl = rest_length  (structural, maintains shape)

This is the correct MuJoCo-native way to implement rest-length actuation.
"""
import numpy as np
import mujoco
from typing import Optional, List, Dict
from src.physics.mujoco_tendon_converter import voxel_to_tendon_xml


class MuJoCoTendonPhysics:
    """
    Tendon-based soft robot physics engine.
    """

    def __init__(
        self,
        default_timestep: float = 0.0005,
        actuation_frequency: float = 10.0,
        actuation_amplitude: float = 0.20,
    ):
        self.default_timestep = default_timestep
        self.actuation_frequency = actuation_frequency
        self.actuation_amplitude = actuation_amplitude  # +-20% rest length

        self.model: Optional[mujoco.MjModel] = None
        self.data:  Optional[mujoco.MjData]  = None
        self.current_time = 0.0

        # Set after load_robot()
        self.tendon_info: List[Dict] = []     # metadata from converter
        self.rest_lengths: Optional[np.ndarray] = None  # shape (num_tendons,)

    # ------------------------------------------------------------------
    def load_robot(
        self,
        voxel_grid: np.ndarray,
        voxel_size: float = 0.01,
        initial_height: float = 0.0,
        kp: float = 100.0,
    ) -> None:
        """Load robot from voxel grid and record tendon rest lengths."""
        xml, self.tendon_info = voxel_to_tendon_xml(
            voxel_grid, voxel_size, initial_height, kp
        )
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data  = mujoco.MjData(self.model)

        # Run forward kinematics to compute initial tendon lengths
        mujoco.mj_forward(self.model, self.data)

        # data.ten_length[i] is the current length of tendon i
        self.rest_lengths = np.array(self.data.ten_length, copy=True)

        self.current_time = 0.0

    # ------------------------------------------------------------------
    def apply_actuation(self) -> None:
        """Set ctrl for every tendon actuator based on material type."""
        if self.model is None or self.rest_lengths is None:
            return

        omega = 2.0 * np.pi * self.actuation_frequency

        for k, info in enumerate(self.tendon_info):
            mat1 = info['mat1']
            mat2 = info['mat2']
            rest = self.rest_lengths[k]

            # Determine phase from material type
            # A tendon is active if either endpoint is an active voxel
            phase = None
            if mat1 == 1 or mat2 == 1:
                phase = 0.0          # Active 0deg
            elif mat1 == 2 or mat2 == 2:
                phase = np.pi        # Active 180deg

            if phase is not None:
                # Active: oscillate rest length by +-amplitude
                signal = self.actuation_amplitude * np.sin(
                    omega * self.current_time + phase
                )
                self.data.ctrl[k] = rest * (1.0 + signal)
            else:
                # Passive: hold at rest length (provides structural support)
                self.data.ctrl[k] = rest

    # ------------------------------------------------------------------
    def step(self) -> None:
        """Advance simulation by one timestep."""
        if self.model is None:
            return
        self.apply_actuation()
        mujoco.mj_step(self.model, self.data)
        self.current_time += self.default_timestep

    # ------------------------------------------------------------------
    def get_position(self) -> np.ndarray:
        """Return center-of-mass position of all voxel bodies."""
        if self.data is None:
            return np.zeros(3)
        positions = [self.data.xpos[i] for i in range(1, self.model.nbody)]
        return np.mean(positions, axis=0)

    # ------------------------------------------------------------------
    def get_fitness(self, simulation_time: float = 5.0) -> float:
        """Run simulation and return horizontal distance traveled."""
        initial_pos = self.get_position()
        steps = int(simulation_time / self.default_timestep)
        for _ in range(steps):
            self.step()
        final_pos = self.get_position()
        return float(np.sqrt(
            (final_pos[0] - initial_pos[0]) ** 2 +
            (final_pos[1] - initial_pos[1]) ** 2
        ))
