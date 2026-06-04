"""
Tendon-Based Soft Robot Evolution
==================================
Canonical entry point for evolving soft robots using the MuJoCo tendon physics.

Genome: direct voxel grid (16x16x16, materials 0-4)
Physics: MuJoCoTendonPhysics (spatial tendons + position actuators)
Controller: CPGController per robot (one oscillator per active tendon)
Fitness: horizontal distance travelled in simulation_time after settling,
         multiplied by ground_fraction to penalise jumping.

Selection
---------
Default: Age-Fitness Pareto (Schmidt & Lipson, GECCO 2010)
  - Each individual carries an "age" (generations of genetic material).
  - Child age = max(parent1.age, parent2.age); survivors age +1 each gen.
  - n_inject fresh random robots (age=1) are added every generation.
  - Pool = current N + (N-n_inject) bred children + n_inject random (2N total).
  - Non-dominated Pareto sort on (fitness↑, age↓); keep top N.
  - Prevents premature convergence without changing the fitness landscape.
Fallback: --no-age-pareto restores the original tournament-3 + elite-2 scheme.

Usage
-----
  python run_tendon_evolution.py --pop 120 --gen 50 --sim-time 5 --workers 30
"""
import argparse
import copy
import json
import os
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
    create_connected_genome, keep_largest_component,
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
DEFAULT_WORKERS     = max(1, (os.cpu_count() or 4) - 2)   # leave 2 cores for OS
DEFAULT_INJECT_FRAC = 0.10   # fraction of pop injected as fresh random each gen


# ──────────────────────────────────────────────────────────────────
# Genome helpers
# ──────────────────────────────────────────────────────────────────
def create_random_genome() -> np.ndarray:
    """Connected voxel body via growth algorithm (guaranteed no orphan voxels)."""
    return create_connected_genome()


def mutate(grid: np.ndarray, rate: float = DEFAULT_MUT_RATE) -> np.ndarray:
    """Randomly add/remove/change voxels, then drop any orphaned clusters."""
    g = grid.copy()
    if np.random.random() < rate:
        n_muts = np.random.randint(1, 5)
        for _ in range(n_muts):
            if np.random.random() < 0.5:
                x, y, z = get_random_interior_position()
                g[x, y, z] = np.random.choice(MATERIAL_TYPES, p=MATERIAL_PROBABILITIES)
            else:
                occupied = np.argwhere(g != 0)
                if len(occupied) > 3:
                    idx = occupied[np.random.randint(len(occupied))]
                    g[tuple(idx)] = 0
    g = keep_largest_component(g)
    if np.count_nonzero(g) < 3:
        return grid.copy()
    return g


