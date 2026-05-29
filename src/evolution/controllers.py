import numpy as np


class CPGController:
    """Central Pattern Generator controller for locomotion.

    One oscillator per active tendon. Pure numpy — no torch dependency.
    """

    def __init__(self, num_actuators: int):
        self.num_actuators = num_actuators

        # Evolvable parameters
        self.frequencies = np.random.uniform(1.0, 3.0, num_actuators)
        self.amplitudes  = np.ones(num_actuators) * 0.8
        self.phases      = np.random.uniform(0, 2 * np.pi, num_actuators)

        # Coupling weights between oscillators
        self.coupling = np.random.randn(num_actuators, num_actuators) * 0.1
        np.fill_diagonal(self.coupling, 0)

        self.time   = 0.0
        self.states = np.zeros(num_actuators)

    def step(self, dt, sensor_data=None) -> np.ndarray:
        """Return control signals in [-1, 1], one per actuator."""
        base = self.amplitudes * np.sin(
            2 * np.pi * self.frequencies * self.time + self.phases
        )
        self.states = base + 0.1 * np.dot(self.coupling, self.states)
        self.time  += dt
        return np.clip(self.states, -1.0, 1.0)

    def mutate(self, mutation_rate: float = 0.1):
        mask = np.random.random(self.num_actuators) < mutation_rate
        self.frequencies[mask] += np.random.normal(0, 0.1, mask.sum())
        self.frequencies = np.clip(self.frequencies, 0.1, 5.0)

        mask = np.random.random(self.num_actuators) < mutation_rate
        self.amplitudes[mask] += np.random.normal(0, 0.1, mask.sum())
        self.amplitudes = np.clip(self.amplitudes, 0.0, 1.0)

        mask = np.random.random(self.num_actuators) < mutation_rate
        self.phases[mask] += np.random.normal(0, 0.5, mask.sum())
        self.phases = np.mod(self.phases, 2 * np.pi)

        mask = np.random.random(self.coupling.shape) < mutation_rate * 0.5
        self.coupling[mask] += np.random.normal(0, 0.05, mask.sum())
        self.coupling = np.clip(self.coupling, -0.5, 0.5)
        np.fill_diagonal(self.coupling, 0)

    def copy(self) -> "CPGController":
        c = CPGController(self.num_actuators)
        c.frequencies = self.frequencies.copy()
        c.amplitudes  = self.amplitudes.copy()
        c.phases      = self.phases.copy()
        c.coupling    = self.coupling.copy()
        c.time        = self.time
        c.states      = self.states.copy()
        return c
