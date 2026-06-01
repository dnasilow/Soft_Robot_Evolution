"""
Tendon-Based Soft Robot Evolution
==================================
Canonical entry point for evolving soft robots using the MuJoCo tendon physics.

Genome: direct voxel grid (8x8x8, materials 0-4)
Physics: MuJoCoTendonPhysics (spatial tendons + position actuators)
Controller: CPGController per robot (one oscillator per active tendon)
Fitness: horizontal distance travelled in simulation_time after settling

Usage
-----
  # Quick test (sanity-check first, then 5 generations):
  python run_tendon_evolution.py

  # Custom run:
  python run_tendon_evolution.py --pop 20 --gen 50 --sim-time 5 --name my_run
"""
import argparse
import copy
import json
import pickle
import time
from pathlib import Path

import numpy as np

from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
from src.evolution.controllers import CPGController
from src.physics.mujoco_tendon_converter import count_active_tendons
from src.evolution.genome_config import (
    VOXEL_GRID_SHAPE, VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX,
    MATERIAL_TYPES, MATERIAL_PROBABILITIES,
    create_empty_grid, get_random_interior_position, get_num_voxels,
)

# ──────────────────────────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────────────────────────
DEFAULT_POP         = 10
DEFAULT_GEN         = 20
DEFAULT_SIM_TIME    = 3.0    # seconds per evaluation (after settling)
DEFAULT_SETTLE_TIME = 0.5    # seconds settling before measuring
DEFAULT_ELITE       = 2
DEFAULT_MUT_RATE    = 0.3
DEFAULT_XOVER_RATE  = 0.7
DEFAULT_FREQ        = 10.0   # Hz
DEFAULT_AMP         = 0.08   # ±8% rest length (matches material test scripts)


# ──────────────────────────────────────────────────────────────────
# Genome helpers
# ──────────────────────────────────────────────────────────────────
def create_random_genome() -> np.ndarray:
    """Random voxel grid with 10–30 voxels placed in the interior."""
    grid = create_empty_grid()
    for _ in range(get_num_voxels()):
        x, y, z = get_random_interior_position()
        grid[x, y, z] = np.random.choice(MATERIAL_TYPES, p=MATERIAL_PROBABILITIES)
    return grid


def mutate(grid: np.ndarray, rate: float = DEFAULT_MUT_RATE) -> np.ndarray:
    """Randomly add/remove/change voxels."""
    g = grid.copy()
    if np.random.random() < rate:
        n_muts = np.random.randint(1, 5)
        for _ in range(n_muts):
            if np.random.random() < 0.5:
                x, y, z = get_random_interior_position()
                g[x, y, z] = np.random.choice(MATERIAL_TYPES, p=MATERIAL_PROBABILITIES)
            else:
                occupied = np.argwhere(g != 0)
                if len(occupied) > 2:
                    idx = occupied[np.random.randint(len(occupied))]
                    g[tuple(idx)] = 0
    return g


