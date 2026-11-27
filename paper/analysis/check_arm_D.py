"""Checks on arm D's result and the audit of its champions, made after the arm's analysis. Arm D
is this project's search in its own MuJoCo engine; its report is made by analyse_arm.py. This
script changes nothing in that report. It checks the report and the runs behind it, and makes
the audit the protocol asks of every champion (PROTOCOL.md, sections 6 and 9.7). Written on 27
November 2026, while the arm was running and before any score of it had been read.

usage, from the project folder:
    python paper/analysis/check_arm_D.py
        after the arm's analysis; refuses while there is no report of the arm in paper/outcomes/
    python paper/analysis/check_arm_D.py --rehearsal trialD_s --seeds 101-110 --generations 3
        the same on runs that are NOT an arm (trials), against their pilot report
        (analyse_arm.py --pilot trialD_s --generation 3 --search --with-body)

What it checks
  by hand     the scores again from the raw files, with readers of its own: each run from its
              generation files, the deposited runs from their archive; medians, ratios of
              medians and A12 against the report's
  runs        each run's record of itself (manifest.json): every start of it, with the same
              command and settings but for the seed, from code that is the arm's code tag in
              every file that computes a run, and with one linear-algebra thread; its
              generations all there. Which runs were started more than once, and what the
              launcher and the runs' own output say about why. How many bodies the engine
              refused (they score 0) and how many times a run stopped itself (section 9.6)
  champions   each run's champion as the analysis picks it, against the run's curve and against
              the run's own record of its best robot
  audit       section 9.7, point 2: each champion's stored body evaluated again in the MuJoCo
              engine with the evaluation of its run (is the recorded score reproduced?), once
              more with a quarter of the time step, and how deep its lowest voxel sank below the
              floor's surface. The audit is reported; nothing is dropped because of it

It writes, in results/analysis/: arm_D_checks.json and arm_D_champion_audit.csv (for a rehearsal:
rehearsal_<prefix>_checks.json and rehearsal_<prefix>_champion_audit.csv).
"""
import argparse
import csv
import glob
import json
import os
import pickle
import re
import statistics
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))

import transfer_scores as ts                                  # noqa: E402  (sets one thread before numpy is loaded)
import numpy as np                                            # noqa: E402
import search_arm                                             # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402

ARM = 'D'
RESULTS = os.path.join(ROOT, 'results')
OUT = os.path.join(RESULTS, 'analysis')
OUTCOMES = os.path.join(ROOT, 'paper', 'outcomes')
DEPOSIT = os.path.join(ROOT, 'research_reference', 'DRYAD_CheneyEtALL', 'softbots2013GenchampData.tgz')
CONDITION = '2013-01-16-10^3-noCost'
QUARTER = 0.25                  # the audit's shorter time step, as a fraction of the engine's
SAME = 1e-12                    # two numbers computed twice from the same data


def arm_spec():
    """Arm D as the launcher and the analysis have it."""
    import start_arm
    arm = search_arm.ARMS[ARM]
    seeds = start_arm.parse_seeds(arm['seeds'])
    return {'name': f'arm {ARM}', 'prefix': arm['tag'] + '_s', 'seeds': seeds, 'generations': arm['generations'],
            'checked_at': (300, 100), 'runner': list(arm['runner']), 'code_tag': arm['code'],
            'report': os.path.join(OUTCOMES, f'arm_{ARM}.json'), 'stem': f'arm_{ARM}', 'is_arm': True}


def rehearsal_spec(prefix, seeds, generations, report=None):
    arm = search_arm.ARMS[ARM]
    return {'name': f'rehearsal {prefix}', 'prefix': prefix, 'seeds': list(seeds), 'generations': int(generations),
            'checked_at': (int(generations),), 'runner': list(arm['runner']), 'code_tag': arm['code'],
            'report': report or os.path.join(OUT, f'pilot_{prefix}_gen{generations}.json'),
            'stem': f'rehearsal_{prefix}', 'is_arm': False}


