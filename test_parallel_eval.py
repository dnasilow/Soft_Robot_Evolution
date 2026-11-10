"""Quick smoke test for parallel evaluation."""
import time
from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
from src.evolution.genome_config import create_connected_genome

if __name__ == "__main__":
    print("Creating 8 robots...")
    genomes = [create_connected_genome() for _ in range(8)]

    print("Testing sequential (n_workers=1)...")
    t0 = time.perf_counter()
    ev1 = MuJoCoTendonEvaluator(simulation_time=2.0, settle_time=0.3, n_workers=1)
    fits_seq = ev1.evaluate_batch(genomes)
    t_seq = time.perf_counter() - t0
    print(f"  Sequential: {[f'{f:.4f}' for f in fits_seq]}")
    print(f"  Time: {t_seq:.1f}s")

    print("\nTesting parallel (n_workers=4)...")
    t0 = time.perf_counter()
    ev4 = MuJoCoTendonEvaluator(simulation_time=2.0, settle_time=0.3, n_workers=4)
    fits_par = ev4.evaluate_batch(genomes)
    t_par = time.perf_counter() - t0
    print(f"  Parallel:   {[f'{f:.4f}' for f in fits_par]}")
    print(f"  Time: {t_par:.1f}s")

    print(f"\nSpeedup: {t_seq/t_par:.1f}x")
    print("PASS" if len(fits_par) == 8 else "FAIL")
