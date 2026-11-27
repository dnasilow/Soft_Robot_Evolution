"""The transfer outcome of the protocol (paper/PROTOCOL.md, sections 4 and 9.4): every final
champion scored in the simulator it was NOT evolved in. Here: the champions of arms R, Rc and A,
which were evolved in the 2013 simulator, and the deposited 2013 champions, scored in this
project's MuJoCo engine with the settings of --preset cheney2013. Committed before it was first
run on an arm.

usage, from the project folder:
    python paper/analysis/transfer_scores.py --arms R Rc
        the champions of the named arms and the deposited champions of their conditions.
        Refuses an arm that has not been analysed (no report in paper/outcomes/).
    python paper/analysis/transfer_scores.py --arms R Rc A --preset cheney2013-floor
        the same under the other preset of the campaign, the settings of arm D: the 2013
        simulator's floor rule, and every body started where it is in the workspace
        (PROTOCOL.md, section 9.5, which asks for the outcome under both presets). Written as
        transfer_floor2013.*; the report under --preset cheney2013 is not touched.
    python paper/analysis/transfer_scores.py --rehearsal pilot10_P0_s --generation 10
        the same scoring for runs that are NOT an arm (pilots, trials)

What the report contains
  per set of champions   how many, how many blew up; the score in each simulator; the transfer
                         ratio (score here over the score the robot was evolved with) with a
                         bootstrapped 95% interval of its median; Spearman's rank correlation
                         between the two simulators' scores
  comparisons            each arm against the deposited champions of its condition (arm A also
                         against arm R) on the transfer ratio: A12 and two-sided Mann-Whitney U.
                         Descriptive: no criterion, p-values not corrected
  the same, as placed    the 2013 simulator starts a body where it is in the workspace, in the air
                         if it does not touch the bottom; the MuJoCo engine sets every body on the
                         floor. Champions that do not touch the bottom are scored a second time,
                         started at their height, and the statistics are given both ways
  time-step check        the first five champions of each set once more with a quarter of the
                         time step
  per champion           everything recorded with each evaluation

An evaluation takes one to two minutes. Finished evaluations are kept in results/transfer/, so
a run that is stopped loses nothing and a set that was scored before is not scored again.
The report is printed and written to results/analysis/ as text, JSON and CSV.
"""
import argparse
import csv
import datetime
import gc
import hashlib
import json
import os
import pickle
import re
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))

import search_arm                                             # noqa: E402

# One linear-algebra thread in this process and in every worker process it starts, as the
# campaign's launcher gives its runs (PROTOCOL.md, section 9.6). It must be set before numpy is
# loaded: left to itself each process sets memory aside for one thread per logical processor,
# 1.5 GB on this machine, and uses none of it. The scores do not depend on it.
os.environ.update(search_arm.ONE_THREAD)

import numpy as np                                            # noqa: E402

import analyse_arm as aa                                      # noqa: E402
import protocol_stats as ps                                   # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402

PRESET = 'cheney2013'                     # the preset the outcome was fixed with (section 9.4)
FLOOR_PRESET = 'cheney2013-floor'         # the other preset of the campaign, arm D's settings (section 9.5)
SLIP_SPEED, STICK_SPEED = 0.02, 0.01      # the defaults of --slip-speed and --stick-speed
NO_EARLY_STOP = -1e9                      # a robot is never judged a non-mover (section 9.4, point 3)
CHECK_FRACTION = 0.25                     # the time-step check: a quarter of the engine's step
CHECK_CHAMPIONS = 5                       # ... on the first five champions of each set
REPLAY = os.path.join(ROOT, 'paper', 'reference_2013', 'replay_2013_simulator.csv')
DIAGNOSTIC = os.path.join(ROOT, 'paper', 'diagnostics_2026-11-18', 'replay2_cheney_results.json')
FLOOR_TEST = os.path.join(ROOT, 'paper', 'diagnostics_2026-11-25', 'built_in_floor_check.json')
CACHE = os.path.join(ROOT, 'results', 'transfer', 'evaluations.json')
CONDITIONS = {'noCost': 'no cost', 'costNumActuated': 'actuated cost'}


# --------------------------------------------------------------------------------------------
# the engine: the search's own evaluation under the preset
# --------------------------------------------------------------------------------------------
def evaluator_arguments(early_stop=False, workspace=None, preset=PRESET):
    """The arguments run_tendon_evolution.py gives its evaluator under a preset (--preset
    cheney2013 unless another is named), read from the preset itself. early_stop=True keeps the
    search's early stop (used only to check this function against a real run); the transfer
    outcome switches it off."""
    import run_tendon_evolution as runner
    name, preset = preset, dict(runner._PRESETS[preset])
    used = set()

    def take(key):
        used.add(key)
        return preset[key]

    side = int(take('grid_size'))
    if workspace is not None:
        side = int(workspace)
    arguments = dict(
        simulation_time=float(take('sim_time')), settle_time=float(take('settle')),
        actuation_frequency=float(take('freq')), actuation_amplitude=float(take('amp')),
        n_workers=1, attach_controller=False, use_flex=False, voxel_size=0.01,
        fitness_mode=take('fitness'), wave_phase_n=None,
        max_voxels=side ** 3 if take('no_trim') else None,
        friction={'mode': 'stickslip', 'mu_s': float(take('friction_static')), 'mu_k': float(take('friction_kinetic')),
                  'v_on': SLIP_SPEED, 'v_off': STICK_SPEED},
        early_term_threshold=None if early_stop else NO_EARLY_STOP, early_term_fraction=None,
        body=take('body'), poisson=take('poisson') == 'on', dt_rule='voxelyze', materials=take('materials'),
        gravity=None, floor_contact=take('floor_contact'), phase_mode='offset',
        direction=take('direction'), divide_by=take('divide_by'), workspace_voxels=side,
        global_damping=float(take('damping_global')), penalty='none', penalty_exp=1.0,
        start=take('start') if 'start' in preset else 'floor',
    )
    unused = sorted(set(preset) - used)
    if unused:
        raise SystemExit(f'The preset {name} has settings this script does not know: {unused}. '
                         f'It must be taught them before it can speak for the preset.')
    return arguments


