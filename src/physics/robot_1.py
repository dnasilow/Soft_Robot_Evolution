import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict

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
MATERIALS = {
    0: None,  # Empty
    1: VoxelMaterial(young_modulus=1e6, poisson_ratio=0.35, density=1000.0, damping=0.1, is_actuated=True, actuation_phase=0.0, actuation_strength=0.2),      # Green (0°)
    2: VoxelMaterial(young_modulus=1e6, poisson_ratio=0.35, density=1000.0, damping=0.1, is_actuated=True, actuation_phase=np.pi, actuation_strength=0.2),    # Red (180°)
    3: VoxelMaterial(young_modulus=0.1e6, poisson_ratio=0.45, density=800.0, damping=0.2, is_actuated=False),    # Light Blue (soft passive)
    4: VoxelMaterial(young_modulus=10e6, poisson_ratio=0.25, density=1200.0, damping=0.05, is_actuated=False),      # Dark Blue (stiff passive)
}

# Color mapping for visualization
MATERIAL_COLORS = {
    0: (0, 0, 0),        # Black (empty - shouldn't be visible)
    1: (0, 255, 0),      # Green - Active 0°
    2: (255, 0, 0),      # Red - Active 180°
    3: (173, 216, 230),  # Light Blue - Soft passive
    4: (0, 0, 139),      # Dark Blue - Stiff passive
}


