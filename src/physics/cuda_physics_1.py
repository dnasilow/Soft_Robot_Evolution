import numpy as np
import cupy as cp

class CUDAPhysicsEngine:
    _gpu_info_printed = False  # Add this line AT THE CLASS LEVEL
    def __init__(self, max_nodes=10000, max_springs=50000, actuation_frequency=1.0, default_timestep=0.0005):
        """Initialize GPU physics engine"""
        self.max_nodes = max_nodes
        self.max_springs = max_springs
        self.default_timestep = default_timestep  # Store default timestep
        self.actuation_frequency = actuation_frequency 
        self.device = cp.cuda.Device(0)
        '''
        # Check GPU availability
        self.device = cp.cuda.Device(0)
        #print(f"Using GPU: Device {self.device.id}")
        mem_info = self.device.mem_info
        #print(f"GPU Memory: {mem_info[1] / 1e9:.1f} GB total, {mem_info[0] / 1e9:.1f} GB free")
        '''

        # Only print GPU info once
        if not CUDAPhysicsEngine._gpu_info_printed:
            print(f"Using GPU: Device {self.device.id}")
            mem_info = self.device.mem_info
            print(f"GPU Memory: {mem_info[1] / 1e9:.1f} GB total, {mem_info[0] / 1e9:.1f} GB free")
            print(f"Default timestep: {default_timestep} s")
            CUDAPhysicsEngine._gpu_info_printed = True
        
        # Allocate GPU memory
        self.d_positions = cp.zeros((max_nodes, 3), dtype=cp.float32)
        self.d_velocities = cp.zeros((max_nodes, 3), dtype=cp.float32)
        self.d_forces = cp.zeros((max_nodes, 3), dtype=cp.float32)
        self.d_masses = cp.ones(max_nodes, dtype=cp.float32)
        
        # Spring data
        self.d_spring_indices = cp.zeros((max_springs, 2), dtype=cp.int32)
        self.d_rest_lengths = cp.zeros(max_springs, dtype=cp.float32)
        self.d_stiffnesses = cp.zeros(max_springs, dtype=cp.float32)
        self.d_damping = cp.zeros(max_springs, dtype=cp.float32)
        
        # Actuator data
        self.d_actuator_indices = cp.zeros(max_springs, dtype=cp.int32)
        self.d_actuator_signals = cp.zeros(max_springs, dtype=cp.float32)
        self.d_actuator_phases = cp.zeros(max_springs, dtype=cp.float32)
        
        # Simulation parameters
        self.gravity = 9.81
        self.time = 0.0
        self.num_nodes = 0
        self.num_springs = 0
        self.num_actuators = 0
    
    def reset(self):
        """Reset simulation state"""
        self.d_positions.fill(0)
        self.d_velocities.fill(0)
        self.d_forces.fill(0)
        self.time = 0.0
        self.num_nodes = 0
        self.num_springs = 0
        self.num_actuators = 0
    
    # def add_robot(self, robot):
    #         """Add a robot to the simulation"""
    #         nodes = robot.get_nodes()
    #         springs = robot.get_springs()
            
    #         # Update node data
    #         n = len(nodes['position'])
    #         self.d_positions[self.num_nodes:self.num_nodes+n] = cp.asarray(nodes['position'])
    #         self.d_masses[self.num_nodes:self.num_nodes+n] = cp.asarray(nodes['mass'])
            
    #         # Update spring data
    #         s = len(springs['indices'])
    #         spring_indices = springs['indices'] + self.num_nodes  # Offset indices
    #         self.d_spring_indices[self.num_springs:self.num_springs+s] = cp.asarray(spring_indices)
    #         self.d_rest_lengths[self.num_springs:self.num_springs+s] = cp.asarray(springs['rest_length'])
    #         self.d_stiffnesses[self.num_springs:self.num_springs+s] = cp.asarray(springs['stiffness'])
    #         self.d_damping[self.num_springs:self.num_springs+s] = cp.asarray(springs['damping'])
            
    #         # Update actuators
    #         actuator_mask = springs['is_actuator']
    #         actuator_indices = np.where(actuator_mask)[0]
            
    #         if len(actuator_indices) > 0:
    #             # Store global spring indices for actuators
    #             global_actuator_indices = actuator_indices + self.num_springs
    #             self.d_actuator_indices[:len(actuator_indices)] = cp.asarray(global_actuator_indices)
                
    #             # Initialize actuator phases with random values if not provided
    #             # This helps robots start moving
    #             phases = np.random.uniform(0, 2*np.pi, len(actuator_indices))
    #             self.d_actuator_phases[:len(actuator_indices)] = cp.asarray(phases)
                
    #             # Initialize signals to 1.0 (full strength)
    #             self.d_actuator_signals[:len(actuator_indices)] = 1.0
                
    #             self.num_actuators = len(actuator_indices)
            
    #         self.num_nodes += n
    #         self.num_springs += s
            
    #         print(f"Added robot: {n} nodes, {s} springs, {self.num_actuators} actuators")
    
    def add_robot(self, robot):
        """Add a robot to the simulation with proper phase handling"""
        nodes = robot.get_nodes()
        springs = robot.get_springs()
        
        # Update node data
        n = len(nodes['position'])
        self.d_positions[self.num_nodes:self.num_nodes+n] = cp.asarray(nodes['position'])
        self.d_masses[self.num_nodes:self.num_nodes+n] = cp.asarray(nodes['mass'])
        
        # Update spring data
        s = len(springs['indices'])
        spring_indices = springs['indices'] + self.num_nodes
        self.d_spring_indices[self.num_springs:self.num_springs+s] = cp.asarray(spring_indices)
        self.d_rest_lengths[self.num_springs:self.num_springs+s] = cp.asarray(springs['rest_length'])
        self.d_stiffnesses[self.num_springs:self.num_springs+s] = cp.asarray(springs['stiffness'])
        self.d_damping[self.num_springs:self.num_springs+s] = cp.asarray(springs['damping'])
        
        # Handle actuators with FIXED phases (no randomization)
        actuator_mask = springs['is_actuator']
        if np.any(actuator_mask):
            actuator_indices = np.where(actuator_mask)[0]
            num_actuators = len(actuator_indices)
            
            # Store global spring indices for actuators
            global_actuator_indices = actuator_indices + self.num_springs
            self.d_actuator_indices[:num_actuators] = cp.asarray(global_actuator_indices)
            
            # Use FIXED phases from material definition (0° for green, 180° for red)
            actuator_phases = springs['actuation_phase'][actuator_mask]
            self.d_actuator_phases[:num_actuators] = cp.asarray(actuator_phases)
            
            # Initialize signals to 1.0 (full strength)
            self.d_actuator_signals[:num_actuators] = 1.0
            
            self.num_actuators = num_actuators
            
            print(f"Added {num_actuators} actuators with phases: {actuator_phases[:5]}...")  # Show first 5
        
        self.num_nodes += n
        self.num_springs += s
    
        
    def integrate_positions(self, dt):
        """Integrate positions using CuPy operations (no custom kernel needed)"""
        if self.num_nodes == 0:
            return
            
        # Limit forces to prevent explosion
        max_force_per_node = 50.0  # N
        force_magnitudes = cp.linalg.norm(self.d_forces[:self.num_nodes], axis=1)
        force_limit_mask = force_magnitudes > max_force_per_node
        if cp.any(force_limit_mask):
            # Scale down forces that are too large
            scale_factors = max_force_per_node / (force_magnitudes + 1e-6)
            self.d_forces[:self.num_nodes][force_limit_mask] *= scale_factors[force_limit_mask, cp.newaxis]
            
        # Add gravity to forces
        self.d_forces[:self.num_nodes, 1] -= self.d_masses[:self.num_nodes] * self.gravity
        
        # Calculate accelerations
        # Reshape masses to broadcast properly
        masses_reshaped = self.d_masses[:self.num_nodes, cp.newaxis]
        # Ensure minimum mass
        masses_reshaped = cp.maximum(masses_reshaped, 0.001)
        accelerations = self.d_forces[:self.num_nodes] / masses_reshaped
        
        # Limit accelerations
        max_acceleration = 100.0  # m/s^2
        accel_magnitudes = cp.linalg.norm(accelerations, axis=1)
        accel_limit_mask = accel_magnitudes > max_acceleration
        if cp.any(accel_limit_mask):
            scale_factors = max_acceleration / (accel_magnitudes + 1e-6)
            accelerations[accel_limit_mask] *= scale_factors[accel_limit_mask, cp.newaxis]
        
        # Update velocities with damping
        self.d_velocities[:self.num_nodes] = (
            self.d_velocities[:self.num_nodes] * 0.995 + accelerations * dt  # More damping
        )
        
        # Limit velocities
        max_velocity = 10.0  # m/s
        vel_magnitudes = cp.linalg.norm(self.d_velocities[:self.num_nodes], axis=1)
        vel_limit_mask = vel_magnitudes > max_velocity
        if cp.any(vel_limit_mask):
            scale_factors = max_velocity / (vel_magnitudes + 1e-6)
            self.d_velocities[:self.num_nodes][vel_limit_mask] *= scale_factors[vel_limit_mask, cp.newaxis]
        
        # Update positions
        self.d_positions[:self.num_nodes] += self.d_velocities[:self.num_nodes] * dt
        
        # Limit positions to reasonable bounds
        max_position = 10.0  # meters from origin
        self.d_positions[:self.num_nodes] = cp.clip(self.d_positions[:self.num_nodes], -max_position, max_position)
        
        # Ground collision
        # Check which nodes are below ground
        below_ground = self.d_positions[:self.num_nodes, 1] < 0.0
        
        # Fix positions at ground
        self.d_positions[:self.num_nodes, 1] = cp.maximum(
            self.d_positions[:self.num_nodes, 1], 0.0
        )
        
        # Apply bounce and friction only to nodes that hit ground
        if cp.any(below_ground):
            # Get indices of nodes below ground
            ground_indices = cp.where(below_ground)[0]
            
            # Bounce
            self.d_velocities[ground_indices, 1] *= -0.3  # Less bouncy
            
            # Friction on X and Z
            self.d_velocities[ground_indices, 0] *= 0.8
            self.d_velocities[ground_indices, 2] *= 0.8
        
        # Clear forces for next iteration
        self.d_forces[:self.num_nodes] = 0.0

    def compute_spring_forces(self):
        """Compute spring forces using CuPy operations"""
        if self.num_springs == 0:
            return
            
        # Get positions for each spring endpoint
        indices1 = self.d_spring_indices[:self.num_springs, 0]
        indices2 = self.d_spring_indices[:self.num_springs, 1]
        
        pos1 = self.d_positions[indices1]
        pos2 = self.d_positions[indices2]
        
        # Calculate displacement vectors
        displacement = pos2 - pos1
        
        # Calculate lengths
        lengths = cp.sqrt(cp.sum(displacement * displacement, axis=1))
        
        # Avoid division by zero
        valid_mask = lengths > 0.0001
        
        # Normalize displacement vectors
        displacement[valid_mask] = displacement[valid_mask] / lengths[valid_mask, cp.newaxis]
        
        # Calculate spring forces (Hooke's law)
        extensions = lengths - self.d_rest_lengths[:self.num_springs]
        
        # Limit maximum extension to prevent instability
        max_extension = self.d_rest_lengths[:self.num_springs] * 0.5  # Max 50% extension
        extensions = cp.clip(extensions, -max_extension, max_extension)
        
        spring_forces = self.d_stiffnesses[:self.num_springs] * extensions
        
        # Calculate damping forces
        vel1 = self.d_velocities[indices1]
        vel2 = self.d_velocities[indices2]
        relative_velocities = vel2 - vel1
        
        # Project relative velocity onto displacement direction
        velocity_projections = cp.sum(relative_velocities * displacement, axis=1)
        damping_forces = self.d_damping[:self.num_springs] * velocity_projections
        
        # Total force magnitudes
        total_force_magnitudes = spring_forces + damping_forces
        
        # Limit maximum force to prevent instability
        max_force = 10.0  # Maximum force in Newtons
        total_force_magnitudes = cp.clip(total_force_magnitudes, -max_force, max_force)
        
        # Force vectors
        force_vectors = displacement * total_force_magnitudes[:, cp.newaxis]
        
        # Apply forces to nodes
        # Since CuPy doesn't have scatter_add, we use a simple loop
        # This is the main performance bottleneck
        for i in range(self.num_springs):
            if valid_mask[i]:
                idx1 = int(indices1[i])
                idx2 = int(indices2[i])
                force = force_vectors[i]
                
                # Check for NaN before applying
                if not cp.any(cp.isnan(force)):
                    self.d_forces[idx1] -= force
                    self.d_forces[idx2] += force

    def apply_actuator_forces(self):
            """Apply actuator control signals"""
            if self.num_actuators == 0:
                return
                
            # Get actuator spring indices
            actuator_spring_indices = self.d_actuator_indices[:self.num_actuators].astype(int)
            
            # Calculate actuation signals (sinusoidal)
            phases = self.d_actuator_phases[:self.num_actuators]
            signals = self.d_actuator_signals[:self.num_actuators]
            
            # Sinusoidal actuation with configurable frequency
            actuation = cp.sin(self.time * 2 * cp.pi * self.actuation_frequency + phases) * signals

            # Store original rest lengths
            original_lengths = self.d_rest_lengths[actuator_spring_indices].copy()
            
            # Modify rest lengths (±20% maximum as per Lipson's spec)
            self.d_rest_lengths[actuator_spring_indices] = original_lengths * (1.0 + 0.2 * actuation)

            # Debug: print first few actuator values occasionally
            if int(self.time * 200) % 200 == 0 and self.time > 0:  # Every second
                actuation_cpu = cp.asnumpy(actuation[:min(5, len(actuation))])
                signals_cpu = cp.asnumpy(signals[:min(5, len(signals))])
                print(f"  Time {self.time:.2f}s - First 5 actuators: signals={signals_cpu}, actuation={actuation_cpu}")
            
            # Store original rest lengths
            original_lengths = self.d_rest_lengths[actuator_spring_indices].copy()
            
            # Modify rest lengths (±14% maximum)
            self.d_rest_lengths[actuator_spring_indices] = original_lengths * (1.0 + 0.20 * actuation)
    
    def step(self, dt=0.0005):
        """Single physics simulation step"""
        if dt is None:
            dt = self.default_timestep  # Use the exact timestep

        # Clear forces
        self.d_forces.fill(0)
        
        # Compute spring forces
        self.compute_spring_forces()
        
        # Apply actuator forces
        self.apply_actuator_forces()
        
        # Integrate positions using CuPy operations
        self.integrate_positions(dt)
        
        self.time += dt
    
    def get_positions(self):
        """Get current positions from GPU"""
        return cp.asnumpy(self.d_positions[:self.num_nodes])
    
    def set_actuator_signals(self, signals):
        """Set actuator control signals"""
        if len(signals) > 0 and self.num_actuators > 0:
            n = min(len(signals), self.num_actuators)
            self.d_actuator_signals[:n] = cp.asarray(signals[:n])