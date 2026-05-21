import numpy as np
from typing import List, Dict, Callable
import pickle
from tqdm import tqdm
import os
import copy
from src.physics.mujoco_tendon_converter import count_active_tendons

class Individual:
    """Container for genome and fitness"""
    def __init__(self, genome, controller=None):
        self.genome = genome
        self.controller = controller
        self.fitness = -np.inf
        self.objectives = {}
        self.age = 0
        self.lineage_id = None
        self.needs_evaluation = True  # NEW: Track if individual needs evaluation
    
    def copy(self):
        """Create a deep copy of the individual"""
        new_individual = Individual(
            genome=self.genome.copy() if hasattr(self.genome, 'copy') else copy.deepcopy(self.genome),
            controller=self.controller.copy() if self.controller and hasattr(self.controller, 'copy') else copy.deepcopy(self.controller)
        )
        new_individual.fitness = self.fitness
        new_individual.objectives = self.objectives.copy()
        new_individual.age = self.age
        new_individual.lineage_id = self.lineage_id
        new_individual.needs_evaluation = False  # Copied individuals don't need re-evaluation
        return new_individual

class EvolutionaryAlgorithm:
    """Base evolutionary algorithm with GPU batch evaluation and PROPER elitism"""
    
    def __init__(self, 
                 population_size: int,
                 genome_class,
                 controller_class,
                 evaluator,
                 selection_method: str = 'tournament'):
        
        self.population_size = population_size
        self.genome_class = genome_class
        self.controller_class = controller_class
        self.evaluator = evaluator
        self.selection_method = selection_method
        
        # Evolution parameters
        self.mutation_rate = 0.1
        self.crossover_rate = 0.5
        self.elitism_size = max(2, population_size // 10)
        
        # Tracking
        self.generation = 0
        self.population = []
        self.best_individual = None
        self.history = {
            'best_fitness': [],
            'mean_fitness': [],
            'diversity': []
        }
        
        # Initialize population
        self._initialize_population()
    
    def _initialize_population(self):
        """Create initial population"""
        print(f"Initializing population of {self.population_size} individuals...")
        
        for i in range(self.population_size):
            # Create genome
            if hasattr(self.genome_class, 'shape'):
                genome = self.genome_class()
            else:
                genome = self.genome_class((10, 10, 10))
            
            # Create controller — sized from tendon count, not old robot.springs
            if hasattr(genome, 'voxels'):
                num_actuators = count_active_tendons(genome.voxels)
            else:
                num_actuators = 0
            controller = self.controller_class(num_actuators) if num_actuators > 0 else None
            
            # Create individual
            individual = Individual(genome, controller)
            individual.lineage_id = i
            individual.needs_evaluation = True  # New individuals need evaluation
            self.population.append(individual)
    
    def evaluate_population(self):
        """Evaluate entire population (used only for generation 0)"""
        print(f"Generation {self.generation}: Evaluating entire population...")
        
        # Prepare batch data — pass raw voxel grids, not VoxelRobot objects
        genomes = []
        controllers = []

        for individual in self.population:
            voxels = individual.genome.voxels if hasattr(individual.genome, 'voxels') else None
            genomes.append(voxels)

            # Lazily create controller if missing or wrong size
            if voxels is not None:
                num_active = count_active_tendons(voxels)
                if num_active > 0 and (
                    individual.controller is None or
                    individual.controller.num_actuators != num_active
                ):
                    individual.controller = self.controller_class(num_active)
            controllers.append(individual.controller)

        # Batch evaluation
        fitness_scores = self.evaluator.evaluate_batch(genomes, controllers)
        
        # Update fitness values
        for i, fitness in enumerate(fitness_scores):
            # Diversity bonus scaled down (0.05 not 0.5) so it nudges but
            # never dominates selection pressure over real locomotion fitness.
            diversity_bonus = self._calculate_individual_diversity(self.population[i]) * 0.05
            self.population[i].fitness = fitness + diversity_bonus
            self.population[i].age += 1
            self.population[i].needs_evaluation = False  # Mark as evaluated

            # Debug info
            self.population[i].base_fitness = fitness
            self.population[i].diversity_bonus = diversity_bonus
        
        # Set best individual for first time
        best_idx = np.argmax(fitness_scores)
        self.best_individual = self.population[best_idx].copy()
        print(f"Initial best fitness: {fitness_scores[best_idx]:.4f}")

    def evaluate_new_population(self):
        """Only evaluate individuals that need evaluation (not elite)"""
        
        # Find individuals that need evaluation
        needs_eval_indices = []
        robots_to_evaluate = []
        controllers_to_evaluate = []
        
        for i, individual in enumerate(self.population):
            if individual.needs_evaluation:
                needs_eval_indices.append(i)
                voxels = individual.genome.voxels if hasattr(individual.genome, 'voxels') else None
                robots_to_evaluate.append(voxels)

                # Lazily create/fix controller
                if voxels is not None:
                    num_active = count_active_tendons(voxels)
                    if num_active > 0 and (
                        individual.controller is None or
                        individual.controller.num_actuators != num_active
                    ):
                        individual.controller = self.controller_class(num_active)
                controllers_to_evaluate.append(individual.controller)
        
        if len(robots_to_evaluate) > 0:
            num_elite = self.population_size - len(robots_to_evaluate)
            print(f"Evaluating {len(robots_to_evaluate)} new individuals (keeping {num_elite} elite)")

            # Batch evaluation of only new individuals (voxel grids + controllers)
            fitness_scores = self.evaluator.evaluate_batch(robots_to_evaluate, controllers_to_evaluate)
            
            # Update fitness values for evaluated individuals only
            for idx_pos, fitness in enumerate(fitness_scores):
                pop_idx = needs_eval_indices[idx_pos]
                diversity_bonus = self._calculate_individual_diversity(self.population[pop_idx]) * 0.5
                self.population[pop_idx].fitness = fitness + diversity_bonus
                self.population[pop_idx].age += 1
                self.population[pop_idx].needs_evaluation = False
                
                # Debug info
                self.population[pop_idx].base_fitness = fitness
                self.population[pop_idx].diversity_bonus = diversity_bonus
        else:
            print("No new individuals to evaluate (all are elite)")
    
    def select_parents(self, num_parents):
        """Select parents for reproduction"""
        if self.selection_method == 'tournament':
            return self._tournament_selection(num_parents)
        elif self.selection_method == 'roulette':
            return self._roulette_selection(num_parents)
        else:
            raise ValueError(f"Unknown selection method: {self.selection_method}")
    
    def _tournament_selection(self, num_parents, tournament_size=3):
        """Tournament selection"""
        tournament_size = min(tournament_size, len(self.population))
        parents = []
        
        for _ in range(num_parents):
            # Random tournament
            tournament = np.random.choice(self.population, tournament_size, replace=False)
            winner = max(tournament, key=lambda x: x.fitness)
            parents.append(winner)
        
        return parents
    
    def _roulette_selection(self, num_parents):
        """Fitness-proportionate selection"""
        fitness_values = np.array([ind.fitness for ind in self.population])

        # FIXED: Handle edge cases robustly
        if np.all(fitness_values == fitness_values[0]):
            # All equal fitness - random selection
            indices = np.random.choice(len(self.population), num_parents, replace=True)
            return [self.population[i] for i in indices]

        # Shift fitness to positive range (use maximum to ensure non-negative)
        min_fitness = np.min(fitness_values)
        shifted_fitness = np.maximum(fitness_values - min_fitness, 0.0) + 1e-6

        # Calculate probabilities
        probabilities = shifted_fitness / np.sum(shifted_fitness)

        # Select parents
        parents = np.random.choice(self.population, num_parents, p=probabilities)
        return list(parents)
    
    def reproduce(self, parents):
        """Create offspring from parents"""
        offspring = []

        # FIXED: Ensure even number of parents for pairing
        # If odd number, duplicate a random parent to make even
        if len(parents) % 2 == 1:
            parents = list(parents)
            parents.append(parents[np.random.randint(len(parents))].copy())

        for i in range(0, len(parents) - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1]
            
            # Crossover
            if np.random.random() < self.crossover_rate:
                child1_genome, child2_genome = parent1.genome.crossover(parent2.genome)
                
                # Also crossover controllers if applicable
                if parent1.controller and parent2.controller:
                    child1_controller = parent1.controller.copy()
                    child2_controller = parent2.controller.copy()
                    # Simple weight averaging for neural controllers
                    if hasattr(child1_controller, 'blend_weight'):
                        child1_controller.blend_weight = (
                            parent1.controller.blend_weight + parent2.controller.blend_weight
                        ) / 2
                else:
                    child1_controller = parent1.controller.copy() if parent1.controller else None
                    child2_controller = parent2.controller.copy() if parent2.controller else None
            else:
                child1_genome = parent1.genome.copy()
                child2_genome = parent2.genome.copy()
                child1_controller = parent1.controller.copy() if parent1.controller else None
                child2_controller = parent2.controller.copy() if parent2.controller else None
            
            # Mutation
            child1_genome.mutate(self.mutation_rate)
            child2_genome.mutate(self.mutation_rate)
            
            if child1_controller:
                child1_controller.mutate(self.mutation_rate)
            if child2_controller:
                child2_controller.mutate(self.mutation_rate)
            
            # Create individuals
            child1 = Individual(child1_genome, child1_controller)
            child2 = Individual(child2_genome, child2_controller)
            
            # Track lineage and mark for evaluation
            child1.lineage_id = parent1.lineage_id
            child2.lineage_id = parent2.lineage_id
            child1.needs_evaluation = True
            child2.needs_evaluation = True
            
            offspring.extend([child1, child2])
        
        return offspring
    
    def step(self):
        """Single evolution step with PROPER elitism"""
        
        # Evaluate population
        if self.generation == 0:
            # First generation - evaluate everyone
            self.evaluate_population()
        else:
            # Subsequent generations - only evaluate new individuals
            self.evaluate_new_population()
        
        # Sort by fitness
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Record statistics
        fitness_values = [ind.fitness for ind in self.population]
        self.history['best_fitness'].append(max(fitness_values))
        self.history['mean_fitness'].append(np.mean(fitness_values))
        self.history['diversity'].append(self._calculate_diversity())
        
        # Update best individual (should never get worse with proper elitism!)
        current_best = self.population[0]
        if self.best_individual is None or current_best.fitness > self.best_individual.fitness:
            self.best_individual = current_best.copy()
            print(f"NEW BEST FITNESS: {current_best.fitness:.4f} (improvement: +{current_best.fitness - (self.history['best_fitness'][-2] if len(self.history['best_fitness']) > 1 else 0):.4f})")
        else:
            print(f"Best fitness maintained: {self.best_individual.fitness:.4f}")
        
        # Create new population with PROPER elitism
        new_population = []
        
        # ELITISM: Keep exact copies of best individuals (DO NOT RE-EVALUATE!)
        elite_individuals = []
        for i in range(self.elitism_size):
            elite_copy = self.population[i].copy()
            elite_copy.needs_evaluation = False  # CRITICAL: Elite don't need re-evaluation
            elite_individuals.append(elite_copy)
        
        new_population.extend(elite_individuals)
        
        # Debug: Print elite fitness values
        elite_fitness = [ind.fitness for ind in elite_individuals]
        print(f"Generation {self.generation}: Elite preserved (fitness: {elite_fitness[:3]}...)")
        
        # Fill rest with offspring
        num_offspring = self.population_size - self.elitism_size
        parents = self.select_parents(num_offspring)
        offspring = self.reproduce(parents)
        new_population.extend(offspring[:num_offspring])
        
        self.population = new_population
        self.generation += 1
    
    def _calculate_diversity(self):
        """Calculate population diversity"""
        # Simple diversity measure based on genome differences
        if len(self.population) < 2:
            return 0.0
        
        # Sample pairs and calculate average distance
        num_samples = min(100, len(self.population) * (len(self.population) - 1) // 2)
        total_distance = 0
        
        for _ in range(num_samples):
            ind1, ind2 = np.random.choice(self.population, 2, replace=False)
            
            # Calculate genome distance
            if hasattr(ind1.genome, 'voxels'):
                # Direct encoding
                distance = np.mean(ind1.genome.voxels != ind2.genome.voxels)
            else:
                # CPPN encoding - compare number of connections
                distance = abs(len(ind1.genome.connections) - len(ind2.genome.connections)) / 100
            
            total_distance += distance
        
        return total_distance / num_samples
    
    def _calculate_individual_diversity(self, individual):
        """Calculate diversity bonus for this individual"""
        if len(self.population) < 2:
            return 0.0
        
        # Compare to a few random other individuals
        total_distance = 0
        num_comparisons = min(5, len(self.population) - 1)
        
        others = [ind for ind in self.population if ind != individual]
        if len(others) == 0:
            return 0.0
        
        selected_others = np.random.choice(others, min(num_comparisons, len(others)), replace=False)
        
        for other in selected_others:
            if hasattr(individual.genome, 'voxels'):
                distance = np.mean(individual.genome.voxels != other.genome.voxels)
            else:
                distance = abs(len(individual.genome.connections) - len(other.genome.connections)) / 100
            total_distance += distance
        
        return total_distance / len(selected_others)
    
    def save_checkpoint(self, directory):
        """Save evolution state"""
        os.makedirs(directory, exist_ok=True)
        
        checkpoint = {
            'generation': self.generation,
            'population': self.population,
            'best_individual': self.best_individual,
            'history': self.history,
            'parameters': {
                'population_size': self.population_size,
                'mutation_rate': self.mutation_rate,
                'crossover_rate': self.crossover_rate,
                'elitism_size': self.elitism_size
            }
        }
        
        filepath = os.path.join(directory, f'checkpoint_gen_{self.generation}.pkl')
        with open(filepath, 'wb') as f:
            pickle.dump(checkpoint, f)
        
        print(f"Saved checkpoint to {filepath}")
    
    def load_checkpoint(self, filepath):
        """Load evolution state"""
        with open(filepath, 'rb') as f:
            checkpoint = pickle.load(f)
        
        self.generation = checkpoint['generation']
        self.population = checkpoint['population']
        self.best_individual = checkpoint['best_individual']
        self.history = checkpoint['history']
        
        # Restore parameters
        params = checkpoint['parameters']
        self.population_size = params['population_size']
        self.mutation_rate = params['mutation_rate']
        self.crossover_rate = params['crossover_rate']
        self.elitism_size = params['elitism_size']
        
        print(f"Loaded checkpoint from generation {self.generation}")