def worker_parameters(arguments):
    """What the search hands each of its worker processes for one evaluation."""
    from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
    evaluator = MuJoCoTendonEvaluator(**arguments)
    try:
        return dict(evaluator._params)
    finally:
        evaluator.close()


GB_PER_WORKER = 0.5      # allowed for a worker. With one linear-algebra thread and MuJoCo's memory stated
                         # (27 November 2026) a process with a full workspace of 1000 voxels asks the system for
                         # 0.1 GB; before that it was 1.5 GB for the libraries' threads and up to 1.7 GB that
                         # MuJoCo reserved, and this allowance was 3 GB
KEEP_FREE_GB = 6.0       # left for everything else on the machine, the running arm above all


free_commit_gb = search_arm.free_commit_gb      # how much memory Windows can still promise to programs, in GB


def workers_that_fit(wanted, free=None, say=print):
    """No more worker processes than the machine's free memory allows; stops if not even one fits."""
    free = free_commit_gb() if free is None else free
    if free is None:
        return wanted
    fit = int((free - KEEP_FREE_GB) / GB_PER_WORKER)
    if fit < 1:
        raise SystemExit(f'Only {free:.1f} GB of memory are left to promise to programs; {GB_PER_WORKER:g} GB are '
                         f'allowed for an evaluation and {KEEP_FREE_GB:g} GB stay free for the rest. Nothing was started.')
    if fit < wanted:
        say(f'{free:.0f} GB of memory are left to promise to programs: {fit} worker processes instead of {wanted}.')
    return min(wanted, fit)


def out_of_memory(exc):
    """True if the exception means the machine had no memory to give. That is not a result of the
    robot, so it must stop the run instead of being recorded as a score of zero."""
    return isinstance(exc, MemoryError) or 'allocate' in str(exc).lower()


