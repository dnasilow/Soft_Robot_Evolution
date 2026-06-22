"""
Tendon-Based Soft Robot Evolution
==================================
Canonical entry point for evolving soft robots using the MuJoCo tendon physics.

Genome: CPPN (Compositional Pattern Producing Network) → voxel grid decoder
        Maps (x,y,z,dist) → material type at each grid position.
        Enables meaningful NEAT-style crossover in weight-space.
        Reference: Cheney et al., "Unshackling Evolution", GECCO 2013.
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
from src.evolution.cppn_genome import CPPNGenome, InnovationCounter

# ──────────────────────────────────────────────────────────────────
# Keep-awake (Windows): stop the machine entering Modern Standby mid-run.
# We observed the dev box enter Modern Standby under load every ~10-25 min,
# which silently killed multi-hour runs (no traceback, no crash event).
# SetThreadExecutionState(ES_SYSTEM_REQUIRED) forces the working state; we
# re-assert periodically because Modern Standby can otherwise still engage.
# Needs no admin rights; the OS clears the request when the process exits.
# ──────────────────────────────────────────────────────────────────
def _prevent_sleep():
    """Keep the system awake (and this process alive) for the run.

    Two layers, because Modern Standby (S0) ignores the legacy call on its own:
      1. SetThreadExecutionState(ES_SYSTEM_REQUIRED) — legacy idle-sleep block.
      2. PowerSetRequest(ExecutionRequired + SystemRequired) — the modern Power
         Request API; ExecutionRequired specifically keeps THIS process running
         through Modern Standby instead of being suspended/killed.
    Returns a stop() callable. No-op off Windows.
    """
    import sys
    if not sys.platform.startswith("win"):
        return lambda: None
    import ctypes
    import threading
    from ctypes import wintypes

    ES_CONTINUOUS      = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    kernel32 = ctypes.windll.kernel32

    def _assert_legacy():
        return kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

    # ── Layer 2: Power Request API (best for Modern Standby) ──────────────────
    POWER_REQUEST_CONTEXT_VERSION       = 0
    POWER_REQUEST_CONTEXT_SIMPLE_STRING = 0x1
    PowerRequestSystemRequired    = 0
    PowerRequestExecutionRequired = 3

    class _REASON_CONTEXT(ctypes.Structure):
        _fields_ = [("Version", wintypes.ULONG),
                    ("Flags", wintypes.DWORD),
                    ("SimpleReasonString", wintypes.LPWSTR)]

    h_request = None
    exec_ok = False
    try:
        kernel32.PowerCreateRequest.restype  = wintypes.HANDLE
        kernel32.PowerCreateRequest.argtypes = [ctypes.POINTER(_REASON_CONTEXT)]
        kernel32.PowerSetRequest.argtypes    = [wintypes.HANDLE, ctypes.c_int]
        kernel32.PowerClearRequest.argtypes  = [wintypes.HANDLE, ctypes.c_int]
        ctx = _REASON_CONTEXT(POWER_REQUEST_CONTEXT_VERSION,
                              POWER_REQUEST_CONTEXT_SIMPLE_STRING,
                              "soft-robot evolution run")
        h_request = kernel32.PowerCreateRequest(ctypes.byref(ctx))
        if h_request and h_request != wintypes.HANDLE(-1).value:
            kernel32.PowerSetRequest(h_request, PowerRequestSystemRequired)
            exec_ok = bool(kernel32.PowerSetRequest(h_request, PowerRequestExecutionRequired))
    except Exception:
        h_request = None

    legacy_ok = _assert_legacy()
    stop_evt  = threading.Event()

    def _keepalive():
        while not stop_evt.wait(45):   # re-assert legacy layer every 45 s
            _assert_legacy()

    threading.Thread(target=_keepalive, daemon=True).start()

    def stop():
        stop_evt.set()
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        if h_request:
            try:
                kernel32.PowerClearRequest(h_request, PowerRequestExecutionRequired)
                kernel32.PowerClearRequest(h_request, PowerRequestSystemRequired)
                kernel32.CloseHandle(h_request)
            except Exception:
                pass

    if legacy_ok and exec_ok:
        status = "ON (system + execution required — survives Modern Standby)"
    elif legacy_ok:
        status = "PARTIAL (idle-block only; Modern Standby may still suspend)"
    else:
        status = "FAILED (run may sleep!)"
    print(f"  Keep-awake : {status}")
    return stop


# ──────────────────────────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────────────────────────
DEFAULT_POP         = 10
DEFAULT_GEN         = 20
DEFAULT_SIM_TIME    = 2.5    # seconds per evaluation = 25 cycles at 10 Hz (after settling)
DEFAULT_SETTLE_TIME = 0.5    # seconds settling before measuring
DEFAULT_ELITE       = 2
DEFAULT_MUT_RATE    = 0.3
DEFAULT_XOVER_RATE  = 0.7
DEFAULT_FREQ        = 10.0   # Hz
DEFAULT_AMP         = 0.08   # ±8% rest length (matches material test scripts)
DEFAULT_WORKERS     = max(1, (os.cpu_count() or 4) - 2)   # leave 2 cores for OS
DEFAULT_INJECT_FRAC = 0.10   # fraction of pop injected as fresh random each gen


# ──────────────────────────────────────────────────────────────────
# CPPN helpers
# ──────────────────────────────────────────────────────────────────
def _make_valid_cppn(innov: InnovationCounter,
                     rng: np.random.Generator,
                     max_tries: int = 50) -> tuple[CPPNGenome, np.ndarray]:
    """Create a random CPPN whose decoded grid meets minimum voxel count."""
    for _ in range(max_tries):
        cppn = CPPNGenome(innov, rng)
        grid = cppn.to_voxel_grid()
        if grid is not None:
            return cppn, grid
    raise RuntimeError("Failed to generate a valid CPPN genome — check MIN_VOXELS_PER_ROBOT")


def _breed_child(parent_cppn1: CPPNGenome,
                 parent_cppn2: CPPNGenome,
                 fitness1: float,
                 fitness2: float,
                 innov: InnovationCounter,
                 rng: np.random.Generator,
                 crossover_rate: float,
                 mutation_rate: float) -> tuple[CPPNGenome, np.ndarray]:
    """
    Produce a child CPPN + decoded grid.
    Falls back to parent 1 (unchanged) if child grid is invalid after 5 tries.
    """
    for _ in range(5):
        if rng.random() < crossover_rate:
            child_cppn = CPPNGenome.crossover(
                parent_cppn1, parent_cppn2, fitness1, fitness2, rng=rng
            )
        else:
            child_cppn = parent_cppn1.copy()
        child_cppn = child_cppn.mutate(innov, rate=mutation_rate)
        child_grid = child_cppn.to_voxel_grid()
        if child_grid is not None:
            return child_cppn, child_grid

    # Rare fallback: just re-mutate parent 1
    child_cppn = parent_cppn1.mutate(innov, rate=mutation_rate)
    child_grid = child_cppn.to_voxel_grid()
    if child_grid is None:
        _fb        = parent_cppn1.to_voxel_grid()
        child_grid = _fb if _fb is not None else create_connected_genome()
        child_cppn = parent_cppn1.copy()
    return child_cppn, child_grid


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
def pareto_select(genomes, controllers, fitnesses, ages, target_n, cppns=None,
                  select_fitness=None, n_elite=0):
    """
    Non-dominated Pareto sort on two objectives:
      - fitness : maximise
      - age     : minimise  (younger = better)

    Individual A dominates B iff A is >= B on both objectives and
    strictly > on at least one.

    select_fitness : optional array used for the fitness objective during
    domination + within-front ranking (e.g. species-shared fitness). When given,
    selection uses it but the RAW `fitnesses` are still what gets returned, so
    reporting/champion tracking stay on true distance.

    n_elite : guarantee the top n_elite individuals by RAW fitness survive. Without
    this, species-fitness-sharing and the age objective can cull the actual champion
    (observed: best found 0.152 m then regressed). Elites are swapped in for the
    worst non-elite selected, so the population never loses its best find.

    Returns (genomes, controllers, fitnesses, ages, cppns) of the top target_n
    individuals, ordered front-by-front then by fitness within the last
    partial front.  cppns element mirrors the input list (may be None).
    """
    n = len(genomes)
    sf = fitnesses if select_fitness is None else select_fitness
    dom_count  = np.zeros(n, dtype=int)      # how many individuals dominate i
    dom_over   = [[] for _ in range(n)]      # indices that i dominates

    for i in range(n):
        for j in range(i + 1, n):
            fi, ai = sf[i], ages[i]
            fj, aj = sf[j], ages[j]
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
            current_front.sort(key=lambda i: sf[i], reverse=True)
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

    # ── Elitism: force-keep the top n_elite by RAW fitness ──────────────────
    if n_elite > 0:
        fr        = np.asarray(fitnesses, dtype=float)
        elite     = list(np.argsort(fr)[::-1][:n_elite])
        elite_set = set(elite)
        sel_set   = set(selected)
        missing   = [e for e in elite if e not in sel_set]
        if missing:
            # worst-first among currently-selected non-elites (by selection fitness)
            non_elite_sel = sorted((i for i in selected if i not in elite_set),
                                   key=lambda i: sf[i])
            for e in missing:
                if not non_elite_sel:
                    break
                worst = non_elite_sel.pop(0)
                selected[selected.index(worst)] = e

    return (
        [genomes[i]     for i in selected],
        [controllers[i] for i in selected],
        np.array([fitnesses[i] for i in selected], dtype=float),
        np.array([ages[i]      for i in selected], dtype=int),
        [cppns[i] for i in selected] if cppns is not None else None,
    )


# ──────────────────────────────────────────────────────────────────
# Speciation + explicit fitness sharing  (NEAT, layered on top of AFPO)
# ──────────────────────────────────────────────────────────────────
SPECIES_THRESHOLD = 1.5   # compat distance to split a species (un-normalised: ~1 added
                          # node ≈ 2.0, weights-only diffs ≈ 0.4-0.8, so 1.5 separates them)


def speciate_and_share(cppns, fitnesses, threshold: float = SPECIES_THRESHOLD):
    """
    Group genomes into species by CPPN compatibility distance and return
    species-shared fitness (raw / species_size) plus the species count.

    Fitness sharing protects structural innovation: a freshly-complexified CPPN
    forms a small species, so its members are divided by a small number and
    survive selection long enough for their new weights to be tuned — which is
    exactly what was NOT happening (CPPNs stayed at 0 hidden nodes).
    """
    reps     = []   # representative cppn per species
    members  = []   # list of member-index lists
    assign   = [0] * len(cppns)

    for i, g in enumerate(cppns):
        placed = False
        for s_idx, rep in enumerate(reps):
            if CPPNGenome.distance(g, rep) < threshold:
                members[s_idx].append(i)
                assign[i] = s_idx
                placed = True
                break
        if not placed:
            reps.append(g)
            members.append([i])
            assign[i] = len(reps) - 1

    sizes = [len(m) for m in members]
    shared = np.array(
        [float(fitnesses[i]) / sizes[assign[i]] for i in range(len(cppns))],
        dtype=float,
    )
    return shared, len(reps)


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
    seed_from:       str   = None,   # path to final_population.pkl from a prior run
    seed_fraction:   float = 0.30,   # fraction of pop seeded from prior run (rest fresh)
    use_controller:  bool  = False,  # default: A1 open-loop material-phase (Cheney-faithful). True → legacy CPG.
    resume:          bool  = True,   # auto-resume from results/<name>/checkpoint.pkl if present
    species_threshold: float = SPECIES_THRESHOLD,  # NEAT compat distance; higher → fewer, larger species
):
    # Keep the machine awake for the whole run; release on any exit (normal or error).
    import atexit
    _stop_sleep = _prevent_sleep()
    atexit.register(_stop_sleep)

    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    out = Path(results_dir) / name
    out.mkdir(parents=True, exist_ok=True)

    innov = InnovationCounter()

    if n_inject is None:
        n_inject = max(1, population_size // 10)

    # A1: when running open-loop (no CPG), every "controller" is None and the physics
    # engine drives each active tendon by its material-derived base phase. This makes
    # the brain a pure function of the body, so it is inherited across body changes.
    def _new_ctrl(grid):
        return make_controller(grid) if use_controller else None

    print("=" * 70)
    print("TENDON-BASED SOFT ROBOT EVOLUTION")
    print("=" * 70)
    print(f"  Population : {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Sim time   : {sim_time}s  +  {settle_time}s settle")
    print(f"  Actuation  : {actuation_freq}Hz  +-{actuation_amp*100:.0f}%")
    if use_controller:
        print(f"  Controller : CPGController (per-tendon oscillators)")
    else:
        print(f"  Controller : OPEN-LOOP material-phase (A1, Cheney-faithful) — no CPG")
    print(f"  Encoding   : CPPN + NEAT crossover")
    if use_age_pareto:
        print(f"  Selection  : Age-Fitness Pareto  (inject {n_inject}/gen)")
    else:
        print(f"  Selection  : Tournament-3 + Elite-{elite_size}")
    print(f"  Workers    : {n_workers}")
    print(f"  Output dir : {out}")
    if seed_from:
        print(f"  Seeding    : {seed_from}")
    print("=" * 70)

    # ── Evaluator ───────────────────────────────────────────────────
    evaluator = MuJoCoTendonEvaluator(
        simulation_time     = sim_time,
        settle_time         = settle_time,
        actuation_frequency = actuation_freq,
        actuation_amplitude = actuation_amp,
        n_workers           = n_workers,
        attach_controller   = use_controller,
    )

    # ── Sanity check ────────────────────────────────────────────────
    print("\nRunning sanity check (1 CPPN robot)...")
    temp_innov   = InnovationCounter()
    temp_cppn   = CPPNGenome(temp_innov, rng)
    _tg         = temp_cppn.to_voxel_grid()
    test_genome = _tg if _tg is not None else create_connected_genome()
    try:
        test_fit = evaluator.evaluate_single(test_genome)
        print(f"  Sanity check passed — fitness={test_fit:.4f}m  "
              f"voxels={int((test_genome != 0).sum())}")
    except Exception as e:
        print(f"  SANITY CHECK FAILED: {e}")
        raise

    # ── Initial population (or resume from checkpoint) ──────────────
    innov.flush_gen_cache()

    ckpt_path = out / 'checkpoint.pkl'
    resuming  = bool(resume) and ckpt_path.exists()
    start_gen = 0
    history = {'best_fitness': [], 'mean_fitness': [], 'worst_fitness': []}
    best_genome = best_controller = best_cppn = None
    best_fitness = -np.inf

    if resuming:
        print(f"\nResuming from {ckpt_path} ...")
        with open(ckpt_path, 'rb') as f:
            ck = pickle.load(f)
        cppns           = ck['cppns']
        genomes         = ck['genomes']
        controllers     = ck['controllers']
        fitnesses       = np.array(ck['fitnesses'], dtype=float)
        ages            = np.array(ck['ages'], dtype=int)
        innov._count    = ck['innov_count']
        best_genome     = ck['best_genome']
        best_controller = ck['best_controller']
        best_cppn       = ck['best_cppn']
        best_fitness    = ck['best_fitness']
        history         = ck['history']
        start_gen       = ck['next_gen']
        np.random.set_state(ck['np_state'])
        rng.bit_generator.state = ck['rng_state']
        t_gen_start     = time.perf_counter()
        print(f"  Resumed at generation {start_gen + 1}/{generations}  |  best so far {best_fitness:.4f}m")
    elif seed_from:
        print(f"\nLoading seed population from {seed_from} ...")
        with open(seed_from, 'rb') as f:
            saved = pickle.load(f)
        all_cppns   = saved['cppns']
        all_genomes = saved['genomes']
        all_ctrls   = saved['controllers']
        all_fits    = np.array(saved['fitnesses'], dtype=float)
        innov._count = saved['innov_next']   # continue innovation numbering to avoid ID collisions

        # Keep only the top seed_fraction of the loaded population
        n_seed  = max(1, int(population_size * seed_fraction))
        top_idx = np.argsort(all_fits)[::-1][:n_seed]
        cppns       = [all_cppns[i]   for i in top_idx]
        genomes     = [all_genomes[i] for i in top_idx]
        controllers = [all_ctrls[i]   for i in top_idx]
        fitnesses   = all_fits[top_idx]
        print(f"  Kept top {n_seed} seeded robots  |  best: {fitnesses.max():.4f}m  worst: {fitnesses.min():.4f}m")

        # Fill remaining slots with fresh random robots and evaluate them
        n_fresh = population_size - n_seed
        print(f"  Generating {n_fresh} fresh robots to fill the rest ...")
        fresh_cppns, fresh_genomes, fresh_ctrls = [], [], []
        for _ in range(n_fresh):
            c, g = _make_valid_cppn(innov, rng)
            fresh_cppns.append(c)
            fresh_genomes.append(g)
            fresh_ctrls.append(_new_ctrl(g))

        print(f"  Evaluating {n_fresh} fresh robots ...")
        t_gen_start   = time.perf_counter()
        fresh_fits    = np.array(evaluator.evaluate_batch(fresh_genomes, fresh_ctrls), dtype=float)

        cppns       = cppns       + fresh_cppns
        genomes     = genomes     + fresh_genomes
        controllers = controllers + fresh_ctrls
        fitnesses   = np.concatenate([fitnesses, fresh_fits])
        ages        = np.ones(population_size, dtype=int)   # reset ages for all
    else:
        print(f"\nGenerating {population_size} CPPN robots...")
        cppns       = []
        genomes     = []
        for _ in range(population_size):
            c, g = _make_valid_cppn(innov, rng)
            cppns.append(c)
            genomes.append(g)
        controllers = [_new_ctrl(g) for g in genomes]
        ages        = np.ones(population_size, dtype=int)

        print(f"Evaluating initial population...")
        t_gen_start = time.perf_counter()
        fitnesses = np.array(evaluator.evaluate_batch(genomes, controllers), dtype=float)

    # ── Evolution loop ──────────────────────────────────────────────
    for gen in range(start_gen, generations):
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
            best_cppn       = cppns[best_idx].copy()

        shared_current, n_species = speciate_and_share(cppns, fitnesses, species_threshold)
        best_cppn_now = cppns[best_idx]
        cppn_str  = f"  cppn=N{best_cppn_now.n_nodes}/E{best_cppn_now.n_connections}"
        spec_str  = f"  species={n_species}"
        age_str   = f"  max_age={int(np.max(ages))}" if use_age_pareto else ""
        print(f"Gen {gen+1:3d}/{generations}  "
              f"best={gen_best:.4f}m  mean={gen_mean:.4f}m  "
              f"worst={gen_wst:.4f}m  [{elapsed:.1f}s]{age_str}{spec_str}{cppn_str}")

        # ── Per-generation checkpoint (Ctrl+C safe after this) ─────
        with open('best_robot_tendon.pkl', 'wb') as f:
            pickle.dump({'genome': best_genome, 'controller': best_controller,
                         'fitness': best_fitness, 'cppn': best_cppn}, f)

        with open(out / f"gen_{gen+1:03d}.json", "w") as f:
            json.dump({
                'generation':    gen + 1,
                'best_fitness':  gen_best,
                'mean_fitness':  gen_mean,
                'worst_fitness': gen_wst,
                'fitnesses':     fitnesses.tolist(),
                'time_s':        elapsed,
            }, f)

        # ── Full-population checkpoint (atomic) — resume here if killed ─
        # next_gen = gen: re-enter this generation on resume; we only lose the
        # in-progress breeding, never an evaluated generation.
        _ck = {
            'cppns': cppns, 'genomes': genomes, 'controllers': controllers,
            'fitnesses': fitnesses.tolist(), 'ages': ages.tolist(),
            'innov_count': innov._count, 'next_gen': gen,
            'best_genome': best_genome, 'best_controller': best_controller,
            'best_cppn': best_cppn, 'best_fitness': best_fitness,
            'history': history,
            'np_state': np.random.get_state(), 'rng_state': rng.bit_generator.state,
        }
        _tmp = out / 'checkpoint.pkl.tmp'
        with open(_tmp, 'wb') as f:
            pickle.dump(_ck, f)
        os.replace(_tmp, ckpt_path)

        if gen == generations - 1:
            break   # don't breed after last generation

        # ── Reproduce ──────────────────────────────────────────────
        def tournament():
            cands = np.random.choice(population_size, 3, replace=False)
            return int(cands[np.argmax(shared_current[cands])])   # species-shared fitness

        innov.flush_gen_cache()

        if use_age_pareto:
            # ── Age-Fitness Pareto breeding ─────────────────────────
            n_breed = population_size - n_inject
            new_cppns       = []
            new_genomes     = []
            new_controllers = []
            new_ages        = []

            for _ in range(n_breed):
                p1_i, p2_i = tournament(), tournament()
                p1_c, p2_c = controllers[p1_i], controllers[p2_i]

                child_cppn, child_g = _breed_child(
                    cppns[p1_i], cppns[p2_i],
                    float(fitnesses[p1_i]), float(fitnesses[p2_i]),
                    innov, rng, crossover_rate, mutation_rate,
                )
                if use_controller:
                    n_active = count_active_tendons(child_g)
                    child_c  = crossover_controller(p1_c, p2_c, n_active)
                    child_c  = mutate_controller(child_c, mutation_rate)
                else:
                    child_c = None

                new_cppns.append(child_cppn)
                new_genomes.append(child_g)
                new_controllers.append(child_c)
                new_ages.append(int(max(ages[p1_i], ages[p2_i])))

            # Inject fresh random robots (age will become 1 after +1 below)
            for _ in range(n_inject):
                c, g = _make_valid_cppn(innov, rng)
                new_cppns.append(c)
                new_genomes.append(g)
                new_controllers.append(_new_ctrl(g))
                new_ages.append(0)

            # Evaluate only the new individuals (survivors keep cached fitness)
            t_gen_start = time.perf_counter()
            new_fitnesses = np.array(
                evaluator.evaluate_batch(new_genomes, new_controllers), dtype=float
            )

            # Pool = current survivors + new individuals (2 × pop_size)
            pool_cppns = cppns       + new_cppns
            pool_g     = genomes     + new_genomes
            pool_c     = controllers + new_controllers
            pool_f     = np.concatenate([fitnesses, new_fitnesses])
            pool_a     = np.concatenate([ages, np.array(new_ages, dtype=int)])

            # Pareto truncate back to population_size, selecting on species-shared
            # fitness (protects innovation) but returning raw fitness for reporting.
            shared_pool, _ = speciate_and_share(pool_cppns, pool_f, species_threshold)
            genomes, controllers, fitnesses, ages, cppns = pareto_select(
                pool_g, pool_c, pool_f, pool_a, population_size, cppns=pool_cppns,
                select_fitness=shared_pool, n_elite=elite_size,
            )
            ages = ages + 1   # everyone survives one more generation

        else:
            # ── Original tournament-3 + elite-2 ────────────────────
            order = np.argsort(fitnesses)[::-1]

            new_cppns       = [cppns[i].copy()               for i in order[:elite_size]]
            new_genomes     = [genomes[i].copy()              for i in order[:elite_size]]
            new_controllers = [copy.deepcopy(controllers[i])  for i in order[:elite_size]]

            while len(new_genomes) < population_size:
                p1_i, p2_i = tournament(), tournament()
                p1_c, p2_c = controllers[p1_i], controllers[p2_i]

                child_cppn, child_g = _breed_child(
                    cppns[p1_i], cppns[p2_i],
                    float(fitnesses[p1_i]), float(fitnesses[p2_i]),
                    innov, rng, crossover_rate, mutation_rate,
                )
                if use_controller:
                    n_active = count_active_tendons(child_g)
                    child_c  = crossover_controller(p1_c, p2_c, n_active)
                    child_c  = mutate_controller(child_c, mutation_rate)
                else:
                    child_c = None
                new_cppns.append(child_cppn)
                new_genomes.append(child_g)
                new_controllers.append(child_c)

            cppns       = new_cppns
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
                     'fitness': best_fitness, 'cppn': best_cppn}, f)
    with open('best_robot_tendon.pkl', 'wb') as f:
        pickle.dump({'genome': best_genome, 'controller': best_controller,
                     'fitness': best_fitness, 'cppn': best_cppn}, f)
    with open(out / 'history.json', 'w') as f:
        json.dump(history, f, indent=2)

    # Save full final population so the next run can warm-start with --seed-from
    with open(out / 'final_population.pkl', 'wb') as f:
        pickle.dump({
            'cppns':       cppns,
            'genomes':     genomes,
            'controllers': controllers,
            'fitnesses':   fitnesses.tolist(),
            'ages':        ages.tolist(),
            'innov_next':  innov._count,   # continue innovation numbering in next run
        }, f)

    print(f"\nFiles saved:")
    print(f"  {out / 'best_robot.pkl'}")
    print(f"  best_robot_tendon.pkl  (root, for quick access)")
    print(f"  {out / 'history.json'}")
    print(f"  {out / 'final_population.pkl'}  (seed for next run with --seed-from)")

    # Finished cleanly — drop the resume checkpoint so a re-run starts fresh.
    try:
        ckpt_path.unlink(missing_ok=True)
    except Exception:
        pass

    evaluator.close()   # shut the persistent worker pool down cleanly
    _stop_sleep()       # release the keep-awake request promptly
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
                        help=f"Elites kept each gen by RAW fitness (default {DEFAULT_ELITE}); "
                             f"protects the champion from fitness-sharing/age culling. 0 disables.")
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
    parser.add_argument("--seed-from",  type=str,   default=None,
                        help="Path to final_population.pkl from a prior run to warm-start from")
    parser.add_argument("--seed-frac",  type=float, default=0.30,
                        help="Fraction of pop to seed from prior run; rest generated fresh (default: 0.30)")
    parser.add_argument("--use-cpg", dest="use_cpg", action="store_true", default=False,
                        help="Opt into the legacy per-tendon CPGController. Default is the "
                             "Cheney-faithful open-loop material-phase actuation (A1), which the "
                             "2026-06-15 A/B showed gives a better population mean and is simpler.")
    parser.add_argument("--open-loop", dest="open_loop", action="store_true", default=False,
                        help="(now the default) Kept as a no-op for backward compatibility.")
    parser.add_argument("--no-resume", dest="resume", action="store_false", default=True,
                        help="Ignore any existing results/<name>/checkpoint.pkl and start fresh. "
                             "By default a run auto-resumes from its checkpoint if one exists.")
    parser.add_argument("--species-threshold", type=float, default=SPECIES_THRESHOLD,
                        help=f"NEAT speciation distance (default {SPECIES_THRESHOLD}). Higher = "
                             f"fewer, larger species (stronger fitness-sharing); try 2.0-2.5 if "
                             f"the run over-speciates.")
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
        seed_from       = args.seed_from,
        seed_fraction   = args.seed_frac,
        use_controller    = args.use_cpg and not args.open_loop,
        resume            = args.resume,
        species_threshold = args.species_threshold,
    )
