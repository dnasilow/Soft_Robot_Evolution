import numpy as np
import torch
import torch.nn as nn

class CPGController:
    """Central Pattern Generator controller for locomotion"""
    
    def __init__(self, num_actuators):
        self.num_actuators = num_actuators
        
        # CPG parameters (evolvable) - BETTER DEFAULTS
        self.frequencies = np.random.uniform(1.0, 3.0, num_actuators)  # Faster oscillation
        self.amplitudes = np.ones(num_actuators) * 0.8  # Strong amplitude
        self.phases = np.random.uniform(0, 2*np.pi, num_actuators)
        
        # Coupling weights between oscillators
        self.coupling = np.random.randn(num_actuators, num_actuators) * 0.1
        np.fill_diagonal(self.coupling, 0)
        
        self.time = 0.0
        self.states = np.zeros(num_actuators)
    
    def step(self, dt, sensor_data=None):
        """Generate control signals"""
        # Base oscillation
        base_signal = self.amplitudes * np.sin(
            2 * np.pi * self.frequencies * self.time + self.phases
        )
        
        # Coupling influence
        coupling_influence = np.dot(self.coupling, self.states)
        
        # Update states
        self.states = base_signal + 0.1 * coupling_influence
        
        # Clip to valid range
        control_signals = np.clip(self.states, -1.0, 1.0)
        
        self.time += dt
        return control_signals
    
    def mutate(self, mutation_rate=0.1):
        """Mutate CPG parameters"""
        # Frequency mutations
        mask = np.random.random(self.num_actuators) < mutation_rate
        self.frequencies[mask] += np.random.normal(0, 0.1, np.sum(mask))
        self.frequencies = np.clip(self.frequencies, 0.1, 5.0)
        
        # Amplitude mutations
        mask = np.random.random(self.num_actuators) < mutation_rate
        self.amplitudes[mask] += np.random.normal(0, 0.1, np.sum(mask))
        self.amplitudes = np.clip(self.amplitudes, 0.0, 1.0)
        
        # Phase mutations
        mask = np.random.random(self.num_actuators) < mutation_rate
        self.phases[mask] += np.random.normal(0, 0.5, np.sum(mask))
        self.phases = np.mod(self.phases, 2*np.pi)
        
        # Coupling mutations
        mask = np.random.random(self.coupling.shape) < mutation_rate * 0.5
        self.coupling[mask] += np.random.normal(0, 0.05, np.sum(mask))
        self.coupling = np.clip(self.coupling, -0.5, 0.5)
        np.fill_diagonal(self.coupling, 0)
    
    def copy(self):
        """Create copy of controller"""
        new_controller = CPGController(self.num_actuators)
        new_controller.frequencies = self.frequencies.copy()
        new_controller.amplitudes = self.amplitudes.copy()
        new_controller.phases = self.phases.copy()
        new_controller.coupling = self.coupling.copy()
        return new_controller

class NeuralController(nn.Module):
    """Neural network controller with sensory feedback"""
    
    def __init__(self, num_actuators, num_sensors=12, hidden_size=64):
        super().__init__()
        self.num_actuators = num_actuators
        
        # Network architecture
        self.network = nn.Sequential(
            nn.Linear(num_sensors + num_actuators, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_actuators),
            nn.Tanh()
        )
        
        # Recurrent state
        self.hidden_state = torch.zeros(num_actuators)
        
        # Initialize weights
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, sensor_data):
        """Forward pass"""
        # Combine sensor data with previous actuator state
        combined_input = torch.cat([
            torch.tensor(sensor_data, dtype=torch.float32),
            self.hidden_state
        ])
        
        # Network forward pass
        output = self.network(combined_input)
        
        # Update hidden state
        self.hidden_state = output.detach()
        
        return output.numpy()
    
    def mutate(self, mutation_rate=0.1):
        """Mutate network weights"""
        with torch.no_grad():
            for param in self.parameters():
                mask = torch.rand_like(param) < mutation_rate
                param[mask] += torch.randn_like(param[mask]) * 0.1
    
    def copy(self):
        """Create copy of controller"""
        new_controller = NeuralController(
            self.num_actuators, 
            num_sensors=12,
            hidden_size=64
        )
        new_controller.load_state_dict(self.state_dict())
        return new_controller

class HybridController:
    """Hybrid CPG + Neural Network controller"""
    
    def __init__(self, num_actuators):
        self.num_actuators = num_actuators
        self.cpg = CPGController(num_actuators)
        self.neural = NeuralController(num_actuators)
        self.blend_weight = 0.7  # How much CPG vs neural
    
    def step(self, dt, sensor_data):
        """Generate control signals"""
        # Get CPG signal
        cpg_signal = self.cpg.step(dt, sensor_data)
        
        # Get neural signal
        neural_signal = self.neural.forward(sensor_data)
        
        # Blend signals
        control_signal = (self.blend_weight * cpg_signal + 
                         (1 - self.blend_weight) * neural_signal)
        
        return np.clip(control_signal, -1.0, 1.0)
    
    def mutate(self, mutation_rate=0.1):
        """Mutate both components"""
        self.cpg.mutate(mutation_rate)
        self.neural.mutate(mutation_rate)
        
        # Mutate blend weight
        if np.random.random() < mutation_rate:
            self.blend_weight += np.random.normal(0, 0.1)
            self.blend_weight = np.clip(self.blend_weight, 0.0, 1.0)
    
    def copy(self):
        """Create copy"""
        new_controller = HybridController(self.num_actuators)
        new_controller.cpg = self.cpg.copy()
        new_controller.neural = self.neural.copy()
        new_controller.blend_weight = self.blend_weight
        return new_controller