class VoxelRobot:
    def __init__(self, voxel_grid, voxel_size=0.01):
        """
        Initialize voxel-based soft robot
        
        Args:
            voxel_grid: 3D numpy array with material indices (0=empty, 1=soft, 2=rigid, 3=actuated)
            voxel_size: Size of each voxel in meters
        """
        self.voxel_grid = voxel_grid
        self.voxel_size = voxel_size
        self.shape = voxel_grid.shape
        
        # Build mass-spring system
        self.nodes = []
        self.springs = []
        self.voxel_to_nodes = {}
        
        self._build_structure()

    def _build_structure(self):
        """Convert voxel grid to mass-spring system"""
        node_index = 0
        
        # Create nodes at voxel corners
        for x in range(self.shape[0] + 1):
            for y in range(self.shape[1] + 1):
                for z in range(self.shape[2] + 1):
                    # Check if node is needed (adjacent to non-empty voxel)
                    needed = False
                    for dx in [-1, 0]:
                        for dy in [-1, 0]:
                            for dz in [-1, 0]:
                                vx, vy, vz = x + dx, y + dy, z + dz
                                if (0 <= vx < self.shape[0] and 
                                    0 <= vy < self.shape[1] and 
                                    0 <= vz < self.shape[2]):
                                    if self.voxel_grid[vx, vy, vz] != 0:  # Not empty
                                        needed = True
                                        break
                    
                    if needed:
                        position = np.array([x, y, z]) * self.voxel_size
                        self.nodes.append({
                            'position': position,
                            'mass': 0.0,  # Will be updated based on voxels
                            'index': node_index
                        })
                        self.voxel_to_nodes[(x, y, z)] = node_index
                        node_index += 1
        
        # Create springs and distribute mass
        for x in range(self.shape[0]):
            for y in range(self.shape[1]):
                for z in range(self.shape[2]):
                    material_idx = self.voxel_grid[x, y, z]
                    if material_idx == 0:  # Empty
                        continue
                    
                    # Get material from fixed indexing
                    material = MATERIALS[material_idx]
                    if material is not None:  # Safety check
                        self._add_voxel_springs(x, y, z, material)
                        self._distribute_voxel_mass(x, y, z, material)
    
    def _add_voxel_springs(self, x, y, z, material):
        """Add springs for a single voxel"""
        # Get corner nodes
        corners = []
        for dx in [0, 1]:
            for dy in [0, 1]:
                for dz in [0, 1]:
                    node_pos = (x + dx, y + dy, z + dz)
                    if node_pos in self.voxel_to_nodes:
                        corners.append(self.voxel_to_nodes[node_pos])
        
        if len(corners) < 2:  # Need at least 2 nodes for a spring
            return
        
        # Edge springs (12 per voxel)
        edges = [
            (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
            (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)
        ]
        
        for i, j in edges:
            if i < len(corners) and j < len(corners):
                self._add_spring(corners[i], corners[j], material, 'edge')
        
        # Face diagonal springs (12 per voxel)
        face_diagonals = [
            (0, 3), (1, 2), (0, 5), (1, 4), (0, 6), (2, 4),
            (1, 7), (3, 5), (2, 7), (3, 6), (4, 7), (5, 6)
        ]
        
        for i, j in face_diagonals:
            if i < len(corners) and j < len(corners):
                self._add_spring(corners[i], corners[j], material, 'face')
        
        # Body diagonal springs (4 per voxel)
        body_diagonals = [(0, 7), (1, 6), (2, 5), (3, 4)]
        
        for i, j in body_diagonals:
            if i < len(corners) and j < len(corners):
                self._add_spring(corners[i], corners[j], material, 'body')

    def _add_spring(self, node1_idx, node2_idx, material, spring_type):
        """Add a spring between two nodes with Lipson-appropriate stiffness"""
        if node1_idx == node2_idx:
            return
            
        # Check if spring already exists
        for spring in self.springs:
            if (spring['indices'][0] == node1_idx and spring['indices'][1] == node2_idx) or \
               (spring['indices'][0] == node2_idx and spring['indices'][1] == node1_idx):
                return
        
        pos1 = self.nodes[node1_idx]['position']
        pos2 = self.nodes[node2_idx]['position']
        rest_length = np.linalg.norm(pos2 - pos1)
        
        # Convert Young's modulus to spring stiffness
        # K = E * A / L, where A is cross-sectional area, L is length
        cross_section_area = (self.voxel_size ** 2)  # Approximate as square cross-section
        base_stiffness = material.young_modulus * cross_section_area / rest_length
        
        # Adjust stiffness based on spring type (Lipson uses beam elements)
        stiffness_multipliers = {
            'edge': 1.0,      # Direct structural connections
            'face': 0.5,      # Diagonal face connections  
            'body': 0.25      # Body diagonal connections
        }
        stiffness = base_stiffness * stiffness_multipliers[spring_type]
        
        # Damping proportional to stiffness
        damping = material.damping * np.sqrt(stiffness)
        
        self.springs.append({
            'indices': [node1_idx, node2_idx],
            'rest_length': rest_length,
            'stiffness': stiffness,
            'damping': damping,
            'is_actuator': material.is_actuated,
            'actuation_phase': material.actuation_phase if material.is_actuated else 0.0,
            'material': material
        })

    def _distribute_voxel_mass(self, x, y, z, material):
        """Distribute voxel mass to corner nodes"""
        voxel_mass = material.density * (self.voxel_size ** 3)
        mass_per_corner = voxel_mass / 8.0
        
        # Ensure minimum mass to prevent numerical issues
        mass_per_corner = max(mass_per_corner, 0.001)  # Minimum 1 gram per corner
        
        for dx in [0, 1]:
            for dy in [0, 1]:
                for dz in [0, 1]:
                    node_pos = (x + dx, y + dy, z + dz)
                    if node_pos in self.voxel_to_nodes:
                        node_idx = self.voxel_to_nodes[node_pos]
                        self.nodes[node_idx]['mass'] += mass_per_corner

    def get_nodes(self):
        """Get node data for physics engine"""
        return {
            'position': np.array([n['position'] for n in self.nodes]),
            'mass': np.array([n['mass'] for n in self.nodes])
        }
    
    def get_springs(self):
        """Get spring data for physics engine with proper phase information"""
        return {
            'indices': np.array([s['indices'] for s in self.springs]),
            'rest_length': np.array([s['rest_length'] for s in self.springs]),
            'stiffness': np.array([s['stiffness'] for s in self.springs]),
            'damping': np.array([s['damping'] for s in self.springs]),
            'is_actuator': np.array([s['is_actuator'] for s in self.springs]),
            'actuation_phase': np.array([s['actuation_phase'] for s in self.springs])  # Add this!
        }
    
    def get_center_of_mass(self, positions=None):
            """Calculate center of mass"""
            if positions is None:
                positions = np.array([n['position'] for n in self.nodes])
            
            if len(self.nodes) == 0 or len(positions) == 0:
                return np.zeros(3)
                
            masses = np.array([n['mass'] for n in self.nodes])
            
            # Check for zero or invalid masses
            valid_masses = masses > 0
            if not np.any(valid_masses):
                # If all masses are zero or negative, return geometric center
                return np.mean(positions, axis=0)
            
            # Use only valid masses
            valid_positions = positions[valid_masses]
            valid_masses = masses[valid_masses]
            
            total_mass = np.sum(valid_masses)
            if total_mass > 0:
                com = np.sum(valid_positions * valid_masses[:, np.newaxis], axis=0) / total_mass
                
                # Check for NaN
                if np.any(np.isnan(com)):
                    print(f"Warning: COM calculation resulted in NaN. Using geometric center.")
                    return np.mean(positions, axis=0)
                
                return com
            else:
                return np.mean(positions, axis=0)
    
    def get_bounding_box_size(self):
        """Get robot bounding box dimensions"""
        if len(self.nodes) == 0:
            return np.zeros(3)
        positions = np.array([n['position'] for n in self.nodes])
        min_pos = np.min(positions, axis=0)
        max_pos = np.max(positions, axis=0)
        return max_pos - min_pos