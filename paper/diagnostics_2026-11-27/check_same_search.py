"""Is a run of the search the same run after the changes of 27 November 2026?

Short runs of the search's own command line are made twice: with the code tagged campaign-v3 as
that code would have run them (in a checkout of its own, with the libraries' default number of
threads), and with the code in this folder as the campaign's launcher starts a run (one
linear-algebra thread; MuJoCo's memory stated; a failed evaluation stops the run). They are
compared generation for generation, score for score, and in the bodies of the final population.

The runs (population 30, tournament selection, as in arms D and E). Their seed is 101, which is
the seed of no arm: arm D has seeds 1 to 10 and arms E1 to E3 have seeds 1 to 3, and no run of an
arm's seed is made before the arm is started.
    base_floor_s101      --preset cheney2013-floor, 5 generations, 3 evaluations at a time
    base_hard_s101       --preset cheney2013 (the hard floor, arm E3), 3 generations, 3 at a time
and, with the code in this folder only, against its own base_floor_s101:
    base_floor_s101_w1   the first 2 generations with one evaluation at a time: the search then
                         simulates in its own process, not in worker processes
    cont_floor_s101      the same run, but stopped twice while it runs and started again

usage, from the project folder:
    python paper/diagnostics_2026-11-27/check_same_search.py [--only-this-code | --only-old-code]
Runs that are complete already are not made again: they are kept in
results/diagnostics_2026-11-27/ (old_code and new_code). Written next to this file:
same_search.json.
--only-this-code makes the runs of the code in this folder, --only-old-code those of
campaign-v3, and neither compares anything yet: the two can then be made at the same time.
"""
import json
import os
import pickle
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))
import search_arm                                             # noqa: E402

OLD_TAG = 'campaign-v3'
OLD_ROOT = os.path.join(ROOT, '_worktrees', 'v3')            # a checkout of that tag (git worktree), made when needed
OLD_OUT = os.path.join(ROOT, 'results', 'diagnostics_2026-11-27', 'old_code')
NEW_OUT = os.path.join(ROOT, 'results', 'diagnostics_2026-11-27', 'new_code')
SEARCH = ['--no-age-pareto', '--pop', '30', '--seed', '101']      # not a seed of any arm
RUNS = (
    ('base_floor_s101', ['--preset', 'cheney2013-floor', '--gen', '5', '--workers', '3']),
    ('base_hard_s101', ['--preset', 'cheney2013', '--gen', '3', '--workers', '3']),
)
ONE_AT_A_TIME = ('base_floor_s101_w1', ['--preset', 'cheney2013-floor', '--gen', '2', '--workers', '1'], 'base_floor_s101')
STOPPED = ('cont_floor_s101', RUNS[0][1], 'base_floor_s101')  # name, settings, the run it must repeat


def git(root, *a):
    return subprocess.run(['git', '-C', root] + list(a), stdin=subprocess.DEVNULL, capture_output=True, text=True)


def old_checkout():
    """The folder that holds the code tagged campaign-v3, made if it is not there."""
    if not os.path.isdir(OLD_ROOT):
        made = git(ROOT, 'worktree', 'add', '--detach', OLD_ROOT, OLD_TAG)
        if made.returncode != 0:
            raise SystemExit(f'Could not check out {OLD_TAG}: {made.stderr.strip()}')
    if git(OLD_ROOT, 'diff', '--quiet', OLD_TAG, '--', *search_arm.RUN_DEFINING).returncode != 0:
        raise SystemExit(f'{OLD_ROOT} does not hold the code tagged {OLD_TAG}.')
    return OLD_ROOT


def generations_of(settings):
    return int(settings[settings.index('--gen') + 1])


def folder_of(out, name):
    return os.path.join(out, 'results', name)


