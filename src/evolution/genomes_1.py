import numpy as np
from abc import ABC, abstractmethod
import copy

class BaseGenome(ABC):
    """Abstract base class for robot genomes"""
    
    @abstractmethod
    def to_phenotype(self):
        """Convert genome to robot structure"""
        pass
    
    @abstractmethod
    def mutate(self, mutation_rate=0.1):
        """Apply mutations to genome"""
        pass
    
    @abstractmethod
    def crossover(self, other):
        """Crossover with another genome"""
        pass
    
    @abstractmethod
    def copy(self):
        """Create deep copy of genome"""
        pass

# class DirectVoxelGenome(BaseGenome):
#     """Direct encoding of voxel materials and actuator phases"""
    
#     def __init__(self, shape=(10, 10, 10), init_random=True):
#         self.shape = shape
#         self.voxels = np.zeros(shape, dtype=np.int8)
#         self.actuator_phases = np.zeros(shape, dtype=np.float32)
        
#         if init_random:
#             self.randomize()
    
#         def __init__(self, shape=(10, 10, 10), init_random=True):  # Default 10x10x10 as per Lipson
#         self.shape = shape
#         self.voxels = np.zeros(shape, dtype=np.int8)
        
#         if init_random:
#             self.randomize()
    
#     def randomize(self):
#         """Initialize with Lipson-style CPPN-like pattern in 10x10x10 grid"""
#         center = np.array(self.shape) // 2
        
#         # Query each voxel position in the full 10x10x10 grid
#         for x in range(self.shape[0]):
#             for y in range(self.shape[1]):
#                 for z in range(self.shape[2]):
#                     # Normalize coordinates to [-1, 1] as CPPN inputs
#                     norm_x = (x - center[0]) / (self.shape[0] / 2)
#                     norm_y = (y - center[1]) / (self.shape[1] / 2) 
#                     norm_z = (z - center[2]) / (self.shape[2] / 2)
                    
#                     # Distance from center
#                     distance = np.sqrt(norm_x**2 + norm_y**2 + norm_z**2)
                    
#                     # Simple CPPN-like function to determine voxel presence and type
#                     # This simulates CPPN output - in real implementation, use actual CPPN
#                     voxel_presence = np.sin(norm_x * 3) * np.cos(norm_y * 3) * np.exp(-distance)
#                     # Now uses the real CPPN network with evolved topology
#                     self.cppn = CPPNGenome(num_inputs=4, num_outputs=5)  
#                     cppn_outputs = self.cppn.evaluate(norm_x, norm_y, norm_z, distance)
                    
#                     if voxel_presence > 0.1:  # Threshold for voxel presence
#                         # Use simple pattern to assign material types
#                         # In real implementation, CPPN would have 4 outputs for material selection
#                         material_val = np.sin(norm_x * 2) + np.cos(norm_z * 2)
                        
#                         if material_val > 0.5:
#                             self.voxels[x, y, z] = 1  # Green active
#                         elif material_val > 0.0:
#                             self.voxels[x, y, z] = 2  # Red active  
#                         elif material_val > -0.5:
#                             self.voxels[x, y, z] = 3  # Light blue soft
#                         else:
#                             self.voxels[x, y, z] = 4  # Dark blue stiff
        
#         print(f"Generated robot with materials: {np.bincount(self.voxels.flatten())}")

#     # AFTER - Lipson-style 20% actuation
#     # def randomize(self):
#     #     """Initialize with Lipson-style parameters: 10x10x10 grid, 20% actuation"""
#     #     center = np.array(self.shape) // 2
        
#     #     # First pass: create basic robot shape
#     #     for x in range(self.shape[0]):
#     #         for y in range(self.shape[1]):
#     #             for z in range(self.shape[2]):
#     #                 dist = np.linalg.norm([x - center[0], y - center[1], z - center[2]])
                    
#     #                 # Larger radius for 10x10x10 grid
#     #                 if dist <= 4:  # Radius 4 instead of 2
#     #                     if np.random.random() < 0.4:  # 40% density (like Lipson)
#     #                         # Start with soft or rigid materials
#     #                         self.voxels[x, y, z] = np.random.choice([1, 2], p=[0.7, 0.3])
        
#     #     # Second pass: convert ~20% of existing voxels to actuators
#     #     existing_voxels = np.where(self.voxels != 0)
#     #     num_existing = len(existing_voxels[0])
        