def preset_of(spec):
    return spec['runner'][spec['runner'].index('--preset') + 1]


# --------------------------------------------------------------------------------------------
# by hand
# --------------------------------------------------------------------------------------------
def generation_files(folder):
    """{generation: the file's content}, by the number each file carries."""
    out = {}
    for path in glob.glob(os.path.join(folder, 'gen_*.json')):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        out[int(d['generation'])] = d
    return out


def column_two(lines):
    """The second column of a learning-curve file of the 2013 program: the champion's original
    fitness, one row per generation."""
    out = []
    for line in lines:
        p = line.split()
        if len(p) >= 2 and p[0][:1].isdigit():
            try:
                out.append(float(p[1]))
            except ValueError:
                pass
    return out


def deposited_curves(archive=DEPOSIT):
    out = []
    with tarfile.open(archive, 'r:gz') as t:
        for m in t:
            if m.isfile() and CONDITION + '/' in m.name and m.name.endswith('.txt'):
                rows = column_two(t.extractfile(m).read().decode('utf-8', 'replace').splitlines())
                if rows:
                    out.append(rows)
    return out


def a12(x, y):
    """Vargha-Delaney: how often a run of x beats a run of y, ties counted half."""
    return sum((a > b) + 0.5 * (a == b) for a in x for b in y) / (len(x) * len(y))


def by_hand(spec, report, results=RESULTS, deposit=None):
    generations = spec['generations']
    arm = {}
    for seed in spec['seeds']:
        files = generation_files(os.path.join(results, f"{spec['prefix']}{seed}"))
        if sorted(files) != list(range(1, generations + 1)):
            raise SystemExit(f'Seed {seed}: its generation files are not 1 to {generations}.')
        # the champion's score of a generation is the largest of that generation's scores
        arm[seed] = [max(files[g]['fitnesses']) for g in range(1, generations + 1)]
        if any(abs(arm[seed][g - 1] - files[g]['best_fitness']) > SAME for g in files):
            raise SystemExit(f'Seed {seed}: a generation file states a best score that is not its largest score.')
    deposit = deposited_curves() if deposit is None else deposit
    out = {'runs': {'arm': len(arm), 'deposited': len(deposit)}, 'generations': {}}
    agrees = True
    for g in spec['checked_at']:
        x = [max(arm[s][:g]) for s in spec['seeds']]
        y = [max(c[:g]) for c in deposit]
        mine = {'arm_median': statistics.median(x), 'deposited_median': statistics.median(y),
                'ratio_to_deposited': statistics.median(x) / statistics.median(y), 'a12_against_deposited': a12(x, y)}
        s = report['scores'][str(g)]
        theirs = {'arm_median': s['arm_median'], 'deposited_median': s['reference_median'],
                  'ratio_to_deposited': s['ratio_of_medians'], 'a12_against_deposited': s['a12']}
        mine['largest_difference_from_the_report'] = max(abs(mine[k] - theirs[k]) for k in theirs)
        agrees = agrees and mine['largest_difference_from_the_report'] <= 1e-9
        out['generations'][str(g)] = mine
    per_seed = {row['seed']: row['scores'] for row in report['per_seed']}
    out['seeds_whose_scores_agree_with_the_report'] = int(sum(
        s in per_seed and all(abs(max(arm[s][:g]) - per_seed[s][str(g)]) <= SAME for g in spec['checked_at'])
        for s in spec['seeds']))
    out['agrees_with_the_report'] = bool(agrees and out['seeds_whose_scores_agree_with_the_report'] == len(arm))
    return out, arm


# --------------------------------------------------------------------------------------------
# the runs' records
# --------------------------------------------------------------------------------------------
def expected_command(spec, seed, workers):
    return (['run_tendon_evolution.py'] + spec['runner']
            + ['--gen', str(spec['generations']), '--workers', str(workers), '--seed', str(seed),
               '--name', f"{spec['prefix']}{seed}"])