def crossover_3d(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Planar split crossover along a random axis."""
    child = np.zeros_like(p1)
    axis  = np.random.randint(0, 3)
    split = np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX)
    for x in range(p1.shape[0]):
        for y in range(p1.shape[1]):
            for z in range(p1.shape[2]):
                coord = [x, y, z][axis]
                child[x, y, z] = p1[x, y, z] if coord < split else p2[x, y, z]
    if np.sum(child != 0) < 3:
        child = p1.copy()
    return child


# ──────────────────────────────────────────────────────────────────
# Controller helpers
# ──────────────────────────────────────────────────────────────────
def make_controller(genome: np.ndarray) -> CPGController | None:
    """Create CPGController sized for this genome's active tendons."""
    n = count_active_tendons(genome)
    return CPGController(n) if n > 0 else None


def mutate_controller(ctrl: CPGController | None,
                      rate: float = DEFAULT_MUT_RATE) -> CPGController | None:
    if ctrl is None:
        return None
    c = copy.deepcopy(ctrl)
    c.mutate(rate)
    return c


def crossover_controller(c1: CPGController | None,
                         c2: CPGController | None,
                         n_active: int) -> CPGController | None:
    """
    Produce a child controller.  If parents match size, blend phases;
    otherwise make a fresh one for the child's genome.
    """
    if n_active == 0:
        return None
    if c1 is None or c2 is None or c1.num_actuators != n_active or c2.num_actuators != n_active:
        return CPGController(n_active)
    child = copy.deepcopy(c1)
    # Blend phases from both parents
    child.phases    = (c1.phases    + c2.phases)    / 2
    child.frequencies = (c1.frequencies + c2.frequencies) / 2
    return child


# ──────────────────────────────────────────────────────────────────
# Main evolution loop
# ──────────────────────────────────────────────────────────────────
def run_evolution(
    population_size: int  = DEFAULT_POP,
    generations:     int  = DEFAULT_GEN,
    sim_time:        float = DEFAULT_SIM_TIME,
    settle_time:     float = DEFAULT_SETTLE_TIME,
    elite_size:      int  = DEFAULT_ELITE,
    mutation_rate:   float = DEFAULT_MUT_RATE,
    crossover_rate:  float = DEFAULT_XOVER_RATE,
    actuation_freq:  float = DEFAULT_FREQ,
    actuation_amp:   float = DEFAULT_AMP,
    results_dir:     str  = "results",
    name:            str  = "tendon_run",
    seed:            int  = 42,
):
    np.random.seed(seed)
    out = Path(results_dir) / name
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("TENDON-BASED SOFT ROBOT EVOLUTION")
    print("=" * 70)
    print(f"  Population : {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Sim time   : {sim_time}s  +  {settle_time}s settle")
    print(f"  Actuation  : {actuation_freq}Hz  +-{actuation_amp*100:.0f}%")
    print(f"  Elite      : {elite_size}")
    print(f"  Output dir : {out}")
    print("=" * 70)

    # ── Evaluator (one engine, reused) ──────────────────────────────
    evaluator = MuJoCoTendonEvaluator(
        simulation_time     = sim_time,
        settle_time         = settle_time,
        actuation_frequency = actuation_freq,
        actuation_amplitude = actuation_amp,
    )

    # ── Sanity check (1 robot, catch import/physics errors early) ──
    print("\nRunning sanity check (1 robot)...")
    test_genome = create_random_genome()
    try:
        test_fit = evaluator.evaluate_single(test_genome)
        print(f"  Sanity check passed — fitness={test_fit:.4f}m")
    except Exception as e:
        print(f"  SANITY CHECK FAILED: {e}")
        raise

    # ── Initial population ──────────────────────────────────────────
    print(f"\nGenerating {population_size} random robots...")
    genomes     = [create_random_genome()   for _ in range(population_size)]
    controllers = [make_controller(g)       for g in genomes]

    history = {
        'best_fitness':  [],
        'mean_fitness':  [],
        'worst_fitness': [],
    }
    best_genome     = None
    best_controller = None
    best_fitness    = -np.inf

    # ── Evolution loop ──────────────────────────────────────────────
    for gen in range(generations):
        t_start = time.perf_counter()

        fitnesses = evaluator.evaluate_batch(genomes, controllers)

        # Track statistics
        best_idx = int(np.argmax(fitnesses))
        gen_best = float(fitnesses[best_idx])
        gen_mean = float(np.mean(fitnesses))
        gen_wst  = float(np.min(fitnesses))

        history['best_fitness'].append(gen_best)
        history['mean_fitness'].append(gen_mean)
        history['worst_fitness'].append(gen_wst)

        if gen_best > best_fitness:
            best_fitness    = gen_best
            best_genome     = genomes[best_idx].copy()
            best_controller = copy.deepcopy(controllers[best_idx])

        elapsed = time.perf_counter() - t_start
        print(f"Gen {gen+1:3d}/{generations}  "
              f"best={gen_best:.4f}m  mean={gen_mean:.4f}m  "
              f"worst={gen_wst:.4f}m  [{elapsed:.1f}s]")

        # Save per-generation JSON
        with open(out / f"gen_{gen+1:03d}.json", "w") as f:
            json.dump({
                'generation': gen + 1,
                'best_fitness': gen_best,
                'mean_fitness': gen_mean,
                'worst_fitness': gen_wst,
                'fitnesses': fitnesses.tolist(),
                'time_s': elapsed,
            }, f)

        if gen == generations - 1:
            break  # Don't breed after last generation

        # ── Selection + reproduction ────────────────────────────────
        order = np.argsort(fitnesses)[::-1]

        new_genomes     = [genomes[i].copy()          for i in order[:elite_size]]
        new_controllers = [copy.deepcopy(controllers[i]) for i in order[:elite_size]]

        # Tournament selection to fill the rest
        while len(new_genomes) < population_size:
            # Pick 2 parents via tournament-3
            def tournament():
                cands = np.random.choice(population_size, 3, replace=False)
                return int(cands[np.argmax(fitnesses[cands])])

            p1_i, p2_i = tournament(), tournament()
            p1_g, p2_g = genomes[p1_i], genomes[p2_i]
            p1_c, p2_c = controllers[p1_i], controllers[p2_i]

            if np.random.random() < crossover_rate:
                child_g = crossover_3d(p1_g, p2_g)
            else:
                child_g = p1_g.copy()

            child_g = mutate(child_g, mutation_rate)
            n_active = count_active_tendons(child_g)
            child_c = crossover_controller(p1_c, p2_c, n_active)
            child_c = mutate_controller(child_c, mutation_rate)

            new_genomes.append(child_g)
            new_controllers.append(child_c)

        genomes     = new_genomes
        controllers = new_controllers

    # ── Save results ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"EVOLUTION COMPLETE — best fitness: {best_fitness:.4f}m")
    print("=" * 70)

    with open(out / 'best_robot.pkl', 'wb') as f:
        pickle.dump({'genome': best_genome, 'controller': best_controller,
                     'fitness': best_fitness}, f)
    # Also write to root for easy access
    with open('best_robot_tendon.pkl', 'wb') as f:
        pickle.dump({'genome': best_genome, 'controller': best_controller,
                     'fitness': best_fitness}, f)

    with open(out / 'history.json', 'w') as f:
        json.dump(history, f, indent=2)

    print(f"\nFiles saved:")
    print(f"  {out/'best_robot.pkl'}")
    print(f"  best_robot_tendon.pkl  (root, for quick access)")
    print(f"  {out/'history.json'}")
    print(f"\nVisualize best robot:")
    print(f"  python test_tendon_material_1.py  (or write a visualize_tendon_best.py)")
    return best_genome, best_controller, best_fitness, history


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tendon-based soft robot evolution")
    parser.add_argument("--pop",       type=int,   default=DEFAULT_POP)
    parser.add_argument("--gen",       type=int,   default=DEFAULT_GEN)
    parser.add_argument("--sim-time",  type=float, default=DEFAULT_SIM_TIME)
    parser.add_argument("--settle",    type=float, default=DEFAULT_SETTLE_TIME)
    parser.add_argument("--elite",     type=int,   default=DEFAULT_ELITE)
    parser.add_argument("--mut",       type=float, default=DEFAULT_MUT_RATE)
    parser.add_argument("--xover",     type=float, default=DEFAULT_XOVER_RATE)
    parser.add_argument("--freq",      type=float, default=DEFAULT_FREQ)
    parser.add_argument("--amp",       type=float, default=DEFAULT_AMP)
    parser.add_argument("--name",      type=str,   default="tendon_run")
    parser.add_argument("--seed",      type=int,   default=42)
    args = parser.parse_args()

    run_evolution(
        population_size = args.pop,
        generations     = args.gen,
        sim_time        = args.sim_time,
        settle_time     = args.settle,
        elite_size      = args.elite,
        mutation_rate   = args.mut,
        crossover_rate  = args.xover,
        actuation_freq  = args.freq,
        actuation_amp   = args.amp,
        name            = args.name,
        seed            = args.seed,
    )