#     #     if num_existing > 0:
#     #         # Select 20% of existing voxels to become actuators
#     #         num_actuators = max(1, int(0.2 * num_existing))
#     #         indices = np.random.choice(num_existing, num_actuators, replace=False)
            
#     #         for i in indices:
#     #             x, y, z = existing_voxels[0][i], existing_voxels[1][i], existing_voxels[2][i]
#     #             self.voxels[x, y, z] = 3  # Convert to actuated
#     #             self.actuator_phases[x, y, z] = np.random.uniform(0, 2*np.pi)

#     def mutate(self, mutation_rate=0.1):
#         """Apply mutations"""
#         # Material mutations
#         mask = np.random.random(self.shape) < mutation_rate
#         mutations = np.random.randint(0, 4, self.shape)
#         self.voxels[mask] = mutations[mask]
        
#         # Phase mutations for actuators
#         actuator_mask = (self.voxels == 3) & mask
#         self.actuator_phases[actuator_mask] += np.random.normal(0, 0.5, np.sum(actuator_mask))
#         self.actuator_phases = np.mod(self.actuator_phases, 2*np.pi)
        
#         # Ensure connectivity (simple check)
#         self._ensure_connectivity()
    
#     def crossover(self, other):
#         """Single-point crossover"""
#         child1 = self.copy()
#         child2 = other.copy()
        
#         # Random crossover plane
#         axis = np.random.randint(0, 3)
#         point = np.random.randint(1, self.shape[axis])
        
#         if axis == 0:
#             child1.voxels[point:, :, :] = other.voxels[point:, :, :]
#             child2.voxels[point:, :, :] = self.voxels[point:, :, :]
#         elif axis == 1:
#             child1.voxels[:, point:, :] = other.voxels[:, point:, :]
#             child2.voxels[:, point:, :] = self.voxels[:, point:, :]
#         else:
#             child1.voxels[:, :, point:] = other.voxels[:, :, point:]
#             child2.voxels[:, :, point:] = self.voxels[:, :, point:]
        
#         return child1, child2
    
#     def _ensure_connectivity(self):
#         """Ensure robot is one connected component"""
#         # Simple flood fill from center
#         visited = np.zeros(self.shape, dtype=bool)
#         center = tuple(np.array(self.shape) // 2)
        
#         # Find nearest non-empty voxel to center
#         if self.voxels[center] == 0:
#             for radius in range(1, max(self.shape)):
#                 found = False
#                 for x in range(max(0, center[0]-radius), min(self.shape[0], center[0]+radius+1)):
#                     for y in range(max(0, center[1]-radius), min(self.shape[1], center[1]+radius+1)):
#                         for z in range(max(0, center[2]-radius), min(self.shape[2], center[2]+radius+1)):
#                             if self.voxels[x, y, z] != 0:
#                                 center = (x, y, z)
#                                 found = True
#                                 break
#                         if found: break
#                     if found: break
#                 if found: break
        
#         # Flood fill from center
#         stack = [center]
#         component = []
        
#         while stack:
#             pos = stack.pop()
#             if visited[pos]:
#                 continue
            
#             visited[pos] = True
#             if self.voxels[pos] != 0:
#                 component.append(pos)
                
#                 # Add neighbors
#                 for dx, dy, dz in [(-1,0,0), (1,0,0), (0,-1,0), (0,1,0), (0,0,-1), (0,0,1)]:
#                     nx, ny, nz = pos[0]+dx, pos[1]+dy, pos[2]+dz
#                     if (0 <= nx < self.shape[0] and 0 <= ny < self.shape[1] and 
#                         0 <= nz < self.shape[2] and not visited[nx, ny, nz]):
#                         stack.append((nx, ny, nz))
        
#         # Keep only largest component
#         new_voxels = np.zeros_like(self.voxels)
#         for pos in component:
#             new_voxels[pos] = self.voxels[pos]
#         self.voxels = new_voxels
    
#     def to_phenotype(self):
#         """Convert to robot structure"""
#         from src.physics.robot import VoxelRobot
#         return VoxelRobot(self.voxels)
    
#     def copy(self):
#         """Deep copy"""
#         new_genome = DirectVoxelGenome(self.shape, init_random=False)
#         new_genome.voxels = self.voxels.copy()
#         new_genome.actuator_phases = self.actuator_phases.copy()
#         return new_genome

