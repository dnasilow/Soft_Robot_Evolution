"""MuJoCo-based physics engine for soft robot evolution"""
import numpy as np
import mujoco
from typing import Optional, Tuple
from src.physics.mujoco_converter import voxel_to_mujoco_xml


class MuJoCoPhysicsEngine:
    """
    Physics engine using MuJoCo for stable soft robot simulation.

    Features:
    - Stable constraint-based physics
    - Sinusoidal actuation for active materials
    - Parallel robot evaluation support
    - Energy-conservative integration
    """

    def __init__(self, default_timestep: float = 0.0005, actuation_frequency: float = 2.0):
        """
        Initialize MuJoCo physics engine.

        Args:
            default_timestep: Simulation timestep in seconds (default: 0.0005s = 0.5ms)
            actuation_frequency: Frequency of sinusoidal actuation in Hz (default: 2Hz)
        """
        self.default_timestep = default_timestep
        self.actuation_frequency = actuation_frequency
        self.actuation_amplitude = 0.20  # ±20% as specified

        # Current simulation state
        self.model: Optional[mujoco.MjModel] = None
        self.data: Optional[mujoco.MjData] = None
        self.current_time = 0.0

        # Robot metadata
        self.voxel_materials = None  # Material ID for each voxel
        self.num_voxels = 0

    def load_robot(self, voxel_grid: np.ndarray, voxel_size: float = 0.01) -> None:
        """
        Load a robot from voxel grid.

        Args:
            voxel_grid: 3D numpy array with material IDs
            voxel_size: Size of each voxel in meters (default: 0.01m = 1cm)
        """
        # Convert voxel grid to MuJoCo XML
        xml = voxel_to_mujoco_xml(voxel_grid, voxel_size)

        # Create MuJoCo model
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)

        # Store metadata
        self.num_voxels = np.count_nonzero(voxel_grid)
        self.voxel_materials = []

        # Extract material information from voxel grid
        for x in range(voxel_grid.shape[0]):
            for y in range(voxel_grid.shape[1]):
                for z in range(voxel_grid.shape[2]):
                    material_id = int(voxel_grid[x, y, z])
                    if material_id != 0:
                        self.voxel_materials.append(material_id)

        self.current_time = 0.0

    def apply_actuation(self) -> None:
        """
        Apply sinusoidal actuation to active materials.

        Active materials (1 and 2) have phase offsets:
        - Material 1 (Active 0°): phase = 0.0
        - Material 2 (Active 180°): phase = π

        Actuation: amplitude * sin(2π * freq * time + phase)
        """
        if self.model is None or self.data is None:
            return

        # MuJoCo uses actuators defined in XML
        # For now, we'll modulate constraint stiffness directly
        # This is a simplified approach - full implementation would use actuators

        # Calculate actuation signal
        omega = 2.0 * np.pi * self.actuation_frequency

        # For each equality constraint (spring connection)
        for i in range(self.model.neq):
            # Get the two bodies connected by this constraint
            # Constraint type 0 = connect constraint
            if self.model.eq_type[i] == 0:  # connect constraint
                body1_id = self.model.eq_obj1id[i]
                body2_id = self.model.eq_obj2id[i]

                # Check if either body uses active material
                # Body 0 is ground, voxels start at body 1
                if body1_id > 0 and body2_id > 0:
                    voxel1_idx = body1_id - 1
                    voxel2_idx = body2_id - 1

                    if voxel1_idx < len(self.voxel_materials) and voxel2_idx < len(self.voxel_materials):
                        mat1 = self.voxel_materials[voxel1_idx]
                        mat2 = self.voxel_materials[voxel2_idx]

                        # Determine actuation phase
                        phase = 0.0
                        is_active = False

                        if mat1 == 1 or mat2 == 1:  # Active 0°
                            phase = 0.0
                            is_active = True
                        elif mat1 == 2 or mat2 == 2:  # Active 180°
                            phase = np.pi
                            is_active = True

                        if is_active:
                            # Sinusoidal actuation signal
                            actuation = self.actuation_amplitude * np.sin(omega * self.current_time + phase)

                            # Modulate solref parameters (spring stiffness/damping)
                            # solref[0] = timeconst (related to stiffness)
                            # Increasing timeconst makes spring softer (simulates contraction)
                            base_timeconst = 0.02
                            modulated_timeconst = base_timeconst * (1.0 + actuation)

                            # Update constraint parameters
                            self.model.eq_solref[i, 0] = modulated_timeconst

    def step(self, dt: Optional[float] = None) -> None:
        """
        Step the simulation forward by one timestep.

        Args:
            dt: Timestep in seconds (uses default if None)
        """
        if self.model is None or self.data is None:
            raise ValueError("No robot loaded! Call load_robot() first.")

        if dt is None:
            dt = self.default_timestep

        # Apply actuation before physics step
        self.apply_actuation()

        # Step MuJoCo simulation
        mujoco.mj_step(self.model, self.data)

        # Update time
        self.current_time += dt

    def get_position(self) -> np.ndarray:
        """Get center of mass position of the robot [x, y, z]."""
        if self.data is None:
            return np.zeros(3)

        # Calculate COM from all voxel bodies (skip ground at index 0)
        total_mass = 0.0
        com = np.zeros(3)

        for i in range(1, self.model.nbody):
            body_mass = self.model.body_mass[i]
            body_pos = self.data.xpos[i]

            com += body_mass * body_pos
            total_mass += body_mass

        if total_mass > 0:
            com /= total_mass

        return com

    def get_fitness(self, simulation_time: float = 5.0) -> float:
        """
        Simulate robot and calculate fitness (distance traveled).

        Args:
            simulation_time: Total simulation time in seconds

        Returns:
            Fitness value (horizontal distance traveled in meters)
        """
        if self.model is None:
            return 0.0

        # Reset simulation
        mujoco.mj_resetData(self.model, self.data)
        self.current_time = 0.0

        # Get initial position
        initial_pos = self.get_position()

        # Simulate
        steps = int(simulation_time / self.default_timestep)
        for _ in range(steps):
            self.step()

        # Get final position
        final_pos = self.get_position()

        # Calculate horizontal distance (X-Y plane, ignore Z height)
        horizontal_distance = np.sqrt((final_pos[0] - initial_pos[0])**2 +
                                     (final_pos[1] - initial_pos[1])**2)

        return float(horizontal_distance)

    def reset(self) -> None:
        """Reset simulation to initial state."""
        if self.model is not None and self.data is not None:
            mujoco.mj_resetData(self.model, self.data)
            self.current_time = 0.0