def score_one(job):
    """One body in the MuJoCo engine. The evaluation is the search's own (the body of
    mujoco_tendon_evaluator._eval_worker: same engine, same call), with what section 9.4 records
    next to it. step_fraction below 1 shortens the time step for the time-step check."""
    key, grid, params, step_fraction = job
    started = time.time()
    out = {'key': key, 'score': 0.0, 'blew_up': False, 'error': None, 'moved': None, 'time_step': None,
           'normal_time_step': None, 'steps': None, 'sunk': None, 'consistent': None,
           'step_fraction': float(step_fraction)}
    engine = None
    from src.evolution import mujoco_tendon_evaluator as evaluation
    import src.physics.mujoco_beam_physics as beam
    try:
        engine = evaluation._make_engine(params)
        if step_fraction != 1.0:
            usual = beam.DT_FRAC_VX if engine.dt_rule == 'voxelyze' else beam.DT_FRAC
            engine.dt_frac = usual * step_fraction
        engine.load_robot(np.asarray(grid), voxel_size=params['voxel_size'],
                          initial_height=evaluation._start_height(np.asarray(grid), params), gait_params=None)
        size = float(engine.voxel_size)
        out['time_step'] = float(engine.default_timestep)
        out['normal_time_step'] = float(engine.stable_dt(None))
        out['steps'] = int(params['simulation_time'] / engine.default_timestep)
        start = np.array(engine.get_position(), float)
        lowest = [float(engine.data.xpos[1:, 2].min())]
        step = engine.step

        def watched_step():
            step()
            z = float(engine.data.xpos[1:, 2].min())
            if z < lowest[0]:
                lowest[0] = z

        engine.step = watched_step
        score = engine.get_fitness(simulation_time=params['simulation_time'], settle_time=params['settle_time'],
                                   return_descriptors=False, **evaluation._fitness_kw(params))
        out['score'] = float(score)
        out['blew_up'] = bool(engine.diverged())
        moved = (np.array(engine.get_position(), float) - start) / (params['workspace_voxels'] * size)
        if np.all(np.isfinite(moved)):
            out['moved'] = [float(v) for v in moved]
            # with no early stop and no settling the score IS the distance moved
            if not out['blew_up'] and params.get('early_term_threshold') == NO_EARLY_STOP:
                out['consistent'] = bool(abs(float(np.linalg.norm(moved)) - out['score']) <= 1e-9)
        if np.isfinite(lowest[0]):
            out['sunk'] = float((size / 2 - lowest[0]) / size)
    except Exception as exc:                                  # noqa: BLE001
        # The search's own rule (mujoco_tendon_evaluator.is_the_bodys_own, since 27 November 2026):
        # only an error that is the body's own is a score of 0. Any other is the machine's or the
        # code's and stops the scoring, as it stops a run of the search.
        if not evaluation.is_the_bodys_own(exc):
            what = 'out of memory while scoring' if out_of_memory(exc) else 'an error that is not a result of the robot'
            raise RuntimeError(f'{what} ({type(exc).__name__}: {exc})') from exc
        out['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        # The watched step refers to the engine and the engine to it; taken apart here so that the
        # engine's memory (over a GB for a large body) is given back before the next evaluation.
        if engine is not None:
            engine.__dict__.pop('step', None)
        del engine
        gc.collect()
    out['seconds'] = round(time.time() - started, 1)
    return out


# --------------------------------------------------------------------------------------------
# the champions
# --------------------------------------------------------------------------------------------
def grid_of_text(robot_text):
    """A robot file of the 2013 programs -> the 10 x 10 x 10 body in this project's numbering."""
    return c13.grid_from_rows([m.group(2) for m in c13.LAYER.finditer(robot_text)])


def grid_in_archive(archive, file_name):
    with tarfile.open(archive, 'r:gz') as t:
        for m in t:
            if m.isfile() and os.path.basename(m.name) == file_name:
                return grid_of_text(t.extractfile(m).read().decode('utf-8', 'replace'))
    raise SystemExit(f'{file_name} is not in {archive}.')


def grid_in_population(path, index, fitness):
    with open(path, 'rb') as f:
        population = pickle.load(f)
    if abs(float(population['fitnesses'][index]) - fitness) > 1e-12:
        raise SystemExit(f'{path}: individual {index} does not have the fitness of the analysed champion.')
    return c13.workspace_grid(np.asarray(population['genomes'][index]))


def arm_champions(arm, results=None, outcomes=None):
    """The final champions of an analysed arm, taken from its committed report, with their bodies.
    None if the arm has no report."""
    spec = aa.ARMS[arm]
    report = aa.finished_arm(arm, outcomes or aa.OUTCOMES)
    if report is None:
        return None
    search = spec['kind'] == 'search'
    results = results or (aa.SEARCH_RUNS if search else aa.RERUNS)
    out = []
    for row in report['per_seed']:
        c = row.get('champion')
        if not c or not c.get('body'):
            raise SystemExit(f"Arm {arm}, seed {row['seed']}: the arm's report has no champion for it.")
        folder = os.path.join(results, f"{spec['prefix']}{row['seed']}")
        if search:
            index = int(re.search(r'individual (\d+)$', c['file']).group(1))
            grid = grid_in_population(os.path.join(folder, 'final_population.pkl'), index, c['original'])
        else:
            grid = grid_in_archive(os.path.join(folder, f"Gen_{spec['generations']:04d}.tgz"), c['file'])
        if int((grid != 0).sum()) != int(c['body']['voxels']):
            raise SystemExit(f"Arm {arm}, seed {row['seed']}: the body read is not the body the arm's report measured.")
        out.append({'set': f'arm_{arm}', 'label': f"seed {row['seed']}", 'file': c['file'],
                    'evolved': float(c['original']), 'recorded_2013': None, 'grid': grid})
    return out


def campaign_build_scores(replay=REPLAY):
    """Every deposited robot's score in this campaign's build of the 2013 simulator."""
    with open(replay, newline='', encoding='utf-8') as f:
        return {(r['condition'], r['run'], r['file']): c13.fitness_from_result(r['final_com_dist_m'])
                for r in csv.DictReader(f)}


def deposited_champions(condition, robots=None, replay=REPLAY):
    """The final champions of the deposited runs of one condition, in the order of the body analysis."""
    robots = robots or aa.DEPOSITED_ROBOTS
    build = campaign_build_scores(replay)
    folder = f'2013-01-16-10^3-{condition}'
    out = []
    for c in aa.reference_champions(condition, robots):
        with open(os.path.join(robots, folder, c['run'], f'Gen_{aa.REFERENCE_GENERATION:04d}', c['file']),
                  encoding='utf-8', errors='replace') as f:
            grid = grid_of_text(f.read())
        if (folder, c['run'], c['file']) not in build:
            raise SystemExit(f"{c['run']}/{c['file']} is not in {replay}: its score in this campaign's build is unknown.")
        out.append({'set': f'deposit_{condition}', 'label': c['run'], 'file': c['file'],
                    'evolved': float(build[(folder, c['run'], c['file'])]), 'recorded_2013': float(c['original']),
                    'grid': grid})
    return out


def rehearsal_champions(prefix, generation, results=None):
    """Champions of runs of the original program that are not an arm."""
    results = results or aa.RERUNS
    out = []
    seeds = sorted(int(d[len(prefix):]) for d in os.listdir(results)
                   if d.startswith(prefix) and d[len(prefix):].isdigit() and os.path.isdir(os.path.join(results, d)))
    for seed in seeds:
        run = aa.load_run(os.path.join(results, f'{prefix}{seed}'), seed)
        aa.load_champion(run, generation)
        c = run.get('champion')
        if not c:
            continue
        grid = grid_in_archive(os.path.join(run['folder'], f'Gen_{generation:04d}.tgz'), c['file'])
        out.append({'set': f'rehearsal_{prefix}', 'label': f'seed {seed}', 'file': c['file'],
                    'evolved': float(c['original']), 'recorded_2013': None, 'grid': grid})
    return out


def set_title(name):
    kind, _, rest = name.partition('_')
    if kind == 'arm':
        return f'arm {rest}'
    if kind == 'deposit':
        return f'deposited 2013, {CONDITIONS.get(rest, rest)}'
    return f'rehearsal: {rest}'


# --------------------------------------------------------------------------------------------
# scoring, with what was already scored kept
# --------------------------------------------------------------------------------------------
def evaluation_key(grid, params, step_fraction, code):
    grid = np.ascontiguousarray(grid, np.int8)
    # A body set on the floor is what every evaluation was before the start became a setting:
    # left out of the key, so that what was scored before 25 November 2026 is still found.
    params = {k: v for k, v in params.items() if not (k == 'start' and v == 'floor')}
    h = hashlib.sha256()
    h.update(repr(grid.shape).encode())
    h.update(grid.tobytes())
    h.update(json.dumps(params, sort_keys=True, default=str).encode())
    h.update(repr((float(step_fraction), code)).encode())
    return h.hexdigest()[:32]


def read_cache(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_cache(path, cache):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache, f)
    os.replace(tmp, path)


def tell(text):
    print(text, flush=True)                                   # progress shows at once, also in a log file


def evaluate_all(jobs, workers, cache_path, evaluate=score_one, say=tell):
    """jobs: (key, grid, params, step_fraction, what it is). Returns {key: result}. Results already in
    the cache are not computed again; every new one is written to it as soon as it exists."""
    cache = read_cache(cache_path)
    todo = [j for j in jobs if j[0] not in cache]
    todo.sort(key=lambda j: j[3])                              # the long ones (short time step) first
    names = {j[0]: j[4] for j in jobs}
    say(f'{len(jobs)} evaluations: {len(jobs) - len(todo)} already done, {len(todo)} to do'
        + (f' with {workers} worker processes.' if todo else '.'))
    started, done = time.time(), 0

    def keep(result):
        nonlocal done
        done += 1
        cache[result['key']] = result
        write_cache(cache_path, cache)
        say(f"  {done:>3}/{len(todo)}  {names[result['key']]:<44} score {result['score']:.4f}"
            f"{'  BLEW UP' if result['blew_up'] else ''}{'  ERROR ' + result['error'] if result['error'] else ''}"
            f"  ({result['seconds']:.0f} s; {(time.time() - started) / 60:.1f} min so far)")

    plain = [j[:4] for j in todo]
    if todo and workers > 1:
        workers = workers_that_fit(workers, say=say)
    if todo and workers > 1:
        from multiprocessing import Pool
        with Pool(workers, maxtasksperchild=8) as pool:
            for result in pool.imap_unordered(evaluate, plain, chunksize=1):
                keep(result)
    else:
        for job in plain:
            keep(evaluate(job))
    return {j[0]: cache[j[0]] for j in jobs}


# --------------------------------------------------------------------------------------------
# the statistics of section 9.4
# --------------------------------------------------------------------------------------------
def summarise(rows, n_boot=None, seed=None):
    """One set of champions. rows: evolved (score in the simulator it was evolved in), score (in the
    other simulator), ratio, blew_up, error, and optionally recorded_2013, moved, sunk."""
    evolved = [r['evolved'] for r in rows]
    scores = [r['score'] for r in rows]
    ratios = [r['ratio'] for r in rows]
    _, lo, hi = ps.median_interval(ratios, n_boot, seed)
    rho, rho_lo, rho_hi = ps.rank_correlation(evolved, scores, n_boot, seed)
    out = {'n': len(rows), 'blew_up': int(sum(bool(r.get('blew_up')) for r in rows)),
           'failed': int(sum(bool(r.get('error')) for r in rows)),
           'evolved': list(ps.quartiles(evolved)), 'score': list(ps.quartiles(scores)),
           'ratio': list(ps.quartiles(ratios)), 'ratio_median_interval': [lo, hi],
           'rank_correlation': rho, 'rank_correlation_interval': [rho_lo, rho_hi],
           'kept_all_or_more': int(sum(r['ratio'] >= 1.0 for r in rows))}
    recorded = [r['recorded_2013'] for r in rows if r.get('recorded_2013') is not None]
    if len(recorded) == len(rows):
        out['recorded_2013'] = list(ps.quartiles(recorded))
        out['ratio_to_recorded_2013'] = list(ps.quartiles([r['score'] / r['recorded_2013'] for r in rows]))
    sunk = [r['sunk'] for r in rows if r.get('sunk') is not None]
    if sunk:
        out['sunk'] = list(ps.quartiles(sunk))
    upward = [abs(r['moved'][2]) / r['score'] for r in rows if r.get('moved') and r['score'] > 0]
    if upward:
        out['vertical_share'] = list(ps.quartiles(upward))
    return out


def compare_sets(x_rows, y_rows, n_boot=None, seed=None):
    """An arm's transfer ratios against a reference set's: A12 and Mann-Whitney, as in section 5."""
    return ps.compare([r['ratio'] for r in x_rows], [r['ratio'] for r in y_rows], n_boot, seed, with_ratio=False)


def lowest_layer(grid):
    """The lowest layer of the workspace the body occupies (0 = it touches the bottom)."""
    occupied = np.argwhere(np.asarray(grid) != 0)
    return int(occupied[:, 2].min()) if len(occupied) else 0


def as_placed(rows):
    """The same champions with the evaluation that started each body where it is in the workspace
    (section 9.4, point 9). A body that touches the bottom has one evaluation; it serves for both."""
    out = []
    for r in rows:
        p = r.get('placed')
        out.append(dict(r, **{k: p[k] for k in ('score', 'ratio', 'blew_up', 'error', 'moved', 'sunk')}) if p else r)
    return out


def step_check(rows):
    """The champions scored a second time with a shorter time step."""
    out = []
    for r in rows:
        q = r.get('quarter')
        if not q:
            continue
        change = (q['score'] - r['score']) / r['score'] if r['score'] > 0 else float('nan')
        out.append({'set': r['set'], 'label': r['label'], 'score': r['score'], 'score_short_step': q['score'],
                    'change': change, 'time_step': r['time_step'], 'short_time_step': q['time_step'],
                    'blew_up': bool(q['blew_up']), 'sunk': r.get('sunk'), 'sunk_short_step': q.get('sunk')})
    return out


def against_diagnostic(rows_by_set, diagnostic=DIAGNOSTIC):
    """The deposited champions were scored once before, on 18 November 2026, by other code under
    the same settings. Where today's champion is the robot scored then (same place in the run
    order, same recorded fitness), the two scores are compared."""
    if not os.path.isfile(diagnostic):
        return None
    with open(diagnostic, encoding='utf-8') as f:
        d = json.load(f)
    setting = [k for k in d['configs'] if k.startswith('D ')]
    earlier = {'deposit_noCost': (d['his'], d['configs'][setting[0]]['ours']) if setting else None,
               'deposit_costNumActuated': (d['cost_D']['his'], d['cost_D']['ours']) if 'cost_D' in d else None}
    out = {}
    for name, rows in rows_by_set.items():
        if not earlier.get(name) or len(earlier[name][0]) != len(rows):
            continue
        recorded, scores = earlier[name]
        differences = [abs(r['score'] - s) for r, rec, s in zip(rows, recorded, scores)
                       if r.get('recorded_2013') is not None and abs(r['recorded_2013'] - rec) <= 1e-9]
        if differences:
            out[name] = {'compared': len(differences), 'identical': int(sum(v <= 1e-9 for v in differences)),
                         'largest_difference': float(max(differences))}
    return out or None


def against_floor_test(rows_by_set, record=FLOOR_TEST):
    """Under --preset cheney2013-floor the champions of arms R and Rc and of the deposit were scored
    once before, on 25 November 2026, through the search's own worker function
    (paper/diagnostics_2026-11-25/check_built_in_floor.py). Where a champion was scored then, the
    two scores are compared."""
    if not os.path.isfile(record):
        return None
    with open(record, encoding='utf-8') as f:
        earlier = {(r['set'], r['label']): r['score'] for r in json.load(f)['rows'] if r['preset'] == 'new'}
    out = {}
    for name, rows in rows_by_set.items():
        differences = [abs(r['score'] - earlier[(name, r['label'])]) for r in rows if (name, r['label']) in earlier]
        if differences:
            out[name] = {'compared': len(differences), 'identical': int(sum(v <= 1e-9 for v in differences)),
                         'largest_difference': float(max(differences))}
    return out or None


# --------------------------------------------------------------------------------------------
# the report
# --------------------------------------------------------------------------------------------
def q(v, fmt='.2f'):
    return aa.med(v[0], v[1], v[2], fmt)


def render(report):
    preset = report.get('preset', PRESET)
    as_fixed = preset == PRESET                  # the outcome as section 9.4 fixed it; otherwise section 9.5
    L = [report['title'],
         f"Made {report['made']} with code {report['code']}; {report['settings']['n_boot']} bootstrap resamples, seed "
         f"{report['settings']['seed']}.",
         f'Engine: this project\'s MuJoCo engine with the settings of --preset {preset}, one evaluation of 0.25 s per '
         'champion, early stop off.', '']
    for note in report.get('notes', []):
        L.append(f'NOTE: {note}')
    if report.get('notes'):
        L.append('')

    L.append('Scores in workspace widths. Transfer ratio: score in the MuJoCo engine over the score in the '
             "campaign's build of the 2013 simulator.")

    def table(sets):
        T = [f"{'set':<30}  {'n':>3}  {'blew up':>7}  {'2013 simulator':>18}  {'MuJoCo engine':>18}  {'transfer ratio':>18}  "
             f"{'95% of its median':>17}  {'rank correlation (95%)':>23}  {'ratio >= 1':>10}"]
        for name, s in sets.items():
            T.append(f"{set_title(name):<30}  {s['n']:>3}  {s['blew_up']:>7}  {q(s['evolved']):>18}  {q(s['score']):>18}  "
                     f"{q(s['ratio']):>18}  {s['ratio_median_interval'][0]:>8.2f}-{s['ratio_median_interval'][1]:<8.2f}  "
                     f"{s['rank_correlation']:>+6.2f} ({s['rank_correlation_interval'][0]:+.2f} to "
                     f"{s['rank_correlation_interval'][1]:+.2f})  {s['kept_all_or_more']:>4} of {s['n']:<3}")
        return T

    def comparisons(rows):
        T = [f"{'':<44}  {'median (quartiles)':>18}  {'reference':>18}  {'A12 (95% interval)':>19}  {'p':>7}"]
        for c in rows:
            s = c['result']
            T.append(f"{set_title(c['set']) + ' against ' + set_title(c['reference']):<44}  "
                     f"{aa.med(s['arm_median'], s['arm_q25'], s['arm_q75']):>18}  "
                     f"{aa.med(s['reference_median'], s['reference_q25'], s['reference_q75']):>18}  "
                     f"{s['a12']:.2f} ({s['a12_interval'][0]:.2f}-{s['a12_interval'][1]:.2f})  {aa.pv(s['p']):>8}")
        return T

    L += ['', 'SETS OF CHAMPIONS, every body set on the floor: the preset as it is, the outcome named in section 4'
          if as_fixed else
          'SETS OF CHAMPIONS, under the 2013 floor rule and every body started where it is in the workspace: the preset '
          'as it is, the settings of arm D (section 9.5)']
    L += table(report['sets'])
    if report.get('comparisons'):
        L += ['', '  Comparisons on the transfer ratio (descriptive: no criterion, p not corrected)']
        L += comparisons(report['comparisons'])
    if report.get('sets_as_placed'):
        L += ['', 'THE SAME, every body started where it is in the workspace, as the 2013 simulator starts it (section 9.4, '
                  'point 9)']
        L.append('  Champions that do not touch the bottom of the workspace and so have a second evaluation: '
                 + ', '.join(f"{set_title(name)} {n} of {report['sets'][name]['n']}" for name, n in report['off_the_floor'].items()))
        L += table(report['sets_as_placed'])
        if report.get('comparisons_as_placed'):
            L += ['', '  Comparisons on the transfer ratio (descriptive: no criterion, p not corrected)']
            L += comparisons(report['comparisons_as_placed'])
    extra = [(name, s) for name, s in report['sets'].items() if 'recorded_2013' in s]
    if extra:
        L += ['', 'The deposited champions against the scores recorded in 2013 (another build of the same simulator):']
        for name, s in extra:
            L.append(f"  {set_title(name):<30}  recorded {q(s['recorded_2013'])}; MuJoCo score over the recorded score "
                     f"{q(s['ratio_to_recorded_2013'])}")
    L += ['', f"Recorded with {'the evaluations on the floor' if as_fixed else 'these evaluations'}: how deep the lowest "
              'voxel sank below the floor (voxels), and the vertical part of the distance moved (share of the score).']
    for name, s in report['sets'].items():
        if 'sunk' in s:
            L.append(f"  {set_title(name):<30}  sank {q(s['sunk'])}; vertical share "
                     f"{q(s['vertical_share']) if 'vertical_share' in s else '-'}")

    if report.get('step_check'):
        L += ['', f"TIME-STEP CHECK: the first {CHECK_CHAMPIONS} champions of each set once more with "
                  f"{CHECK_FRACTION:g} of the time step"]
        L.append(f"{'set':<30}  {'champion':<10}  {'score':>7}  {'short step':>10}  {'change':>7}  {'sank':>5}  {'short step':>10}")
        for r in report['step_check']:
            sunk = '-' if r['sunk'] is None else f"{r['sunk']:.2f}"
            sunk_short = '-' if r['sunk_short_step'] is None else f"{r['sunk_short_step']:.2f}"
            L.append(f"{set_title(r['set']):<30}  {r['label']:<10}  {r['score']:>7.3f}  {r['score_short_step']:>10.3f}  "
                     f"{100 * r['change']:>+6.1f}%  {sunk:>5}  {sunk_short:>10}{'  BLEW UP' if r['blew_up'] else ''}")
        changes = [abs(r['change']) for r in report['step_check'] if np.isfinite(r['change'])]
        if changes:
            L.append(f"  Change in absolute value: median {100 * float(np.median(changes)):.1f}%, largest "
                     f"{100 * max(changes):.1f}% ({len(changes)} champions).")
        if not as_fixed:
            L.append('  Under this preset the floor rule itself depends on the time step (section 9.5): it stops a voxel '
                     'that the brake would stop within one step. A shorter step therefore changes the rule as well as the '
                     'accuracy.')

    if report.get('diagnostic'):
        L += ['', 'AGAINST THE DIAGNOSTIC OF 18 NOVEMBER 2026 (the same robots, the same settings, other code)']
        for name, d in report['diagnostic'].items():
            L.append(f"  {set_title(name):<30}  {d['identical']} of {d['compared']} scores identical; largest difference "
                     f"{d['largest_difference']:.2e}")

    if report.get('floor_test'):
        L += ['', 'AGAINST THE SCORES OF 25 NOVEMBER 2026 (the same robots under the same preset, scored then through the '
                  'search\'s own worker function)']
        for name, d in report['floor_test'].items():
            L.append(f"  {set_title(name):<30}  {d['identical']} of {d['compared']} scores identical; largest difference "
                     f"{d['largest_difference']:.2e}")

    L += ['', 'PER CHAMPION. "placed": the score when the body is started where it is in the workspace (only bodies that '
              'do not touch its bottom).' if as_fixed else
          'PER CHAMPION. Every body is started where it is in the workspace; "lowest layer" says how many voxels up that is.']
    L.append(f"{'set':<30}  {'champion':<10}  {'voxels':>6}  {'lowest layer':>12}  {'2013 sim':>8}  {'MuJoCo':>7}  {'ratio':>6}  "
             f"{'placed':>7}  {'ratio':>6}  {'moved x':>8}  {'moved y':>8}  {'moved z':>8}  {'sank':>5}  {'time step':>9}  note")
    for r in report['champions']:
        moved = r['moved'] or [float('nan')] * 3
        p = r.get('placed')
        note = ', '.join(n for n in ('BLEW UP' if r['blew_up'] else '', r['error'] or '',
                                     'score and distance moved disagree' if r['consistent'] is False else '',
                                     'BLEW UP when placed' if p and p['blew_up'] else '',
                                     (p['error'] or '') if p else '') if n)
        sunk = '-' if r['sunk'] is None else f"{r['sunk']:.2f}"
        step = '-' if r['time_step'] is None else f"{r['time_step']:.2e}"
        placed = f"{p['score']:>7.3f}  {p['ratio']:>6.2f}" if p else f"{'':>7}  {'':>6}"
        L.append(f"{set_title(r['set']):<30}  {r['label']:<10}  {r['voxels']:>6}  {r['lowest_layer']:>12}  {r['evolved']:>8.3f}  "
                 f"{r['score']:>7.3f}  {r['ratio']:>6.2f}  {placed}  {moved[0]:>+8.3f}  {moved[1]:>+8.3f}  {moved[2]:>+8.3f}  "
                 f"{sunk:>5}  {step:>9}  {note}")
    return '\n'.join(L)


CSV_COLUMNS = ('set', 'label', 'file', 'voxels', 'lowest_layer', 'evolved', 'recorded_2013', 'score', 'ratio', 'blew_up',
               'error', 'moved_x', 'moved_y', 'moved_z', 'sunk', 'time_step', 'steps', 'seconds',
               'score_short_step', 'short_time_step', 'score_as_placed', 'ratio_as_placed', 'blew_up_as_placed',
               'moved_z_as_placed')


def write_csv(path, champions):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in champions:
            moved = r['moved'] or ['', '', '']
            quarter = r.get('quarter') or {}
            p = r.get('placed')
            w.writerow([r['set'], r['label'], r['file'], r['voxels'], r['lowest_layer'], r['evolved'],
                        '' if r['recorded_2013'] is None else r['recorded_2013'], r['score'], r['ratio'], int(r['blew_up']),
                        r['error'] or '', moved[0], moved[1], moved[2], '' if r['sunk'] is None else r['sunk'],
                        r['time_step'], r['steps'], r['seconds'], quarter.get('score', ''), quarter.get('time_step', '')]
                       + ([p['score'], p['ratio'], int(p['blew_up']), p['moved'][2] if p['moved'] else ''] if p
                          else ['', '', '', '']))


def comparisons_of(by_set, arms, n_boot=None, seed=None):
    out = []
    for arm in arms:
        spec = aa.ARMS[arm]
        pairs = [(f'arm_{arm}', f"deposit_{spec['condition']}")]
        if spec.get('against'):
            pairs.append((f'arm_{arm}', f"arm_{spec['against']}"))
        for x, y in pairs:
            if len(by_set.get(x, [])) >= 3 and len(by_set.get(y, [])) >= 3:
                out.append({'set': x, 'reference': y, 'result': compare_sets(by_set[x], by_set[y], n_boot, seed)})
    return out


def build_report(sets, results, keys, n_boot=None, seed=None, arms=(), preset=PRESET):
    """sets: {name: champions}; results: {key: evaluation}; keys: {(set, label, which): key} with which
    'floor' (every champion, under the preset as it is), 'short' (the time-step check) or 'placed'
    (bodies off the bottom, where the preset sets every body on the floor)."""
    champions, by_set = [], {}
    for name, entries in sets.items():
        by_set[name] = []
        for c in entries:
            r = results[keys[(name, c['label'], 'floor')]]
            row = {'set': name, 'label': c['label'], 'file': c['file'], 'voxels': int((np.asarray(c['grid']) != 0).sum()),
                   'lowest_layer': lowest_layer(c['grid']),
                   'evolved': c['evolved'], 'recorded_2013': c['recorded_2013'], 'score': r['score'],
                   'ratio': r['score'] / c['evolved'], 'blew_up': r['blew_up'], 'error': r['error'], 'moved': r['moved'],
                   'sunk': r['sunk'], 'time_step': r['time_step'], 'steps': r['steps'], 'consistent': r['consistent'],
                   'seconds': r['seconds']}
            if (name, c['label'], 'short') in keys:
                s = results[keys[(name, c['label'], 'short')]]
                row['quarter'] = {'score': s['score'], 'time_step': s['time_step'], 'blew_up': s['blew_up'],
                                  'sunk': s['sunk'], 'seconds': s['seconds']}
            if (name, c['label'], 'placed') in keys:
                p = results[keys[(name, c['label'], 'placed')]]
                row['placed'] = {'score': p['score'], 'ratio': p['score'] / c['evolved'], 'blew_up': p['blew_up'],
                                 'error': p['error'], 'moved': p['moved'], 'sunk': p['sunk'],
                                 'consistent': p['consistent'], 'seconds': p['seconds']}
            champions.append(row)
            by_set[name].append(row)
    enough = {name: rows for name, rows in by_set.items() if len(rows) >= 3}
    report = {'preset': preset,
              'sets': {name: summarise(rows, n_boot, seed) for name, rows in enough.items()},
              'comparisons': comparisons_of(by_set, arms, n_boot, seed), 'champions': champions,
              'step_check': step_check(champions),
              'diagnostic': against_diagnostic(by_set) if preset == PRESET else None,
              'floor_test': against_floor_test(by_set) if preset == FLOOR_PRESET else None,
              'off_the_floor': {name: int(sum('placed' in r for r in rows)) for name, rows in enough.items()}}
    if any(report['off_the_floor'].values()):
        placed = {name: as_placed(rows) for name, rows in by_set.items()}
        report['sets_as_placed'] = {name: summarise(placed[name], n_boot, seed) for name in enough}
        report['comparisons_as_placed'] = comparisons_of(placed, arms, n_boot, seed)
    return report


def plan(sets, params, code, with_step_check=True):
    """Every evaluation a report needs. -> (jobs, keys): jobs as evaluate_all takes them, keys
    {(set, label, which): key}. Each champion once under the preset as it is ('floor'); the first
    CHECK_CHAMPIONS of each set once more with a shorter time step ('short'); and, where the preset
    sets every body on the floor, each body that does not touch the bottom of the workspace once
    more from its height ('placed'). A preset that starts bodies where they are needs no second
    evaluation for that."""
    set_on_the_floor = params.get('start', 'floor') == 'floor'
    jobs, keys = [], {}
    for set_name, champions in sets.items():
        for i, c in enumerate(champions):
            height = lowest_layer(c['grid']) * params['voxel_size']
            variants = [('floor', params, 1.0, '')]
            if i < CHECK_CHAMPIONS and with_step_check:
                variants.append(('short', params, CHECK_FRACTION, ', short step'))
            if height > 0 and set_on_the_floor:
                variants.append(('placed', dict(params, initial_height=height), 1.0, ', started at its height'))
            for which, settings, fraction, suffix in variants:
                key = evaluation_key(c['grid'], settings, fraction, code)
                keys[(set_name, c['label'], which)] = key
                jobs.append((key, c['grid'], settings, fraction, f"{set_title(set_name)}, {c['label']}{suffix}"))
    return jobs, keys


def finish(report, name, out_dir):
    report['made'] = datetime.datetime.now().isoformat(timespec='minutes')
    report['code'] = aa.code_version()
    report['settings'] = {'n_boot': ps.N_BOOT, 'seed': ps.SEED, 'check_fraction': CHECK_FRACTION,
                          'check_champions': CHECK_CHAMPIONS}
    text = render(report)
    print(text)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + '.txt'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1, default=float)
    write_csv(os.path.join(out_dir, name + '_champions.csv'), report['champions'])
    print(f"\nWritten to {os.path.join(out_dir, name)}.txt, .json and _champions.csv")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument('--arms', nargs='+', choices=sorted(aa.ARMS), help='analysed arms whose champions are scored')
    what.add_argument('--rehearsal', metavar='PREFIX', help='runs that are not an arm: the start of their folder names')
    ap.add_argument('--generation', type=int, help='rehearsal only: the generation whose champions are scored')
    ap.add_argument('--preset', default=PRESET, choices=(PRESET, FLOOR_PRESET),
                    help=f'the engine settings (default {PRESET}, the outcome as fixed in section 9.4; {FLOOR_PRESET}: '
                         f'the settings of arm D, section 9.5)')
    ap.add_argument('--workers', type=int, default=6, help='evaluations side by side (default 6)')
    ap.add_argument('--no-step-check', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--results-dir', help=argparse.SUPPRESS)
    ap.add_argument('--out-dir', default=aa.OUT, help=argparse.SUPPRESS)
    ap.add_argument('--outcomes-dir', default=aa.OUTCOMES, help=argparse.SUPPRESS)
    ap.add_argument('--cache', default=CACHE, help=argparse.SUPPRESS)
    ap.add_argument('--deposit-dir', default=aa.DEPOSITED_ROBOTS, help=argparse.SUPPRESS)
    ap.add_argument('--replay', default=REPLAY, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')

    import run_tendon_evolution as runner
    # The engine must be the campaign's: the code of one of its tags. Every one of them computes
    # the same scores under a preset it has (PROTOCOL.md, sections 9.5 and 9.6), so evaluations
    # are kept under the name of the first tag that has the preset: campaign-v2 for --preset
    # cheney2013, campaign-v3 for the other.
    tag = search_arm.campaign_tag_of_code()
    if a.preset not in runner._PRESETS:
        print(f'This code has no preset {a.preset}. Nothing was computed.')
        return 2
    as_fixed = a.preset == PRESET
    stem = 'transfer' if as_fixed else 'transfer_floor2013'
    differs = None if tag else ('run_tendon_evolution.py or src/ are not those of a code tag of the campaign ('
                                + ', '.join(search_arm.ENGINE_TAGS) + ').')
    notes = []
    sets = {}
    if a.arms:
        if differs:
            print(f'{differs}\nThe transfer outcome is scored with the engine of the campaign. Nothing was computed.')
            return 2
        for arm in a.arms:
            champions = arm_champions(arm, a.results_dir, a.outcomes_dir)
            if champions is None:
                print(f"Arm {arm} has not been analysed: there is no report of it in {a.outcomes_dir}.\n"
                      f"An arm's champions are scored only after the arm's own analysis (PROTOCOL.md, section 9.4). "
                      f"Nothing was computed.")
                return 2
            sets[f'arm_{arm}'] = champions
            reference = f"deposit_{aa.ARMS[arm]['condition']}"
            if reference not in sets:
                sets[reference] = deposited_champions(aa.ARMS[arm]['condition'], a.deposit_dir, a.replay)
        title = (f"TRANSFER: the final champions of {', '.join('arm ' + x for x in a.arms)} and the deposited 2013 "
                 f"champions, scored in the MuJoCo engine{'' if as_fixed else ' under --preset ' + a.preset}.")
        name = stem
    else:
        if not a.generation:
            ap.error('--rehearsal needs --generation')
        if differs:
            notes.append(differs)
        champions = rehearsal_champions(a.rehearsal, a.generation, a.results_dir)
        if len(champions) < 3:
            print(f'Fewer than 3 runs named {a.rehearsal}<seed> have a champion at generation {a.generation}. '
                  f'Nothing was computed.')
            return 2
        sets[f'rehearsal_{a.rehearsal}'] = champions
        title = (f"REHEARSAL, not an arm: the generation-{a.generation} champions of the runs {a.rehearsal}<seed>, "
                 f"scored in the MuJoCo engine{'' if as_fixed else ' under --preset ' + a.preset}.")
        name = f'{stem}_rehearsal_{a.rehearsal}{a.generation}'

    params = worker_parameters(evaluator_arguments(preset=a.preset))
    code = search_arm.ENGINE_TAGS[0 if as_fixed else 1] if tag else aa.code_version()
    jobs, keys = plan(sets, params, code, not a.no_step_check)

    from run_tendon_evolution import _prevent_sleep
    awake = _prevent_sleep()
    try:
        results = evaluate_all(jobs, max(1, a.workers), a.cache)
    finally:
        awake()
    print()
    report = build_report(sets, results, keys, arms=a.arms or (), preset=a.preset)
    report['title'], report['notes'] = title, notes
    finish(report, name, a.out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