class DirectVoxelGenome(BaseGenome):
    """Direct encoding using actual CPPN for pattern generation"""
    
    def __init__(self, shape=(10, 10, 10), init_random=True):
        self.shape = shape
        self.voxels = np.zeros(shape, dtype=np.int8)
        
        # Create a real CPPN for pattern generation
        self.cppn = CPPNGenome(num_inputs=4, num_outputs=5)  # Use the existing CPPN class!
        
        if init_random:
            self.randomize()
    
    def randomize(self):
        """Use actual CPPN to generate robot patterns"""
        print("Generating robot using real CPPN...")
        
        center = np.array(self.shape) / 2
        
        # Query CPPN for each voxel position in 10x10x10 grid
        for x in range(self.shape[0]):
            for y in range(self.shape[1]):
                for z in range(self.shape[2]):
                    # Normalize coordinates to [-1, 1] as CPPN inputs
                    norm_x = (x - center[0]) / (self.shape[0] / 2)
                    norm_y = (y - center[1]) / (self.shape[1] / 2)
                    norm_z = (z - center[2]) / (self.shape[2] / 2)
                    
                    # Distance from center
                    distance = np.sqrt(norm_x**2 + norm_y**2 + norm_z**2)
                    
                    # Query the actual CPPN network
                    cppn_outputs = self.cppn.evaluate(norm_x, norm_y, norm_z, distance)
                    
                    # Interpret CPPN outputs
                    # Output 0: voxel presence threshold
                    if cppn_outputs[0] > 0.0:  # Voxel exists
                        # Outputs 1-4: material type selection
                        material_outputs = cppn_outputs[1:5]

                        # Softmac Selection (Most Lipson-like)
                        # Apply softmax for probabilistic selection
                        exp_logits = np.exp(material_outputs - np.max(material_outputs))  # Numerical stability
                        probabilities = exp_logits / np.sum(exp_logits)
                        material_index = np.random.choice([1, 2, 3, 4], p=probabilities) # Sample material based on probabilities
                        
                        #Treshold-Based Selection - The material has to have a certain treshold to be selected
                        # # Normalize and apply individual thresholds
                        # material_scores = (material_scores + 1) / 2  # Map [-1,1] to [0,1]                    
                        # # Select materials that exceed threshold
                        # active_materials = [i+1 for i, score in enumerate(material_scores) if score > 0.6]                        
                        # if active_materials:
                        #     material_index = np.random.choice(active_materials)
                        # else:
                        #     material_index = np.random.choice([1, 2, 3, 4])  # Fallback


                        # Current method of slecting materials - winner's take it all
                        #material_index = np.argmax(material_outputs) + 1  # 1-4

                        self.voxels[x, y, z] = material_index
        
        # Print material distribution
        unique, counts = np.unique(self.voxels, return_counts=True)
        material_counts = dict(zip(unique, counts))
        print(f"Generated robot with materials: {material_counts}")
        
        # Ensure we have at least some voxels
        if np.sum(self.voxels > 0) == 0:
            print("Warning: CPPN generated empty robot, adding center voxel")
            center_pos = tuple(self.shape[i] // 2 for i in range(3))
            self.voxels[center_pos] = 1  # Add green actuator at center
    
    def to_phenotype(self):
        """Convert genome to robot structure - MISSING METHOD FIXED"""
        from src.physics.robot import VoxelRobot  # Import here to avoid circular imports
        return VoxelRobot(self.voxels)
    
    def mutate(self, mutation_rate=0.1):
        """Mutate the underlying CPPN, then regenerate voxels"""
        # Mutate the CPPN network
        self.cppn.mutate(mutation_rate)
        
        # Regenerate voxel pattern from mutated CPPN
        old_pattern = self.voxels.copy()
        self.randomize()  # This uses the mutated CPPN
        
        # Optional: track how much the pattern changed
        changes = np.sum(old_pattern != self.voxels)
        total_voxels = np.prod(self.shape)
        change_percentage = changes / total_voxels * 100
        print(f"Mutation changed {change_percentage:.1f}% of voxels")
    
    def crossover(self, other):
        """Crossover between two CPPN genomes"""
        child1 = DirectVoxelGenome(self.shape, init_random=False)
        child2 = DirectVoxelGenome(self.shape, init_random=False)
        
        # Crossover the CPPNs
        child1.cppn, child2.cppn = self.cppn.crossover(other.cppn)
        
        # Generate voxel patterns from crossed-over CPPNs
        child1.randomize()
        child2.randomize()
        
        return child1, child2
    
    def copy(self):
        """Create a deep copy"""
        new_genome = DirectVoxelGenome(self.shape, init_random=False)
        new_genome.cppn = self.cppn.copy()
        new_genome.voxels = self.voxels.copy()
        return new_genome
    
    
class CPPNGenome(BaseGenome):
    """CPPN-NEAT genome for generative encoding"""
    
    def __init__(self, num_inputs=4, num_outputs=3):
        self.num_inputs = num_inputs  # x, y, z, distance_from_center
        self.num_outputs = num_outputs  # material_presence, material_type, actuator_phase
        
        # Node genes (id -> activation_function)
        self.nodes = {}
        self.node_counter = 0
        
        # Connection genes (innovation_number -> (from, to, weight, enabled))
        self.connections = {}
        self.innovation_counter = 0
        
        # Initialize minimal network
        self._initialize_minimal_network()
    
    def _initialize_minimal_network(self):
        """Create initial fully connected network"""
        # Input nodes
        for i in range(self.num_inputs):
            self.nodes[self.node_counter] = {'type': 'input', 'activation': 'linear'}
            self.node_counter += 1
        
        # Output nodes
        for i in range(self.num_outputs):
            self.nodes[self.node_counter] = {'type': 'output', 'activation': 'tanh'}
            self.node_counter += 1
        
        # Hidden layer
        hidden_size = 5
        for i in range(hidden_size):
            activation = np.random.choice(['tanh', 'sin', 'gaussian', 'relu'])
            self.nodes[self.node_counter] = {'type': 'hidden', 'activation': activation}
            self.node_counter += 1
        
        # Connect inputs to hidden
        for i in range(self.num_inputs):
            for h in range(self.num_inputs + self.num_outputs, 
                           self.num_inputs + self.num_outputs + hidden_size):
                self.connections[self.innovation_counter] = {
                    'from': i,
                    'to': h,
                    'weight': np.random.randn() * 0.5,
                    'enabled': True
                }
                self.innovation_counter += 1
        
        # Connect hidden to outputs
        for h in range(self.num_inputs + self.num_outputs, 
                       self.num_inputs + self.num_outputs + hidden_size):
            for o in range(self.num_inputs, self.num_inputs + self.num_outputs):
                self.connections[self.innovation_counter] = {
                    'from': h,
                    'to': o,
                    'weight': np.random.randn() * 0.5,
                    'enabled': True
                }
                self.innovation_counter += 1
    
    def evaluate(self, x, y, z, dist):
        """Evaluate CPPN at given coordinates"""
        # Prepare node values
        node_values = {}
        
        # Set input values
        node_values[0] = x
        node_values[1] = y
        node_values[2] = z
        node_values[3] = dist
        
        # Topological sort for evaluation order
        evaluated = set(range(self.num_inputs))
        
        # Evaluate network
        while len(evaluated) < len(self.nodes):
            for node_id, node_info in self.nodes.items():
                if node_id in evaluated:
                    continue
                
                # Check if all inputs are ready
                inputs_ready = True
                incoming = []
                
                for conn in self.connections.values():
                    if conn['to'] == node_id and conn['enabled']:
                        if conn['from'] not in evaluated:
                            inputs_ready = False
                            break
                        incoming.append((conn['from'], conn['weight']))
                
                if inputs_ready:
                    # Calculate node value
                    if node_info['type'] == 'input':
                        continue  # Already set
                    
                    # Sum weighted inputs
                    total = sum(node_values[from_node] * weight 
                              for from_node, weight in incoming)
                    
                    # Apply activation
                    activation = node_info['activation']
                    if activation == 'tanh':
                        node_values[node_id] = np.tanh(total)
                    elif activation == 'sin':
                        node_values[node_id] = np.sin(total * np.pi)
                    elif activation == 'gaussian':
                        node_values[node_id] = np.exp(-total * total)
                    elif activation == 'relu':
                        node_values[node_id] = max(0, total)
                    else:  # linear
                        node_values[node_id] = total
                    
                    evaluated.add(node_id)
        
        # Return output values
        outputs = []
        for i in range(self.num_inputs, self.num_inputs + self.num_outputs):
            outputs.append(node_values.get(i, 0.0))
        
        return outputs
    
    def mutate(self, mutation_rate=0.1):
        """NEAT-style mutations"""
        # Weight mutations
        for conn in self.connections.values():
            if np.random.random() < mutation_rate:
                if np.random.random() < 0.9:
                    # Perturb weight
                    conn['weight'] += np.random.randn() * 0.2
                else:
                    # Replace weight
                    conn['weight'] = np.random.randn()
        
        # Add node mutation
        if np.random.random() < mutation_rate * 0.3:
            self._mutate_add_node()
        
        # Add connection mutation
        if np.random.random() < mutation_rate * 0.5:
            self._mutate_add_connection()
    
    def _mutate_add_node(self):
        """Add a new node by splitting a connection"""
        enabled_connections = [i for i, c in self.connections.items() if c['enabled']]
        if not enabled_connections:
            return
        
        # Choose random connection to split
        conn_id = np.random.choice(enabled_connections)
        conn = self.connections[conn_id]
        
        # Disable old connection
        conn['enabled'] = False
        
        # Add new node
        new_node_id = self.node_counter
        self.nodes[new_node_id] = {
            'type': 'hidden',
            'activation': np.random.choice(['tanh', 'sin', 'gaussian', 'relu'])
        }
        self.node_counter += 1
        
        # Add two new connections
        self.connections[self.innovation_counter] = {
            'from': conn['from'],
            'to': new_node_id,
            'weight': 1.0,
            'enabled': True
        }
        self.innovation_counter += 1
        
        self.connections[self.innovation_counter] = {
            'from': new_node_id,
            'to': conn['to'],
            'weight': conn['weight'],
            'enabled': True
        }
        self.innovation_counter += 1
    
    def _mutate_add_connection(self):
        """Add a new connection between nodes"""
        # Get possible connections
        possible_from = list(self.nodes.keys())
        possible_to = [n for n, info in self.nodes.items() if info['type'] != 'input']
        
        # Try to find valid new connection
        for _ in range(10):
            from_node = np.random.choice(possible_from)
            to_node = np.random.choice(possible_to)
            
            # Check if connection already exists
            exists = False
            for conn in self.connections.values():
                if conn['from'] == from_node and conn['to'] == to_node:
                    exists = True
                    break
            
            if not exists and from_node != to_node:
                # Add new connection
                self.connections[self.innovation_counter] = {
                    'from': from_node,
                    'to': to_node,
                    'weight': np.random.randn() * 0.5,
                    'enabled': True
                }
                self.innovation_counter += 1
                break
    
    def crossover(self, other):
        """NEAT crossover"""
        # For simplicity, return copies with weight averaging
        child1 = self.copy()
        child2 = other.copy()
        
        # Average matching connections
        for inn_num in child1.connections:
            if inn_num in other.connections:
                if np.random.random() < 0.5:
                    child1.connections[inn_num]['weight'] = other.connections[inn_num]['weight']
        
        return child1, child2
    
    def to_phenotype(self, shape=(8, 8, 8)):
        """Generate voxel robot from CPPN"""
        voxels = np.zeros(shape, dtype=np.int8)
        phases = np.zeros(shape, dtype=np.float32)
        
        center = np.array(shape) / 2
        
        for x in range(shape[0]):
            for y in range(shape[1]):
                for z in range(shape[2]):
                    # Normalize coordinates
                    nx = 2 * x / shape[0] - 1
                    ny = 2 * y / shape[1] - 1
                    nz = 2 * z / shape[2] - 1
                    
                    # Distance from center
                    dist = np.linalg.norm([x - center[0], y - center[1], z - center[2]])
                    ndist = 2 * dist / np.linalg.norm(center) - 1
                    
                    # Query CPPN
                    outputs = self.evaluate(nx, ny, nz, ndist)
                    
                    # Interpret outputs
                    if outputs[0] > 0:  # Material presence
                        # Material type
                        mat_val = outputs[1]
                        if mat_val < -0.33:
                            voxels[x, y, z] = 1  # Soft
                        elif mat_val < 0.33:
                            voxels[x, y, z] = 2  # Rigid
                        else:
                            voxels[x, y, z] = 3  # Actuated
                            phases[x, y, z] = (outputs[2] + 1) * np.pi
        
        # Create genome with generated structure
        genome = DirectVoxelGenome(shape, init_random=False)
        genome.voxels = voxels
        genome.actuator_phases = phases
        
        return genome.to_phenotype()
    
    def copy(self):
        """Deep copy"""
        new_genome = CPPNGenome(self.num_inputs, self.num_outputs)
        new_genome.nodes = copy.deepcopy(self.nodes)
        new_genome.connections = copy.deepcopy(self.connections)
        new_genome.node_counter = self.node_counter
        new_genome.innovation_counter = self.innovation_counter
        return new_genome