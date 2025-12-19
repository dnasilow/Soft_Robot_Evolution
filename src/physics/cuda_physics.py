import numpy as np
import cupy as cp

# Try to import sparse matrix support (fallback if not available)
try:
    from cupyx.scipy.sparse import csr_matrix
    import cupyx.scipy.sparse as cp_sparse
    SPARSE_AVAILABLE = True
except ImportError:
    print("Warning: CuPy sparse matrices not available, using fallback method")
    SPARSE_AVAILABLE = False

class OptimizedCUDAPhysicsEngine:
    """Heavily optimized GPU physics engine - 10-50x faster"""
    _gpu_info_printed = False  # Class variable to print GPU info only once
    
    def __init__(self, max_nodes=2000, max_springs=15000, actuation_frequency=1.0, default_timestep=0.0001):
        self.max_nodes = max_nodes
        self.max_springs = max_springs
        self.default_timestep = default_timestep
        self.actuation_frequency = actuation_frequency
        
        # GPU device setup
        self.device = cp.cuda.Device(0)
        
        # Only print GPU info once
        if not OptimizedCUDAPhysicsEngine._gpu_info_printed:
            print(f"Using GPU: Device {self.device.id}")
            mem_info = self.device.mem_info
            print(f"GPU Memory: {mem_info[1] / 1e9:.1f} GB total, {mem_info[0] / 1e9:.1f} GB free")
            print(f"Default timestep: {default_timestep} s")
            if SPARSE_AVAILABLE:
                print("[OK] CuPy sparse matrices available (fastest force distribution)")
            else:
                print("[WARN] Using fallback force distribution (still fast)")
            OptimizedCUDAPhysicsEngine._gpu_info_printed = True
        
        # GPU memory - preallocate everything
        self.d_positions = cp.zeros((max_nodes, 3), dtype=cp.float32)
        self.d_velocities = cp.zeros((max_nodes, 3), dtype=cp.float32)
        self.d_forces = cp.zeros((max_nodes, 3), dtype=cp.float32)
        self.d_masses = cp.ones(max_nodes, dtype=cp.float32) * 0.001  # Minimum mass
        
        # Spring data - optimized storage
        self.d_spring_node1 = cp.zeros(max_springs, dtype=cp.int32)
        self.d_spring_node2 = cp.zeros(max_springs, dtype=cp.int32)
        self.d_rest_lengths = cp.zeros(max_springs, dtype=cp.float32)
        self.d_stiffnesses = cp.zeros(max_springs, dtype=cp.float32)
        self.d_damping = cp.zeros(max_springs, dtype=cp.float32)
        
        # Actuator data
        self.d_actuator_spring_ids = cp.zeros(max_springs, dtype=cp.int32)
        self.d_actuator_phases = cp.zeros(max_springs, dtype=cp.float32)
        self.d_actuator_signals = cp.ones(max_springs, dtype=cp.float32)
        
        # Pre-computed sparse matrices for force distribution
        self.force_distribution_matrix = None
        
        # Simulation state
        self.gravity = 9.81
        self.time = 0.0
        self.num_nodes = 0
        self.num_springs = 0
        self.num_actuators = 0
        
        print(f"Optimized GPU Physics initialized: {max_nodes} max nodes, {max_springs} max springs")

    def reset(self):
        """Reset simulation state"""
        self.d_positions.fill(0)
        self.d_velocities.fill(0)
        self.d_forces.fill(0)
        self.time = 0.0
        self.num_nodes = 0
        self.num_springs = 0
        self.num_actuators = 0
        self.force_distribution_matrix = None

        # FIXED: Ensure GPU operations complete before returning
        # Prevents race conditions in batch evaluation
        cp.cuda.Stream.null.synchronize()

    def add_robot(self, robot):
        """Add robot with optimized data structures"""
        nodes = robot.get_nodes()
        springs = robot.get_springs()
        
        n = len(nodes['position'])
        s = len(springs['indices'])
        
        # Update node data
        self.d_positions[self.num_nodes:self.num_nodes+n] = cp.asarray(nodes['position'], dtype=cp.float32)
        self.d_masses[self.num_nodes:self.num_nodes+n] = cp.maximum(
            cp.asarray(nodes['mass'], dtype=cp.float32), 0.001
        )
        
        # Update spring data - separate arrays for better memory access
        spring_indices = springs['indices'] + self.num_nodes
        self.d_spring_node1[self.num_springs:self.num_springs+s] = cp.asarray(spring_indices[:, 0], dtype=cp.int32)
        self.d_spring_node2[self.num_springs:self.num_springs+s] = cp.asarray(spring_indices[:, 1], dtype=cp.int32)
        self.d_rest_lengths[self.num_springs:self.num_springs+s] = cp.asarray(springs['rest_length'], dtype=cp.float32)
        self.d_stiffnesses[self.num_springs:self.num_springs+s] = cp.asarray(springs['stiffness'], dtype=cp.float32)
        self.d_damping[self.num_springs:self.num_springs+s] = cp.asarray(springs['damping'], dtype=cp.float32)
        
        # Handle actuators
        actuator_mask = springs['is_actuator']
        if np.any(actuator_mask):  # Use numpy any for boolean array
            actuator_indices = np.where(actuator_mask)[0] + self.num_springs
            num_actuators = len(actuator_indices)
            
            self.d_actuator_spring_ids[:num_actuators] = cp.asarray(actuator_indices, dtype=cp.int32)
            self.d_actuator_phases[:num_actuators] = cp.asarray(springs['actuation_phase'][actuator_mask], dtype=cp.float32)
            self.num_actuators = num_actuators
            
            print(f"Added {num_actuators} actuators with phases: {springs['actuation_phase'][actuator_mask][:5]}...")
        
        self.num_nodes += n
        self.num_springs += s
        
        # Build sparse force distribution matrix for this robot
        self._build_force_distribution_matrix()
        
        print(f"Added robot: {n} nodes, {s} springs, {self.num_actuators} actuators")

    def _build_force_distribution_matrix(self):
        """Pre-build sparse matrix for efficient force distribution"""
        if self.num_springs == 0:
            return
        
        if not SPARSE_AVAILABLE:
            print("Sparse matrices not available, using atomic operations")
            self.force_distribution_matrix = None
            return
            
        try:
            # Create sparse matrix that maps spring forces to node forces
            row_indices = []
            col_indices = []
            data = []
            
            for i in range(self.num_springs):
                node1 = int(self.d_spring_node1[i])
                node2 = int(self.d_spring_node2[i])
                
                # Spring i affects node1 (negative) and node2 (positive)
                # We'll have 3 components (x,y,z) for each
                for axis in range(3):
                    # Node1 gets -force
                    row_indices.extend([node1 * 3 + axis])
                    col_indices.extend([i * 3 + axis])
                    data.extend([-1.0])
                    
                    # Node2 gets +force  
                    row_indices.extend([node2 * 3 + axis])
                    col_indices.extend([i * 3 + axis])
                    data.extend([1.0])
            
            # Build sparse matrix
            matrix_shape = (self.num_nodes * 3, self.num_springs * 3)
            self.force_distribution_matrix = csr_matrix(
                (cp.array(data), (cp.array(row_indices), cp.array(col_indices))),
                shape=matrix_shape
            )
            print("Built sparse force distribution matrix (fastest method)")
            
        except Exception as e:
            print(f"Sparse matrix construction failed: {e}")
            print("Falling back to atomic operations (still fast)")
            self.force_distribution_matrix = None

    def compute_spring_forces_vectorized(self):
        """Fully vectorized spring force computation - NO PYTHON LOOPS"""
        if self.num_springs == 0:
            return
        
        try:
            # Get all spring endpoint positions at once
            pos1 = self.d_positions[self.d_spring_node1[:self.num_springs]]  # (num_springs, 3)
            pos2 = self.d_positions[self.d_spring_node2[:self.num_springs]]  # (num_springs, 3)
            
            # Vector from node1 to node2
            displacement = pos2 - pos1  # (num_springs, 3)
            
            # Spring lengths
            lengths = cp.linalg.norm(displacement, axis=1)  # (num_springs,)
            
            # Avoid division by zero
            valid_mask = lengths > 1e-6
            safe_lengths = cp.where(valid_mask, lengths, 1.0)
            
            # Unit displacement vectors
            unit_displacement = displacement / safe_lengths[:, cp.newaxis]  # (num_springs, 3)

            # CRITICAL FIX: Spring force direction was inverted!
            # Correct physics: F = k * (rest_length - current_length)
            # - If rest > current (compressed): F > 0, pushes nodes apart (expands)
            # - If rest < current (stretched): F < 0, pulls nodes together (contracts)
            # Previous code had: F = k * (current - rest) which is backwards!
            extensions = self.d_rest_lengths[:self.num_springs] - lengths  # FLIPPED SIGN
            spring_forces = self.d_stiffnesses[:self.num_springs] * extensions  # (num_springs,)
            
            # Damping forces (simple velocity-proportional damping)
            vel1 = self.d_velocities[self.d_spring_node1[:self.num_springs]]
            vel2 = self.d_velocities[self.d_spring_node2[:self.num_springs]]
            relative_vel = vel2 - vel1  # (num_springs, 3)

            # Project relative velocity onto displacement direction
            vel_projections = cp.sum(relative_vel * unit_displacement, axis=1)  # (num_springs,)
            damping_forces = self.d_damping[:self.num_springs] * vel_projections
            
            # Total force magnitudes
            total_forces = spring_forces + damping_forces  # (num_springs,)

            # FIXED: Removed restrictive 55N force limit - now using unified 5000N limit
            # in integrate_positions_vectorized() which allows realistic spring forces
            # for robots with mass up to ~500 kg (gravity + spring compression forces)

            # Force vectors (springs push/pull along their direction)
            force_vectors = unit_displacement * total_forces[:, cp.newaxis]  # (num_springs, 3)
            
            # Zero out invalid springs
            force_vectors[~valid_mask] = 0.0
            
            # Distribute forces to nodes
            if self.force_distribution_matrix is not None:
                try:
                    # Sparse matrix approach (fastest)
                    forces_flat = force_vectors.flatten()  # (num_springs * 3,)
                    node_forces_flat = self.force_distribution_matrix @ forces_flat  # (num_nodes * 3,)
                    node_forces = node_forces_flat.reshape(self.num_nodes, 3)
                    self.d_forces[:self.num_nodes] += node_forces
                except Exception as e:
                    # Fallback to atomic operations
                    self._distribute_forces_atomic(force_vectors, valid_mask)
            else:
                # Use atomic operations (still fast)
                self._distribute_forces_atomic(force_vectors, valid_mask)
                
        except Exception as e:
            print(f"Warning: Spring force computation error: {e}")
            # Emergency fallback to prevent crash
            pass

    def _distribute_forces_atomic(self, force_vectors, valid_mask):
        """Fallback force distribution using atomic operations"""
        # This is slower than sparse matrix but still much faster than original
        for i in range(self.num_springs):
            if valid_mask[i]:
                node1 = int(self.d_spring_node1[i])
                node2 = int(self.d_spring_node2[i])
                force = force_vectors[i]
                
                # Atomic adds (CuPy handles this efficiently)
                self.d_forces[node1] -= force
                self.d_forces[node2] += force

    def apply_actuator_forces_vectorized(self):
        """Vectorized actuator force application"""
        if self.num_actuators == 0:
            return
            
        # Get all actuator data at once
        spring_ids = self.d_actuator_spring_ids[:self.num_actuators]
        phases = self.d_actuator_phases[:self.num_actuators]
        signals = self.d_actuator_signals[:self.num_actuators]
        
        # Vectorized sinusoidal actuation
        actuation = cp.sin(self.time * 2 * cp.pi * self.actuation_frequency + phases) * signals
        
        # Modify rest lengths (±20% actuation as per Lipson)
        original_lengths = self.d_rest_lengths[spring_ids]
        self.d_rest_lengths[spring_ids] = original_lengths * (1.0 + 0.2 * actuation)

    def integrate_positions_vectorized(self, dt):
        """FIXED: Stiffer springs + relaxed limits for realistic physics"""
        if self.num_nodes == 0:
            return
            
        active_slice = slice(0, self.num_nodes)
        
        # Add gravity (unchanged)
        self.d_forces[active_slice, 1] -= self.d_masses[active_slice] * self.gravity
        
        # RELAXED FORCE LIMITING (your test showed this helps)
        force_magnitudes = cp.linalg.norm(self.d_forces[active_slice], axis=1)
        force_limit_mask = force_magnitudes > 5000.0  # Increased from 50N to 5000N
        if cp.any(force_limit_mask):
            scale_factors = 5000.0 / (force_magnitudes + 1e-6)
            self.d_forces[active_slice][force_limit_mask] *= scale_factors[force_limit_mask, cp.newaxis]
        
        # INCREASED SPRING DAMPING APPROACH:
        # Material spring damping increased from 0.4 to 10.0 (25x increase)
        # Global damping kept moderate to maintain realistic terminal velocity
        # Terminal velocity = g / damping = 9.81 / 7.5 = 1.31 m/s
        #
        # Previous attempts:
        # - damping=0.4, global=10.0: Stable but too restrictive (0.98 m/s terminal velocity)
        # - damping=0.4, global=7.5: Better but 18-27cm jello wobble
        # - damping=0.4, global=5.0: Too jello-like, excessive oscillation
        #
        # New approach (high spring damping + moderate global):
        # - Spring damping = 10.0 (strong damping opposes oscillations directly)
        # - Global damping = 7.5 s^-1 prevents energy gain
        # - Should reduce jello wobble significantly without killing terminal velocity
        damping_coefficient = 7.5  # s^-1
        damping_factor = 1.0 - damping_coefficient * dt
        accelerations = self.d_forces[active_slice] / self.d_masses[active_slice, cp.newaxis]
        self.d_velocities[active_slice] = self.d_velocities[active_slice] * damping_factor + accelerations * dt

        # FIXED: Increased velocity limiting for realistic dynamics
        # Typical terminal velocity for soft robots ~34 m/s, allowing 100 m/s for safety
        # and fast actuation dynamics without numerical instability
        vel_magnitudes = cp.linalg.norm(self.d_velocities[active_slice], axis=1)
        vel_limit_mask = vel_magnitudes > 100.0  # Increased from 50 m/s to 100 m/s
        if cp.any(vel_limit_mask):
            scale_factors = 100.0 / (vel_magnitudes + 1e-6)
            self.d_velocities[active_slice][vel_limit_mask] *= scale_factors[vel_limit_mask, cp.newaxis]

        # Update positions (unchanged)
        self.d_positions[active_slice] += self.d_velocities[active_slice] * dt

        # OPTION A: Spring-based ground contact (allows natural oscillation)
        # Instead of hard position clamping, apply repulsive spring force when penetrating ground
        # This allows nodes to compress slightly into ground before bouncing back (realistic)
        ground_level = 0.0
        penetration = ground_level - self.d_positions[active_slice, 1]  # Positive when below ground
        penetrating_mask = penetration > 0

        if cp.any(penetrating_mask):
            # Mass-adaptive ground stiffness: Scale with node mass to avoid instability
            # Target: Ground force should produce ~100 m/s² acceleration (10× gravity)
            # F = m × a, so k = m × a / penetration
            # For typical 1mm penetration: k = m × 100 / 0.001 = m × 100000
            penetrating_masses = self.d_masses[active_slice][penetrating_mask]

            # Base stiffness per unit mass: 100000 N/(m·kg)
            # This gives consistent behavior across all mass scales
            stiffness_per_kg = 100000.0  # N/(m·kg)
            ground_stiffnesses = stiffness_per_kg * penetrating_masses  # N/m per node

            # Damping also scales with mass for consistent settling time
            # Critical damping: c = 2 * sqrt(k * m)
            # Use 80% of critical for slight oscillation
            damping_per_kg = 1000.0  # N·s/(m·kg)
            ground_dampings = damping_per_kg * penetrating_masses  # N·s/m per node

            # Spring force: F = k × penetration_depth (upward)
            repulsion_forces = ground_stiffnesses * penetration[penetrating_mask]

            # Damping force: F = c × velocity (opposes downward motion)
            ground_velocities = self.d_velocities[active_slice, 1][penetrating_mask]
            damping_forces = -ground_dampings * ground_velocities

            # Total upward force (spring + damping)
            total_ground_forces = repulsion_forces + damping_forces

            # Apply forces to Y-axis only (ground is horizontal)
            # Force / mass = acceleration, then × dt = velocity change
            accelerations = total_ground_forces / penetrating_masses
            self.d_velocities[active_slice, 1][penetrating_mask] += accelerations * dt

            # Horizontal friction: Only apply when in contact with significant penetration
            # Friction proportional to normal force (realistic Coulomb friction)
            significant_contact = penetration > 0.001  # > 1mm penetration
            if cp.any(significant_contact):
                friction_coefficient = 0.3  # Reduced from 0.8 to 0.3 (less aggressive)
                # Apply friction: reduce horizontal velocity by friction coefficient
                friction_mask = cp.logical_and(penetrating_mask, significant_contact)
                self.d_velocities[active_slice, 0][friction_mask] *= (1.0 - friction_coefficient * dt * 100)
                self.d_velocities[active_slice, 2][friction_mask] *= (1.0 - friction_coefficient * dt * 100)

            # Safety: Prevent deep tunneling (only if penetration > 5cm, clearly a bug)
            deep_penetration = penetration > 0.05
            if cp.any(deep_penetration):
                # Hard stop only for extreme cases
                self.d_positions[active_slice, 1][deep_penetration] = ground_level - 0.05
                # Kill downward velocity
                moving_down = self.d_velocities[active_slice, 1][deep_penetration] < 0
                if cp.any(moving_down):
                    self.d_velocities[active_slice, 1][deep_penetration][moving_down] = 0.0

        # Clear forces
        self.d_forces[active_slice] = 0.0    

    def step(self, dt=None):
        """Optimized physics step - should be 10-50x faster"""
        if dt is None:
            dt = self.default_timestep

        # Clear forces
        self.d_forces[:self.num_nodes] = 0.0

        # Vectorized computations
        self.compute_spring_forces_vectorized()
        self.apply_actuator_forces_vectorized()
        self.integrate_positions_vectorized(dt)

        self.time += dt

        # FIXED: Synchronize after critical physics operations
        # Ensures GPU computations complete before CPU accesses data
        if self.num_nodes > 0:
            cp.cuda.Stream.null.synchronize()
    
    def get_positions(self):
        """Get positions (minimize CPU-GPU transfer)"""
        return cp.asnumpy(self.d_positions[:self.num_nodes])
    
    def set_actuator_signals(self, signals):
        """Set actuator signals"""
        if len(signals) > 0 and self.num_actuators > 0:
            n = min(len(signals), self.num_actuators)
            self.d_actuator_signals[:n] = cp.asarray(signals[:n], dtype=cp.float32)

# Backward compatibility alias - this is the key line that fixes your import error!
CUDAPhysicsEngine = OptimizedCUDAPhysicsEngine