def complete(out, name, generations):
    folder = folder_of(out, name)
    return (os.path.isfile(os.path.join(folder, 'final_population.pkl'))
            and os.path.isfile(os.path.join(folder, f'gen_{generations:03d}.json'))
            and not os.path.isfile(os.path.join(folder, 'checkpoint.pkl')))


def command(code_root, name, settings):
    return [sys.executable, os.path.join(code_root, 'run_tendon_evolution.py')] + settings + SEARCH + ['--name', name]


def default_threads():
    """The environment without any thread setting: how every run was started before 27 November."""
    return {k: v for k, v in os.environ.items() if k not in search_arm.ONE_THREAD}


def start(code_root, out, name, settings, environment):
    os.makedirs(out, exist_ok=True)
    log = open(os.path.join(out, name + '.log'), 'ab')
    return subprocess.Popen(command(code_root, name, settings), cwd=out, env=environment,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)


def read(out, name, generations):
    folder = folder_of(out, name)
    scores = []
    for g in range(1, generations + 1):
        with open(os.path.join(folder, f'gen_{g:03d}.json')) as f:
            scores.append([float(v) for v in json.load(f)['fitnesses']])
    with open(os.path.join(folder, 'final_population.pkl'), 'rb') as f:
        population = pickle.load(f)
    with open(os.path.join(folder, 'manifest.json')) as f:
        starts = json.load(f)['invocations']
    return {'scores': scores, 'bodies': [np.asarray(g) for g in population['genomes']],
            'final': [float(v) for v in population['fitnesses']],
            'starts': [{'started': s['started'], 'code': s['git_commit'], 'modified': s['git_modified'],
                        'threads': s.get('threads'), 'command': s['command']} for s in starts]}


def compare(a, b):
    """Two readings of the same run, generation for generation."""
    rows = []
    for g, (x, y) in enumerate(zip(a['scores'], b['scores']), 1):
        rows.append({'generation': g, 'scores': len(x), 'identical': int(sum(p == q for p, q in zip(x, y))),
                     'largest_difference': float(max(abs(p - q) for p, q in zip(x, y))),
                     'best': max(x), 'zero_scores': int(sum(v == 0.0 for v in x))})
    same_bodies = int(sum(np.array_equal(p, q) for p, q in zip(a['bodies'], b['bodies'])))
    return {'generations': rows,
            'scores': int(sum(r['scores'] for r in rows)), 'identical': int(sum(r['identical'] for r in rows)),
            'final_bodies': len(a['bodies']), 'final_bodies_identical': same_bodies,
            'final_scores_identical': a['final'] == b['final'],
            'voxels_of_final_bodies': [int(min((g != 0).sum() for g in a['bodies'])),
                                       int(max((g != 0).sum() for g in a['bodies']))]}


