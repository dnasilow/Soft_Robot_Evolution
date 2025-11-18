import numpy as np
from abc import ABC, abstractmethod
import copy
from numba import njit, prange

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

class OptimizedCPPNGenome:
    """Optimized CPPN with batch evaluation"""
    
    def __init__(self, num_inputs=4, num_outputs=5):
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.nodes = {}
        self.connections = {}
        self.node_counter = 0
        self.innovation_counter = 0
        
        # Cache for evaluation
        self._evaluation_cache = {}
        self._cache_enabled = True
        
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
        hidden_size = 8
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
                    'weight': np.random.randn() * 1.0,
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
                    'weight': np.random.randn() * 1.0,
                    'enabled': True
                }
                self.innovation_counter += 1
        print(f"Initialized CPPN with {len(self.nodes)} nodes and {len(self.connections)} connections")

    def evaluate_batch(self, coords_batch, distances_batch):
        """Batch evaluate CPPN for many positions at once"""
        batch_size = len(coords_batch)
        outputs = np.zeros((batch_size, self.num_outputs))
        
        # Vectorized evaluation where possible
        for i in range(batch_size):
            coord = coords_batch[i]
            outputs[i] = self.evaluate(coord[0], coord[1], coord[2], coord[3])
        
        return outputs
    
    def evaluate(self, x, y, z, dist):
        """Single CPPN evaluation with caching"""
        # Cache key for repeated evaluations
        if self._cache_enabled:
            cache_key = (round(x, 3), round(y, 3), round(z, 3), round(dist, 3))
            if cache_key in self._evaluation_cache:
                return self._evaluation_cache[cache_key]
        
        # Prepare node values
        node_values = {0: x, 1: y, 2: z, 3: dist}
        
        # Evaluation order (pre-computed for efficiency)
        evaluation_order = self._get_evaluation_order()
        
        # Fast evaluation using pre-computed order
        for node_id in evaluation_order:
            if node_id in node_values:
                continue
                
            node_info = self.nodes[node_id]
            if node_info['type'] == 'input':
                continue
            
            # Compute inputs
            total = 0.0
            for conn in self.connections.values():
                if conn['to'] == node_id and conn['enabled']:
                    total += node_values.get(conn['from'], 0.0) * conn['weight']
            
            # Apply activation (optimized)
            activation = node_info['activation']
            if activation == 'tanh':
                node_values[node_id] = np.tanh(total)
            elif activation == 'sin':
                node_values[node_id] = np.sin(total * np.pi)
            elif activation == 'gaussian':
                node_values[node_id] = np.exp(-total * total)
            elif activation == 'relu':
                node_values[node_id] = max(0.0, total)
            else:  # linear
                node_values[node_id] = total
        
        # Extract outputs
        outputs = []
        for i in range(self.num_inputs, self.num_inputs + self.num_outputs):
            outputs.append(node_values.get(i, 0.0))
        
        # Cache result
        if self._cache_enabled and len(self._evaluation_cache) < 10000:
            self._evaluation_cache[cache_key] = outputs.copy()
        
        return outputs
    
    def _get_evaluation_order(self):
        """Pre-compute evaluation order for efficiency"""
        if hasattr(self, '_cached_eval_order'):
            return self._cached_eval_order
        
        # Topological sort
        order = []
        visited = set(range(self.num_inputs))  # Inputs first
        
        while len(visited) < len(self.nodes):
            progress = False
            for node_id in self.nodes:
                if node_id in visited:
                    continue
                
                # Check if all dependencies are satisfied
                deps_satisfied = True
                for conn in self.connections.values():
                    if conn['to'] == node_id and conn['enabled']:
                        if conn['from'] not in visited:
                            deps_satisfied = False
                            break
                
                if deps_satisfied:
                    order.append(node_id)
                    visited.add(node_id)
                    progress = True
            
            if not progress:
                break  # Avoid infinite loops
        
        self._cached_eval_order = order
        return order
    
    def mutate(self, mutation_rate=0.1):
        """Optimized mutation with cache invalidation"""
        # Clear caches
        self._evaluation_cache.clear()
        if hasattr(self, '_cached_eval_order'):
            delattr(self, '_cached_eval_order')
        
        # Fast weight mutations (vectorized where possible)
        for conn in self.connections.values():
            if np.random.random() < mutation_rate:
                if np.random.random() < 0.9:
                    conn['weight'] += np.random.randn() * 0.2
                else:
                    conn['weight'] = np.random.randn()
        
        # Structural mutations (less frequent)
        if np.random.random() < mutation_rate * 0.3:
            self._mutate_add_node()
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
    
    def copy(self):
        """Fast copy"""
        new_genome = OptimizedCPPNGenome(self.num_inputs, self.num_outputs)
        new_genome.nodes = copy.deepcopy(self.nodes)
        new_genome.connections = copy.deepcopy(self.connections)
        new_genome.node_counter = self.node_counter
        new_genome.innovation_counter = self.innovation_counter
        return new_genome

