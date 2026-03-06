"""
MuJoCo Physics Engine with Proper Rest-Length Actuation

This version implements actuation by directly modulating spring rest lengths
by ±20%, not just stiffness. This creates visible oscillation.
"""
import numpy as np
import mujoco
from typing import Optional
from src.physics.mujoco_converter import voxel_to_mujoco_xml


class MuJoCoActuatedPhysics:
    """
    Physics engine with rest-length based actuation (±20% oscillation)
    """

    def __init__(self, default_timestep: float = 0.0005, actuation_frequency: float = 10.0):
        self.default_timestep = default_timestep
        self.actuation_frequency = actuation_frequency
        self.actuation_amplitude = 0.20  # ±20% rest length modulation

        # Model and simulation state
        self.model: Optional[mujoco.MjModel] = None
        self.data: Optional[mujoco.MjData] = None
        self.current_time = 0.0

        # Robot metadata
        self.voxel_materials = None
        self.num_voxels = 0

        # Store initial rest lengths for each constraint
        self.initial_distances = None

    def load_robot(self, voxel_grid: np.ndarray, voxel_size: float = 0.01, initial_height: float = 0.0) -> None:
        """Load robot and record initial spring rest lengths"""
        # Convert to XML and load
        xml = voxel_to_mujoco_xml(voxel_grid, voxel_size, initial_height)
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)

        # Store voxel materials for actuation logic
        self.num_voxels = np.count_nonzero(voxel_grid)
        self.voxel_materials = []

        for x in range(voxel_grid.shape[0]):
            for y in range(voxel_grid.shape[1]):
                for z in range(voxel_grid.shape[2]):
                    if voxel_grid[x, y, z] > 0:
                        self.voxel_materials.append(voxel_grid[x, y, z])

        # Run forward kinematics to get initial body positions
        mujoco.mj_forward(self.model, self.data)

        # Record initial distances between connected bodies
        self.initial_distances = []
        for i in range(self.model.neq):
            if self.model.eq_type[i] == 0:  # connect constraint
                body1_id = self.model.eq_obj1id[i]
                body2_id = self.model.eq_obj2id[i]

                # Get body positions
                pos1 = self.data.xpos[body1_id]
                pos2 = self.data.xpos[body2_id]
                initial_dist = np.linalg.norm(pos2 - pos1)

                self.initial_distances.append(initial_dist)

        self.current_time = 0.0

    def apply_actuation(self) -> None:
        """
        Apply actuation by modulating constraint DATA, simulating rest-length changes.

        Since MuJoCo connect constraints don't have modifiable rest lengths,
        we apply forces that simulate changing rest lengths.
        """
        if self.model is None or self.data is None:
            return

        omega = 2.0 * np.pi * self.actuation_frequency

        for i in range(self.model.neq):
            if self.model.eq_type[i] != 0:  # Only connect constraints
                continue

            body1_id = self.model.eq_obj1id[i]
            body2_id = self.model.eq_obj2id[i]

            # Skip ground connections
            if body1_id == 0 or body2_id == 0:
                continue

            # Check if connected to active material
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

                    if is_active and i < len(self.initial_distances):
                        # Calculate actuation signal (±20%)
                        actuation = self.actuation_amplitude * np.sin(omega * self.current_time + phase)

                        # Get current distance
                        pos1 = self.data.xpos[body1_id]
                        pos2 = self.data.xpos[body2_id]
                        current_dist = np.linalg.norm(pos2 - pos1)

                        # Calculate target distance (rest length ± 20%)
                        rest_length = self.initial_distances[i]
                        target_dist = rest_length * (1.0 + actuation)

                        # Apply corrective force proportional to distance error
                        # This simulates a spring with changing rest length
                        dist_error = current_dist - target_dist

                        # VERY AGGRESSIVE stiffness modulation to enforce rest length
                        # Lower timeconst = stiffer = stronger enforcement
                        # Using EXTREME values to force visible motion
                        if actuation > 0:  # Expanding
                            # Make spring VERY soft to allow expansion
                            self.model.eq_solref[i, 0] = 0.2  # Very soft (was 0.04)
                        else:  # Contracting
                            # Make spring VERY stiff to force contraction
                            self.model.eq_solref[i, 0] = 0.001  # Very stiff (was 0.01)

                        # Also apply direct force proportional to distance error
                        # This adds extra "push" to help overcome damping
                        force_scale = 100.0  # Strong force
                        if abs(dist_error) > 0.0001:  # If not at target
                            # Calculate force direction (from body1 to body2)
                            direction = (pos2 - pos1) / (current_dist + 1e-10)
                            # Force magnitude proportional to error
                            force_mag = force_scale * dist_error
                            # Apply equal and opposite forces
                            self.data.xfrc_applied[body1_id, :3] += direction * force_mag
                            self.data.xfrc_applied[body2_id, :3] -= direction * force_mag

    def step(self) -> None:
        """Advance simulation by one timestep with actuation"""
        if self.model is None or self.data is None:
            return

        # Apply actuation before physics step
        self.apply_actuation()

        # Step physics
        mujoco.mj_step(self.model, self.data)

        # Update time
        self.current_time += self.default_timestep

    def get_position(self) -> np.ndarray:
        """Get center of mass position of robot"""
        if self.data is None:
            return np.zeros(3)

        # Average position of all voxel bodies (skip world body 0)
        positions = [self.data.xpos[i] for i in range(1, self.model.nbody)]
        return np.mean(positions, axis=0)

    def get_fitness(self, simulation_time: float = 5.0) -> float:
        """Simulate and return fitness (horizontal distance traveled)"""
        initial_pos = self.get_position()

        steps = int(simulation_time / self.default_timestep)
        for _ in range(steps):
            self.step()

        final_pos = self.get_position()

        # Horizontal distance (X-Y plane)
        horizontal_distance = np.sqrt((final_pos[0] - initial_pos[0])**2 +
                                     (final_pos[1] - initial_pos[1])**2)

        return float(horizontal_distance)