def crossover_3d(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Planar split crossover along a random axis, then drop orphan clusters."""
    child = np.zeros_like(p1)
    axis  = np.random.randint(0, 3)
    split = np.random.randint(VOXEL_INTERIOR_MIN, VOXEL_INTERIOR_MAX)
    for x in range(p1.shape[0]):
        for y in range(p1.shape[1]):
            for z in range(p1.shape[2]):
                coord = [x, y, z][axis]
                child[x, y, z] = p1[x, y, z] if coord < split else p2[x, y, z]
    child = keep_largest_component(child)
    if np.count_nonzero(child) < 3:
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
    child.phases      = (c1.phases      + c2.phases)      / 2
    child.frequencies = (c1.frequencies + c2.frequencies) / 2
    return child


# ──────────────────────────────────────────────────────────────────
# Age-Fitness Pareto selection  (Schmidt & Lipson, GECCO 2010)
# ──────────────────────────────────────────────────────────────────
def pareto_select(genomes, controllers, fitnesses, ages, target_n):
    """
    Non-dominated Pareto sort on two objectives:
      - fitness : maximise
      - age     : minimise  (younger = better)

    Individual A dominates B iff A is >= B on both objectives and
    strictly > on at least one.

    Returns (genomes, controllers, fitnesses, ages) of the top target_n
    individuals, ordered front-by-front then by fitness within the last
    partial front.
    """
    n = len(genomes)
    dom_count  = np.zeros(n, dtype=int)      # how many individuals dominate i
    dom_over   = [[] for _ in range(n)]      # indices that i dominates

    for i in range(n):
        for j in range(i + 1, n):
            fi, ai = fitnesses[i], ages[i]
            fj, aj = fitnesses[j], ages[j]
            # i dominates j?
            if fi >= fj and ai <= aj and (fi > fj or ai < aj):
                dom_count[j] += 1
                dom_over[i].append(j)
            # j dominates i?
            elif fj >= fi and aj <= ai and (fj > fi or aj < ai):
                dom_count[i] += 1
                dom_over[j].append(i)

    selected = []
    remaining_count = dom_count.copy()
    current_front   = [i for i in range(n) if remaining_count[i] == 0]

    while current_front and len(selected) < target_n:
        if len(selected) + len(current_front) <= target_n:
            selected.extend(current_front)
        else:
            # Fill remainder of this partial front by fitness (descending)
            current_front.sort(key=lambda i: fitnesses[i], reverse=True)
            need = target_n - len(selected)
            selected.extend(current_front[:need])
            break

        # Build next front
        next_front = []
        for i in current_front:
            for j in dom_over[i]:
                remaining_count[j] -= 1
                if remaining_count[j] == 0:
                    next_front.append(j)
        current_front = next_front

    return (
        [genomes[i]     for i in selected],
        [controllers[i] for i in selected],
        np.array([fitnesses[i] for i in selected], dtype=float),
        np.array([ages[i]      for i in selected], dtype=int),
    )


# ──────────────────────────────────────────────────────────────────
# Main evolution loop
# ──────────────────────────────────────────────────────────────────
def run_evolution(
    population_size: int   = DEFAULT_POP,
    generations:     int   = DEFAULT_GEN,
    sim_time:        float = DEFAULT_SIM_TIME,
    settle_time:     float = DEFAULT_SETTLE_TIME,
    elite_size:      int   = DEFAULT_ELITE,
    mutation_rate:   float = DEFAULT_MUT_RATE,
    crossover_rate:  float = DEFAULT_XOVER_RATE,
    actuation_freq:  float = DEFAULT_FREQ,
    actuation_amp:   float = DEFAULT_AMP,
    n_workers:       int   = DEFAULT_WORKERS,
    use_age_pareto:  bool  = True,
    n_inject:        int   = None,   # None → pop // 10
    results_dir:     str   = "results",
    name:            str   = "tendon_run",
    seed:            int   = 42,
):
    np.random.seed(seed)
    out = Path(results_dir) / name
    out.mkdir(parents=True, exist_ok=True)

    if n_inject is None:
        n_inject = max(1, population_size // 10)

    print("=" * 70)
    print("TENDON-BASED SOFT ROBOT EVOLUTION")
    print("=" * 70)
    print(f"  Population : {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Sim time   : {sim_time}s  +  {settle_time}s settle")
    print(f"  Actuation  : {actuation_freq}Hz  +-{actuation_amp*100:.0f}%")
    if use_age_pareto:
        print(f"  Selection  : Age-Fitness Pareto  (inject {n_inject}/gen)")
    else:
        print(f"  Selection  : Tournament-3 + Elite-{elite_size}")
    print(f"  Workers    : {n_workers}")
    print(f"  Output dir : {out}")
    print("=" * 70)

    # ── Evaluator ───────────────────────────────────────────────────
    evaluator = MuJoCoTendonEvaluator(
        simulation_time     = sim_time,
        settle_time         = settle_time,
        actuation_frequency = actuation_freq,
        actuation_amplitude = actuation_amp,
        n_workers           = n_workers,
    )

    # ── Sanity check ────────────────────────────────────────────────
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
    genomes     = [create_random_genome() for _ in range(population_size)]
    controllers = [make_controller(g)     for g in genomes]
    ages        = np.ones(population_size, dtype=int)

    print(f"Evaluating initial population...")
    t_gen_start = time.perf_counter()
    fitnesses = np.array(evaluator.evaluate_batch(genomes, controllers), dtype=float)

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
        # elapsed = time since end of previous evaluation (or initial eval)
        elapsed = time.perf_counter() - t_gen_start

        # ── Stats ──────────────────────────────────────────────────
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

        age_str   = f"  max_age={int(np.max(ages))}" if use_age_pareto else ""
        print(f"Gen {gen+1:3d}/{generations}  "
              f"best={gen_best:.4f}m  mean={gen_mean:.4f}m  "
              f"worst={gen_wst:.4f}m  [{elapsed:.1f}s]{age_str}")

        # ── Per-generation checkpoint (Ctrl+C safe after this) ─────
        with open('best_robot_tendon.pkl', 'wb') as f:
            pickle.dump({'genome': best_genome, 'controller': best_controller,
                         'fitness': best_fitness}, f)

        with open(out / f"gen_{gen+1:03d}.json", "w") as f:
            json.dump({
                'generation':    gen + 1,
                'best_fitness':  gen_best,
                'mean_fitness':  gen_mean,
                'worst_fitness': gen_wst,
                'fitnesses':     fitnesses.tolist(),
                'time_s':        elapsed,
            }, f)

        if gen == generations - 1:
            break   # don't breed after last generation

        # ── Reproduce ──────────────────────────────────────────────
        def tournament():
            cands = np.random.choice(population_size, 3, replace=False)
            return int(cands[np.argmax(fitnesses[cands])])

        if use_age_pareto:
            # ── Age-Fitness Pareto breeding ─────────────────────────
            n_breed = population_size - n_inject
            new_genomes     = []
            new_controllers = []
            new_ages        = []

            for _ in range(n_breed):
                p1_i, p2_i = tournament(), tournament()
                p1_g, p2_g = genomes[p1_i], genomes[p2_i]
                p1_c, p2_c = controllers[p1_i], controllers[p2_i]

                if np.random.random() < crossover_rate:
                    child_g = crossover_3d(p1_g, p2_g)
                else:
                    child_g = p1_g.copy()
                child_g = mutate(child_g, mutation_rate)
                n_active = count_active_tendons(child_g)
                child_c  = crossover_controller(p1_c, p2_c, n_active)
                child_c  = mutate_controller(child_c, mutation_rate)

                new_genomes.append(child_g)
                new_controllers.append(child_c)
                new_ages.append(int(max(ages[p1_i], ages[p2_i])))

            # Inject fresh random robots (age will become 1 after +1 below)
            for _ in range(n_inject):
                g = create_random_genome()
                new_genomes.append(g)
                new_controllers.append(make_controller(g))
                new_ages.append(0)

            # Evaluate only the new individuals (survivors keep cached fitness)
            t_gen_start = time.perf_counter()
            new_fitnesses = np.array(
                evaluator.evaluate_batch(new_genomes, new_controllers), dtype=float
            )

            # Pool = current survivors + new individuals (2 × pop_size)
            pool_g = genomes     + new_genomes
            pool_c = controllers + new_controllers
            pool_f = np.concatenate([fitnesses,  new_fitnesses])
            pool_a = np.concatenate([ages, np.array(new_ages, dtype=int)])

            # Pareto truncate back to population_size
            genomes, controllers, fitnesses, ages = pareto_select(
                pool_g, pool_c, pool_f, pool_a, population_size
            )
            ages = ages + 1   # everyone survives one more generation

        else:
            # ── Original tournament-3 + elite-2 ────────────────────
            order = np.argsort(fitnesses)[::-1]

            new_genomes     = [genomes[i].copy()             for i in order[:elite_size]]
            new_controllers = [copy.deepcopy(controllers[i]) for i in order[:elite_size]]

            while len(new_genomes) < population_size:
                p1_i, p2_i = tournament(), tournament()
                p1_g, p2_g = genomes[p1_i], genomes[p2_i]
                p1_c, p2_c = controllers[p1_i], controllers[p2_i]

                if np.random.random() < crossover_rate:
                    child_g = crossover_3d(p1_g, p2_g)
                else:
                    child_g = p1_g.copy()
                child_g  = mutate(child_g, mutation_rate)
                n_active = count_active_tendons(child_g)
                child_c  = crossover_controller(p1_c, p2_c, n_active)
                child_c  = mutate_controller(child_c, mutation_rate)
                new_genomes.append(child_g)
                new_controllers.append(child_c)

            genomes     = new_genomes
            controllers = new_controllers
            ages        = np.ones(population_size, dtype=int)

            # Re-evaluate new population (no fitness caching in standard mode)
            t_gen_start = time.perf_counter()
            fitnesses = np.array(
                evaluator.evaluate_batch(genomes, controllers), dtype=float
            )

    # ── Save final results ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"EVOLUTION COMPLETE — best fitness: {best_fitness:.4f}m")
    print("=" * 70)

    with open(out / 'best_robot.pkl', 'wb') as f:
        pickle.dump({'genome': best_genome, 'controller': best_controller,
                     'fitness': best_fitness}, f)
    with open('best_robot_tendon.pkl', 'wb') as f:
        pickle.dump({'genome': best_genome, 'controller': best_controller,
                     'fitness': best_fitness}, f)
    with open(out / 'history.json', 'w') as f:
        json.dump(history, f, indent=2)

    print(f"\nFiles saved:")
    print(f"  {out / 'best_robot.pkl'}")
    print(f"  best_robot_tendon.pkl  (root, for quick access)")
    print(f"  {out / 'history.json'}")
    return best_genome, best_controller, best_fitness, history


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tendon-based soft robot evolution")
    parser.add_argument("--pop",        type=int,   default=DEFAULT_POP)
    parser.add_argument("--gen",        type=int,   default=DEFAULT_GEN)
    parser.add_argument("--sim-time",   type=float, default=DEFAULT_SIM_TIME)
    parser.add_argument("--settle",     type=float, default=DEFAULT_SETTLE_TIME)
    parser.add_argument("--elite",      type=int,   default=DEFAULT_ELITE,
                        help="Elite size (only used with --no-age-pareto)")
    parser.add_argument("--mut",        type=float, default=DEFAULT_MUT_RATE)
    parser.add_argument("--xover",      type=float, default=DEFAULT_XOVER_RATE)
    parser.add_argument("--freq",       type=float, default=DEFAULT_FREQ)
    parser.add_argument("--amp",        type=float, default=DEFAULT_AMP)
    parser.add_argument("--workers",    type=int,   default=DEFAULT_WORKERS,
                        help=f"Parallel worker processes (default: {DEFAULT_WORKERS})")
    parser.add_argument("--inject",     type=int,   default=None,
                        help="Fresh random robots injected per gen (default: pop//10)")
    parser.add_argument("--age-pareto", dest="age_pareto", action="store_true",  default=True)
    parser.add_argument("--no-age-pareto", dest="age_pareto", action="store_false",
                        help="Use original tournament-3 + elite selection instead")
    parser.add_argument("--name",       type=str,   default="tendon_run")
    parser.add_argument("--seed",       type=int,   default=42)
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
        n_workers       = args.workers,
        use_age_pareto  = args.age_pareto,
        n_inject        = args.inject,
        name            = args.name,
        seed            = args.seed,
    )