def main():
    new_environment = search_arm.run_environment()
    only_new = '--only-this-code' in sys.argv[1:]             # make this code's runs and compare nothing yet
    only_old = '--only-old-code' in sys.argv[1:]              # make the runs of campaign-v3 and compare nothing yet
    report = {'made': time.strftime('%Y-%m-%dT%H:%M'), 'old_code': OLD_TAG,
              'new_code': git(ROOT, 'describe', '--tags', '--always', '--dirty').stdout.strip(),
              'new_code_differs_from_old_in': git(ROOT, 'diff', '--stat', OLD_TAG, '--',
                                                  *search_arm.RUN_DEFINING).stdout.strip().splitlines(),
              'search': SEARCH, 'runs': {}}

    # the code of campaign-v3, one run after the other: each of its processes may ask for 3 GB
    for name, settings in RUNS:
        if not only_new and not complete(OLD_OUT, name, generations_of(settings)):
            print(f'{OLD_TAG}: {name} ...', flush=True)
            if start(old_checkout(), OLD_OUT, name, settings, default_threads()).wait() != 0:
                raise SystemExit(f'{name} did not finish under {OLD_TAG}; see {os.path.join(OLD_OUT, name)}.log')

    if only_old:
        return 0

    # the code in this folder, side by side
    going = {}
    for name, settings in RUNS + (ONE_AT_A_TIME[:2],):
        if not complete(NEW_OUT, name, generations_of(settings)):
            print(f'this code: {name} ...', flush=True)
            going[name] = start(ROOT, NEW_OUT, name, settings, new_environment)
    name, settings, _ = STOPPED
    stops = []
    if not complete(NEW_OUT, name, generations_of(settings)):
        print(f'this code: {name}, to be stopped twice ...', flush=True)
        for after in (2, 3):                      # stopped once generation 2 is recorded, and again after 3
            process = start(ROOT, NEW_OUT, name, settings, new_environment)
            while process.poll() is None and not os.path.isfile(
                    os.path.join(folder_of(NEW_OUT, name), f'gen_{after:03d}.json')):
                time.sleep(1)
            time.sleep(20)                        # well into the evaluation of the next generation
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                process.wait()
                stops.append(after)
        going[name] = start(ROOT, NEW_OUT, name, settings, new_environment)
        with open(os.path.join(NEW_OUT, name + '_stops.json'), 'w') as f:
            json.dump(stops, f)
    for name, process in going.items():
        if process.wait() != 0:
            raise SystemExit(f'{name} did not finish with this code; see {os.path.join(NEW_OUT, name)}.log')
    if only_new:
        return 0

    print()
    for name, settings in RUNS:
        n = generations_of(settings)
        old, new = read(OLD_OUT, name, n), read(NEW_OUT, name, n)
        row = compare(old, new)
        row.update(settings=settings, old_starts=old['starts'], new_starts=new['starts'])
        report['runs'][name] = row
        print(f"{name:18} {row['identical']} of {row['scores']} scores identical over {n} generations; "
              f"{row['final_bodies_identical']} of {row['final_bodies']} final bodies identical "
              f"({row['voxels_of_final_bodies'][0]} to {row['voxels_of_final_bodies'][1]} voxels); best "
              f"{row['generations'][-1]['best']:.4f}; threads {old['starts'][0]['threads']} -> {new['starts'][0]['threads']}")

    # one evaluation at a time against three at a time: the first two generations of the same run
    name, settings, twin = ONE_AT_A_TIME
    n = generations_of(settings)
    three, one = read(NEW_OUT, twin, n), read(NEW_OUT, name, n)
    same = sum(p == q for x, y in zip(three['scores'], one['scores']) for p, q in zip(x, y))
    report['one_at_a_time_against_three'] = {'generations': n, 'identical': int(same), 'scores': 30 * n,
                                             'starts': one['starts']}
    print(f'{name:18} one evaluation at a time against three at a time: {same} of {30 * n} scores identical')

    name, settings, twin = STOPPED
    n = generations_of(settings)
    cont, base = read(NEW_OUT, name, n), read(NEW_OUT, twin, n)
    row = compare(base, cont)
    stops_file = os.path.join(NEW_OUT, name + '_stops.json')
    row.update(starts=cont['starts'], stopped_after_generation=json.load(open(stops_file)) if os.path.exists(stops_file) else None)
    report['stopped_and_continued'] = row
    print(f"{name:18} started {len(cont['starts'])} times: {row['identical']} of {row['scores']} scores identical to "
          f"the uninterrupted run, {row['final_bodies_identical']} of {row['final_bodies']} final bodies identical")

    with open(os.path.join(HERE, 'same_search.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    whole = all(r['identical'] == r['scores'] and r['final_bodies_identical'] == r['final_bodies']
                and r['final_scores_identical'] for r in list(report['runs'].values()) + [row])
    whole = whole and report['one_at_a_time_against_three']['identical'] == report['one_at_a_time_against_three']['scores']
    print('\nEVERY RUN IS THE SAME RUN.' if whole else '\nNOT EVERY RUN IS THE SAME RUN.')
    return 0 if whole else 1


if __name__ == '__main__':
    sys.exit(main())
