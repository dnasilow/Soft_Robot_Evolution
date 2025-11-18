import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
import numpy as np
from collections import deque

class EvolutionProgressMonitor:
    """Simple evolution progress visualization without threading"""
    
    def __init__(self, save_plots=True):
        self.save_plots = save_plots
        
        # Data storage
        self.generation_history = []
        self.best_fitness_history = []
        self.mean_fitness_history = []
        self.diversity_history = []
        
        # Don't create figure immediately - will create on demand
        self.fig = None
        
    def update(self, generation, best_fitness, mean_fitness, diversity, best_robot=None):
        """Store update data"""
        self.generation_history.append(generation)
        self.best_fitness_history.append(best_fitness)
        self.mean_fitness_history.append(mean_fitness)
        self.diversity_history.append(diversity)
        
        # Print to console for immediate feedback
        print(f"Gen {generation}: Best={best_fitness:.4f}, Mean={mean_fitness:.4f}, Diversity={diversity:.4f}")
    
    def create_summary_plot(self, output_path=None):
        """Create a summary plot after evolution completes"""
        if len(self.generation_history) == 0:
            return
            
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Soft Robot Evolution Summary', fontsize=16)
        
        # Fitness evolution
        ax = axes[0, 0]
        ax.plot(self.generation_history, self.best_fitness_history, 'b-', linewidth=2, label='Best')
        ax.plot(self.generation_history, self.mean_fitness_history, 'g--', linewidth=1, label='Mean')
        ax.set_xlabel('Generation')
        ax.set_ylabel('Fitness (BL/s)')
        ax.set_title('Fitness Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Diversity
        ax = axes[0, 1]
        ax.plot(self.generation_history, self.diversity_history, 'r-', linewidth=2)
        ax.set_xlabel('Generation')
        ax.set_ylabel('Population Diversity')
        ax.set_title('Genetic Diversity')
        ax.grid(True, alpha=0.3)
        
        # Improvement rate
        ax = axes[1, 0]
        if len(self.best_fitness_history) > 1:
            improvement = np.diff(self.best_fitness_history)
            ax.bar(self.generation_history[1:], improvement, alpha=0.7)
            ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
            ax.set_xlabel('Generation')
            ax.set_ylabel('Fitness Improvement')
            ax.set_title('Generation-to-Generation Improvement')
            ax.grid(True, alpha=0.3)
        
        # Statistics
        ax = axes[1, 1]
        ax.axis('off')
        stats_text = f"""Final Statistics:
        
Best Fitness: {self.best_fitness_history[-1]:.4f}
Mean Fitness: {self.mean_fitness_history[-1]:.4f}
Improvement: {self.best_fitness_history[-1] - self.best_fitness_history[0]:.4f}
Final Diversity: {self.diversity_history[-1]:.4f}

Total Generations: {len(self.generation_history)}
        """
        ax.text(0.1, 0.5, stats_text, transform=ax.transAxes, 
                fontsize=12, verticalalignment='center')
        
        plt.tight_layout()
        
        if output_path and self.save_plots:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Progress plot saved to: {output_path}")
        
        # Don't show in thread - just save
        plt.close()
        
        return fig
    
    def show(self):
        """This method is kept for compatibility but does nothing"""
        pass  # No longer needed - we'll save plots instead