class OptimizedDirectVoxelGenome(BaseGenome):
    """Optimized genome with fast CPPN evaluation and softmax selection"""
    
    def __init__(self, shape=(10, 10, 10), init_random=True):
        self.shape = shape
        self.voxels = np.zeros(shape, dtype=np.int8)
        
        # Create optimized CPPN
        self.cppn = OptimizedCPPNGenome(num_inputs=4, num_outputs=5)
        
        if init_random:
            self.randomize()
    
    def randomize(self):
        """Vectorized CPPN evaluation with softmax selection"""
        print("Generating robot using optimized CPPN with softmax selection...")
        
        # Pre-compute ALL coordinate queries at once (vectorized)
        coords, distances = self._generate_coordinate_arrays()
        
        # Batch evaluate CPPN for all positions
        all_outputs = self.cppn.evaluate_batch(coords, distances)
        
        # Vectorized softmax material selection
        self.voxels = self._apply_softmax_selection(all_outputs)
        
        # Print material distribution
        unique, counts = np.unique(self.voxels, return_counts=True)
        material_counts = dict(zip(unique, counts))
        print(f"Generated robot with materials: {material_counts}")
        
        # Ensure we have at least some voxels
        if np.sum(self.voxels > 0) == 0:
            print("Warning: CPPN generated empty robot, adding center voxel")
            center_pos = tuple(self.shape[i] // 2 for i in range(3))
            self.voxels[center_pos] = 1
    
    def _generate_coordinate_arrays(self):
        """Pre-compute all coordinate queries (vectorized)"""
        center = np.array(self.shape) / 2
        
        # Create coordinate meshgrid
        x_coords = np.arange(self.shape[0])
        y_coords = np.arange(self.shape[1]) 
        z_coords = np.arange(self.shape[2])
        
        X, Y, Z = np.meshgrid(x_coords, y_coords, z_coords, indexing='ij')
        
        # Normalize coordinates to [-1, 1]
        norm_X = (X - center[0]) / (self.shape[0] / 2)
        norm_Y = (Y - center[1]) / (self.shape[1] / 2)
        norm_Z = (Z - center[2]) / (self.shape[2] / 2)
        
        # Calculate distances
        distances = np.sqrt(norm_X**2 + norm_Y**2 + norm_Z**2)
        
        # Stack coordinates for batch processing
        coords = np.stack([norm_X.flatten(), norm_Y.flatten(), 
                          norm_Z.flatten(), distances.flatten()], axis=1)
        
        return coords, distances.flatten()
    
    def _apply_softmax_selection_fixed(self, all_outputs):
        """Apply softmax material selection with FIXED thresholds"""
        # Extract outputs
        presence_outputs = all_outputs[:, 0]  # First output
        material_logits = all_outputs[:, 1:5]  # Next 4 outputs
        
        # FIXED: Much more permissive presence threshold
        # Use adaptive threshold based on output distribution
        presence_threshold = np.percentile(presence_outputs, 70)  # Top 30% of positions
        presence_threshold = max(presence_threshold, -0.5)  # But not too restrictive
        
        print(f"Using presence threshold: {presence_threshold:.3f}")
        
        # Use numba-accelerated selection with FIXED threshold
        return self._apply_softmax_selection_numba_fixed(
            presence_outputs, material_logits, self.shape, presence_threshold
        )

    def _create_basic_robot(self):
        """Create a basic robot structure when CPPN fails"""
        print("Creating basic 3×3×3 robot structure...")
        center = np.array(self.shape) // 2
        
        # Create a 3×3×3 block around center
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for dz in range(-1, 2):
                    x, y, z = center[0] + dx, center[1] + dy, center[2] + dz
                    if 0 <= x < self.shape[0] and 0 <= y < self.shape[1] and 0 <= z < self.shape[2]:
                        # Create diverse materials
                        if dx == 0 and dy == 0 and dz == 0:
                            self.voxels[x, y, z] = 1  # Green actuator (center)
                        elif abs(dx) + abs(dy) + abs(dz) <= 2:
                            # Mix of materials for interesting dynamics
                            material_choice = np.random.choice([1, 2, 3, 4], p=[0.3, 0.3, 0.2, 0.2])
                            self.voxels[x, y, z] = material_choice

    @staticmethod
    @njit(parallel=True)
    def _apply_softmax_selection_numba(presence_outputs, material_logits, shape):
        """Numba-accelerated softmax selection"""
        voxels = np.zeros(shape, dtype=np.int8)
        flat_voxels = voxels.flatten()
        
        for i in prange(len(presence_outputs)):
            if presence_outputs[i] > 0.0:  # Voxel exists
                # Softmax with temperature for better exploration
                temperature = 2.0
                logits = material_logits[i] / temperature
                
                # Numerically stable softmax
                max_logit = np.max(logits)
                exp_logits = np.exp(logits - max_logit)
                probabilities = exp_logits / np.sum(exp_logits)
                
                # Sample from distribution
                rand_val = np.random.random()
                cumulative = 0.0
                material_index = 1  # Default
                
                for j in range(4):
                    cumulative += probabilities[j]
                    if rand_val <= cumulative:
                        material_index = j + 1
                        break
                
                flat_voxels[i] = material_index
        
        return voxels
    
    def _apply_softmax_selection(self, all_outputs):
        """Apply softmax material selection (optimized)"""
        # Extract outputs
        presence_outputs = all_outputs[:, 0]  # First output
        material_logits = all_outputs[:, 1:5]  # Next 4 outputs
        
        # Use numba-accelerated selection
        return self._apply_softmax_selection_numba(
            presence_outputs, material_logits, self.shape
        )
    
    def to_phenotype(self):
        """Convert to robot using standard robot creation"""
        from src.physics.robot import VoxelRobot  # Use your existing robot
        return VoxelRobot(self.voxels)
    
    def mutate(self, mutation_rate=0.1):
        """Optimized mutation"""
        # Mutate CPPN (this is already efficient)
        self.cppn.mutate(mutation_rate)
        
        # Quick regeneration with caching
        old_pattern = self.voxels.copy()
        self.randomize()
        
        # Track changes
        changes = np.sum(old_pattern != self.voxels)
        change_percentage = changes / np.prod(self.shape) * 100
        if change_percentage > 0:
            print(f"Mutation changed {change_percentage:.1f}% of voxels")
    
    def crossover(self, other):
        """Optimized crossover"""
        child1 = OptimizedDirectVoxelGenome(self.shape, init_random=False)
        child2 = OptimizedDirectVoxelGenome(self.shape, init_random=False)
        
        # Fast CPPN crossover
        child1.cppn, child2.cppn = self.cppn.crossover(other.cppn)
        
        # Parallel regeneration
        child1.randomize()
        child2.randomize()
        
        return child1, child2
    
    def copy(self):
        """Fast copy"""
        new_genome = OptimizedDirectVoxelGenome(self.shape, init_random=False)
        new_genome.cppn = self.cppn.copy()
        new_genome.voxels = self.voxels.copy()
        return new_genome

# Backward compatibility aliases
DirectVoxelGenome = OptimizedDirectVoxelGenome
CPPNGenome = OptimizedCPPNGenome