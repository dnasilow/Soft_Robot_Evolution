"""Quick physics test at new 16x16x16 grid size."""
from src.evolution.genome_config import create_connected_genome
from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator

if __name__ == "__main__":
    genomes = [create_connected_genome() for _ in range(3)]
    sizes = [int((g != 0).sum()) for g in genomes]
    print(f"Robot sizes: {sizes} voxels")

    ev = MuJoCoTendonEvaluator(simulation_time=2.0, settle_time=0.3, n_workers=1)
    fits = ev.evaluate_batch(genomes)
    print(f"Fitnesses: {[f'{f:.4f}' for f in fits]}")
    print("Physics OK")