def same_code_as_tag(commit, tag, root=ROOT):
    """Are the files that compute a run the same in this commit as in the code tag?"""
    r = subprocess.run(['git', '-C', root, 'diff', '--quiet', commit, tag, '--'] + search_arm.RUN_DEFINING,
                       stdin=subprocess.DEVNULL, capture_output=True)
    return r.returncode == 0


def touches_the_code(modified):
    """Does a list of files that differed from the commit name a file that computes a run?"""
    return [m for m in modified if m.replace('\\', '/').startswith('src/') or m.endswith('run_tendon_evolution.py')]


def read_text(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError:
        return ''


def runs(spec, results=RESULTS, same_code=same_code_as_tag, preset_entries=None):
    """Each run's record of itself, and what the launcher recorded."""
    if preset_entries is None:
        import run_tendon_evolution as runner
        preset_entries = dict(runner._PRESETS[preset_of(spec)])
    generations = spec['generations']
    first, problems, starts, commits, workers_used = None, [], {}, {}, set()
    for seed in spec['seeds']:
        folder = os.path.join(results, f"{spec['prefix']}{seed}")
        with open(os.path.join(folder, 'manifest.json'), encoding='utf-8') as f:
            invocations = json.load(f)['invocations']
        starts[seed] = [i['started'] for i in invocations]
        for k, i in enumerate(invocations, start=1):
            which = f'seed {seed}, start {k}'
            workers = i['settings'].get('workers')
            workers_used.add(workers)
            if i['command'] != expected_command(spec, seed, workers):
                problems.append(f"{which}: command {i['command']}")
            if i['settings'].get('seed') != seed or i['settings'].get('name') != f"{spec['prefix']}{seed}":
                problems.append(f'{which}: its settings name another seed or run')
            if i.get('preset_applied') != preset_entries:
                problems.append(f'{which}: the preset was not applied as it is')
            if i.get('threads') != search_arm.ONE_THREAD:
                problems.append(f"{which}: thread settings {i.get('threads')}")
            commits.setdefault(i['git_commit'], None)
            if touches_the_code(i['git_modified']):
                problems.append(f"{which}: files that compute a run differed from the commit: {i['git_modified']}")
            same = {key: v for key, v in i['settings'].items() if key not in ('seed', 'name', 'workers')}
            rest = {key: i[key] for key in ('python', 'mujoco', 'numpy', 'platform')}
            if first is None:
                first = (same, rest)
            elif (same, rest) != first:
                problems.append(f"{which}: settings or libraries differ from the first start of seed {spec['seeds'][0]}")
        history = json.loads(read_text(os.path.join(folder, 'history.json')) or '{"best_fitness": []}')
        if len(history['best_fitness']) < generations:       # a continued run lists a generation twice
            problems.append(f"seed {seed}: history.json has {len(history['best_fitness'])} entries")
        for name in ('final_population.pkl', 'best_robot.pkl'):
            if not os.path.isfile(os.path.join(folder, name)):
                problems.append(f'seed {seed}: {name} is missing')
        if os.path.isfile(os.path.join(folder, 'checkpoint.pkl')):
            problems.append(f'seed {seed}: a checkpoint is left over')
    for commit in commits:
        commits[commit] = bool(same_code(commit, spec['code_tag']))
        if not commits[commit]:
            problems.append(f"commit {commit[:7]}: its run_tendon_evolution.py or src/ are not those of {spec['code_tag']}")

    stem = spec['prefix'][:-2]
    campaign = os.path.join(results, 'campaign')
    launches = json.loads(read_text(os.path.join(campaign, f'{stem}_launches.json')) or '[]')
    log = read_text(os.path.join(campaign, f'{stem}_launcher.log'))
    ended = []
    for line in log.splitlines():
        m = re.search(rf"{re.escape(spec['prefix'])}(\d+): ended with code (-?\d+) at generation (\d+)(.*?)(?:; continuing|$)", line)
        if m:
            ended.append({'seed': int(m.group(1)), 'code': int(m.group(2)), 'generation': int(m.group(3)),
                          'why': m.group(4).lstrip(': ').strip()})
    for seed, times in re.findall(rf"{re.escape(spec['prefix'])}(\d+): ended (\d+) times without finishing", log):
        problems.append(f'seed {seed}: the launcher gave it up after {times} starts')
    stood_still = [line.split('] ', 1)[-1].split(':')[0] for line in log.splitlines() if 'has recorded no new generation' in line]
    refused, stopped = {}, {}
    for seed in spec['seeds']:
        text = read_text(os.path.join(campaign, f'{stem}_logs', f"{spec['prefix']}{seed}.log"))
        said = re.findall(r'failed and scores 0: (.*)', text)
        if said:
            refused[seed] = {'bodies': len(said), 'reasons': sorted(set(s.strip() for s in said))}
        # one stop per start of the run whose output names the error (a run with worker processes
        # prints it twice: once as the worker raised it, once as the run did)
        attempts = re.split(r'^=== .* attempt \d+: .*$', text, flags=re.M)
        if 'EvaluationStopped' in text:
            stopped[seed] = sum('EvaluationStopped' in part for part in attempts)
    return {'runs': len(spec['seeds']), 'problems': problems,
            'first_start': min(s[0] for s in starts.values()), 'last_start': max(s[-1] for s in starts.values()),
            'started_more_than_once': {str(s): v for s, v in starts.items() if len(v) > 1},
            'code_commits': {c[:7]: same for c, same in commits.items()}, 'code_tag': spec['code_tag'],
            'evaluations_at_a_time': sorted(workers_used),
            'launches': len(launches), 'launcher_code': [launch['git'].get('describe') for launch in launches],
            'runs_that_ended_early_by_the_launcher_log': ended, 'runs_that_stood_still': stood_still,
            'bodies_the_engine_refused': {str(s): v for s, v in refused.items()},
            'runs_that_stopped_themselves': {str(s): v for s, v in stopped.items()}}


# --------------------------------------------------------------------------------------------
# the champions, and their audit
# --------------------------------------------------------------------------------------------
def champions(spec, report, curves, results=RESULTS):
    """Each run's champion, picked here as the analysis picks it (the highest fitness of the final
    population, the first on ties). -> (rows, {seed: the body as the run stored it})."""
    generations = spec['generations']
    reported = {row['seed']: row for row in report['per_seed']}
    rows, stored = [], {}
    for seed in spec['seeds']:
        folder = os.path.join(results, f"{spec['prefix']}{seed}")
        with open(os.path.join(folder, 'final_population.pkl'), 'rb') as f:
            population = pickle.load(f)
        with open(os.path.join(folder, 'best_robot.pkl'), 'rb') as f:
            best = pickle.load(f)
        fitnesses = [float(v) for v in population['fitnesses']]
        index = max(range(len(fitnesses)), key=lambda k: (fitnesses[k], -k))
        fitness = fitnesses[index]
        genome = np.asarray(population['genomes'][index])
        grid = c13.workspace_grid(genome)
        tied = [k for k, v in enumerate(fitnesses) if v == fitness]
        bodies = {'|'.join(c13.layer_rows(c13.workspace_grid(np.asarray(population['genomes'][k])))) for k in tied}
        c = (reported.get(seed) or {}).get('champion') or {}
        rows.append({
            'seed': seed, 'individual': index, 'fitness': fitness, 'voxels': int((grid != 0).sum()),
            'the_one_the_report_measured': bool(c and c['file'].endswith(f'individual {index}')
                                                and abs(c['original'] - fitness) <= SAME
                                                and c['body']['voxels'] == int((grid != 0).sum())),
            'is_the_last_point_of_the_curve': bool(abs(curves[seed][generations - 1] - fitness) <= SAME),
            'is_the_best_of_the_whole_run': bool(abs(max(curves[seed]) - fitness) <= SAME),
            'is_the_run_s_recorded_best_robot': bool(
                abs(float(best['fitness']) - fitness) <= SAME
                and np.array_equal(c13.workspace_grid(np.asarray(best['genome'])), grid)),
            'individuals_with_that_fitness': len(tied), 'different_bodies_among_them': len(bodies),
            'lowest_layer': int(np.argwhere(grid != 0)[:, 2].min()),
        })
        stored[seed] = genome
    return rows, stored


def audit(spec, rows, stored, workers=4, cache=None, evaluate_all=None, params=None):
    """Section 9.7, point 2. Each champion's stored body through the evaluation of its run, at the
    engine's time step and at a quarter of it."""
    evaluate_all = evaluate_all or ts.evaluate_all
    if params is None:
        params = ts.worker_parameters(ts.evaluator_arguments(early_stop=True, preset=preset_of(spec)))
    cache = cache or os.path.join(OUT, f"{spec['stem']}_audit_evaluations.json")
    jobs, keys = [], {}
    for row in rows:
        for which, fraction in (('again', 1.0), ('quarter', QUARTER)):
            key = ts.evaluation_key(stored[row['seed']], params, fraction, f"audit of {spec['prefix']}{row['seed']}")
            keys[(row['seed'], which)] = key
            jobs.append((key, stored[row['seed']], params, fraction,
                         f"{spec['name']}, seed {row['seed']}" + ('' if fraction == 1.0 else ', short step')))
    results = evaluate_all(jobs, max(1, workers), cache)
    out = []
    for row in rows:
        a, q = results[keys[(row['seed'], 'again')]], results[keys[(row['seed'], 'quarter')]]
        change = (q['score'] - a['score']) / a['score'] if a['score'] > 0 else float('nan')
        out.append({'seed': row['seed'], 'voxels': row['voxels'], 'lowest_layer': row['lowest_layer'],
                    'recorded': row['fitness'], 'again': a['score'], 'reproduced': bool(a['score'] == row['fitness']),
                    'difference': a['score'] - row['fitness'], 'blew_up': bool(a['blew_up']), 'error': a['error'],
                    'sank': a['sunk'], 'moved': a['moved'], 'time_step': a['time_step'], 'steps': a['steps'],
                    'quarter': q['score'], 'quarter_change': change, 'quarter_blew_up': bool(q['blew_up']),
                    'quarter_error': q['error'], 'quarter_sank': q['sunk'], 'quarter_time_step': q['time_step'],
                    'seconds': a['seconds'], 'quarter_seconds': q['seconds']})
    return out


def audit_summary(rows):
    changes = [abs(r['quarter_change']) for r in rows if r['quarter_change'] == r['quarter_change']]
    sank = [r['sank'] for r in rows if r['sank'] is not None]
    largest = max(rows, key=lambda r: abs(r['quarter_change']) if r['quarter_change'] == r['quarter_change'] else -1)
    return {'champions': len(rows), 'reproduced': int(sum(r['reproduced'] for r in rows)),
            'blew_up': int(sum(r['blew_up'] for r in rows)),
            'quarter_change_median': float(np.median(changes)) if changes else None,
            'quarter_change_over_10_percent': int(sum(c > 0.10 for c in changes)),
            'quarter_change_largest': largest['quarter_change'], 'quarter_change_largest_seed': largest['seed'],
            'quarter_blew_up': int(sum(r['quarter_blew_up'] for r in rows)),
            'sank': [float(v) for v in ts.ps.quartiles(sank)] if sank else None}


AUDIT_COLUMNS = ('seed', 'voxels', 'lowest_layer', 'recorded', 'again', 'reproduced', 'difference', 'blew_up', 'error', 'sank',
                 'moved_x', 'moved_y', 'moved_z', 'time_step', 'steps', 'quarter', 'quarter_change', 'quarter_blew_up',
                 'quarter_error', 'quarter_sank', 'quarter_time_step', 'seconds', 'quarter_seconds')


def write_audit(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(AUDIT_COLUMNS)
        for r in rows:
            moved = r['moved'] or ['', '', '']
            flat = dict(r, moved_x=moved[0], moved_y=moved[1], moved_z=moved[2])
            w.writerow(['' if flat[c] is None else flat[c] for c in AUDIT_COLUMNS])


# --------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    ap.add_argument('--rehearsal', metavar='PREFIX', help='runs that are not an arm: the start of their folder names')
    ap.add_argument('--seeds', help='rehearsal only: the seeds, e.g. 101-110')
    ap.add_argument('--generations', type=int, help='rehearsal only: the generations each run has')
    ap.add_argument('--report', help='rehearsal only: the pilot report to check against')
    ap.add_argument('--workers', type=int, default=4, help='evaluations side by side in the audit (default 4)')
    ap.add_argument('--results-dir', default=RESULTS, help=argparse.SUPPRESS)
    ap.add_argument('--out-dir', default=OUT, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')

    if a.rehearsal:
        if not a.seeds or not a.generations:
            ap.error('--rehearsal needs --seeds and --generations')
        import start_arm
        spec = rehearsal_spec(a.rehearsal, start_arm.parse_seeds(a.seeds), a.generations, a.report)
    else:
        spec = arm_spec()
    if not os.path.isfile(spec['report']):
        raise SystemExit(f"There is no report of {spec['name']} at {os.path.relpath(spec['report'], ROOT)} yet. "
                         f"These checks follow the analysis.")
    with open(spec['report'], encoding='utf-8') as f:
        report = json.load(f)
    title = f"{spec['name'].upper()}{'' if spec['is_arm'] else ' (not an arm of the campaign)'}"

    hand, curves = by_hand(spec, report, a.results_dir)
    print(f'{title}\n\nBY HAND, from the raw files')
    for g, v in hand['generations'].items():
        print(f"  generation {g:>4}: {spec['name']} {v['arm_median']:.4f}, deposited {v['deposited_median']:.4f}; ratio "
              f"{v['ratio_to_deposited']:.4f}; A12 {v['a12_against_deposited']:.4f}; largest difference from the report "
              f"{v['largest_difference_from_the_report']:.1e}")
    print(f"  seeds whose scores are the report's: {hand['seeds_whose_scores_agree_with_the_report']} of {hand['runs']['arm']}")

    records = runs(spec, a.results_dir)
    print('\nTHE RUNS')
    print(f"  {records['runs']} runs, started {records['first_start']} to {records['last_start']}; code "
          + ', '.join(f"{c} ({'the same as' if same else 'NOT'} {records['code_tag']} in what computes a run)"
                      for c, same in records['code_commits'].items())
          + f"; launched {records['launches']} time(s); evaluations at a time {records['evaluations_at_a_time']}")
    print(f"  problems: {records['problems'] or 'none'}")
    again = records['started_more_than_once']
    print(f"  runs started more than once: {', '.join(f'seed {s} ({len(v)} starts)' for s, v in again.items()) or 'none'}")
    for e in records['runs_that_ended_early_by_the_launcher_log']:
        print(f"    seed {e['seed']} ended with code {e['code']} at generation {e['generation']}"
              + (f": {e['why']}" if e['why'] else ''))
    print(f"  runs that stood still and were ended by the launcher: {records['runs_that_stood_still'] or 'none'}")
    refused = records['bodies_the_engine_refused']
    print(f"  bodies the engine refused (they score 0): {sum(v['bodies'] for v in refused.values())}"
          + ''.join(f"\n    seed {s}: {v['bodies']}, {v['reasons']}" for s, v in refused.items()))
    print(f"  times a run stopped itself because an evaluation failed (section 9.6): "
          f"{sum(records['runs_that_stopped_themselves'].values())}")

    rows, stored = champions(spec, report, curves, a.results_dir)
    print('\nTHE CHAMPIONS')
    for key in ('the_one_the_report_measured', 'is_the_last_point_of_the_curve', 'is_the_best_of_the_whole_run',
                'is_the_run_s_recorded_best_robot'):
        print(f"  {key.replace('_', ' ')}: {sum(r[key] for r in rows)} of {len(rows)}")
    print(f"  runs in which different bodies share the top fitness: {sum(r['different_bodies_among_them'] > 1 for r in rows)}")
    print(f"  champions that do not touch the bottom of the workspace: {sum(r['lowest_layer'] > 0 for r in rows)}")

    print('\nAUDIT (PROTOCOL.md, section 9.7, point 2): each champion evaluated again in the MuJoCo engine')
    os.makedirs(a.out_dir, exist_ok=True)
    audited = audit(spec, rows, stored, a.workers, os.path.join(a.out_dir, f"{spec['stem']}_audit_evaluations.json"))
    s = audit_summary(audited)
    print(f"\n  Reproduced score: {s['reproduced']} of {s['champions']} champions get their recorded score to the last digit.")
    for r in audited:
        if not r['reproduced']:
            print(f"    seed {r['seed']}: recorded {r['recorded']!r}, evaluated again {r['again']!r}")
    if s['quarter_change_median'] is not None:
        print(f"  A quarter of the time step: the score changes by {100 * s['quarter_change_median']:.1f}% in the median, by "
              f"more than 10% for {s['quarter_change_over_10_percent']} of {s['champions']}, and at most by "
              f"{100 * s['quarter_change_largest']:+.1f}% (seed {s['quarter_change_largest_seed']}).")
    print('    Under this preset the floor rule itself depends on the time step (section 9.5): it stops a voxel that the '
          'brake would stop within one step. The change is therefore not numerical error alone.')
    if s['sank']:
        print(f"  Floor penetration: the lowest voxel sank {s['sank'][0]:.2f} of a voxel below the floor's surface in the "
              f"median (quartiles {s['sank'][1]:.2f} to {s['sank'][2]:.2f}). The floor of this preset is the 2013 "
              f"simulator's spring.")
    print(f"  Simulations that blew up: {s['blew_up']} at the engine's time step, {s['quarter_blew_up']} at a quarter of it.")
    print(f"\n  {'seed':>4}  {'voxels':>6}  {'recorded':>9}  {'again':>9}  {'quarter step':>12}  {'change':>7}  {'sank':>5}  "
          f"{'sank, quarter':>13}")
    for r in audited:
        sank = '-' if r['sank'] is None else f"{r['sank']:.2f}"
        sank_q = '-' if r['quarter_sank'] is None else f"{r['quarter_sank']:.2f}"
        print(f"  {r['seed']:>4}  {r['voxels']:>6}  {r['recorded']:>9.4f}  {r['again']:>9.4f}  {r['quarter']:>12.4f}  "
              f"{100 * r['quarter_change']:>+6.1f}%  {sank:>5}  {sank_q:>13}"
              f"{'  BLEW UP' if r['blew_up'] else ''}{'  BLEW UP at a quarter' if r['quarter_blew_up'] else ''}")

    out = {'what': spec['name'], 'is_arm': spec['is_arm'], 'by_hand': hand, 'runs': records, 'champions': rows,
           'audit': {'summary': s, 'champions': audited, 'quarter': QUARTER, 'code': ts.aa.code_version()}}
    checks = os.path.join(a.out_dir, f"{spec['stem']}_checks.json")
    with open(checks, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, default=float)
    table = os.path.join(a.out_dir, f"{spec['stem']}_champion_audit.csv")
    write_audit(table, audited)
    print(f'\nWritten to {os.path.relpath(checks, ROOT)} and {os.path.relpath(table, ROOT)}')
    good = (hand['agrees_with_the_report'] and not records['problems']
            and all(r['the_one_the_report_measured'] and r['is_the_last_point_of_the_curve'] for r in rows)
            and s['reproduced'] == s['champions'])
    print('ALL CHECKS HOLD' if good else 'A CHECK DOES NOT HOLD: see above')
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
