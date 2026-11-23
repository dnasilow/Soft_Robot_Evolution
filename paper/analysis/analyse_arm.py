"""Analysis of one arm of the campaign against the deposited 2013 runs, as frozen in
paper/PROTOCOL.md (sections 4, 5 and 9). Developed and tested on pilot runs and on the deposited
2013 data, and committed before it was first run on an arm.

usage, from the project folder:
    python paper/analysis/analyse_arm.py --arm R
        the arm's report. Refuses unless every seed of the arm is complete.
    python paper/analysis/analyse_arm.py --pilot pilot10_P0_s --generation 10
        the same comparison at one generation for runs that are NOT an arm (pilots, trials)
    python paper/analysis/analyse_arm.py --what-can-the-criterion-show
        from the deposited runs alone: how often a perfect reproduction would meet the criterion

What an arm's report contains
  scores   the champion's original score, best so far, at generations 1000 (primary), 300 and
           100: medians, ratio of medians with its bootstrapped 95% interval, A12 with its
           interval, two-sided Mann-Whitney U, and the reproduction criterion (interval of the
           ratio inside 0.90-1.10) for the primary outcome
  body     each run's final champion measured with morphology_scorecard.body_metrics, the code
           used on the deposited robots: voxels, footprint, fill, muscle fraction (Mann-Whitney,
           A12) and two or more separate feet (Fisher's exact test), Holm-corrected within the arm
  per seed every seed, with its generations, scores and champion

The report is printed and written to results/analysis/ as text and as JSON.
Arms R and Rc (re-runs of the original program, collected by collect_2013_runs.sh) are covered;
the arms run with this project's own search need a reader of their own and are not yet here.
Not yet here either: the transfer scores of the champions in the other simulator.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tarfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))

import protocol_stats as ps                                   # noqa: E402
from morphology_scorecard import body_metrics                 # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402
from summarise_run import deposited_curves                    # noqa: E402

RERUNS = os.path.join(ROOT, 'results', 'rerun2013')
OUT = os.path.join(ROOT, 'results', 'analysis')
DEPOSITED_ROBOTS = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')

ARMS = {
    'R':  {'prefix': 'armR_P0_s', 'seeds': list(range(1, 36)), 'generations': 1000, 'condition': 'noCost',
           'title': 'the original 2013 search program and simulator, no cost'},
    'Rc': {'prefix': 'armRc_P2_s', 'seeds': list(range(1, 36)), 'generations': 1000, 'condition': 'costNumActuated',
           'title': 'the original 2013 search program and simulator, actuated-voxel cost'},
}
SCORE_GENERATIONS = (1000, 300, 100)        # the first is the primary outcome
REFERENCE_GENERATION = 1000                 # the deposit holds the robots of generation 1000 only
BODY_MEASURES = (('voxels', 'voxels', '.0f'), ('footprint', 'footprint (cells)', '.0f'),
                 ('fill', 'fill of bounding box', '.2f'), ('muscle', 'muscle fraction', '.2f'))
ROBOT = re.compile(r'--adjFit_([0-9.eE+-]+)--numFilled_(\d+)--origFit_([0-9.eE+-]+)_genome\.vxa$')


# --------------------------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------------------------
def read_curve(path):
    """A run's learning-curve file -> (champion's original fitness per generation, best so far).
    Column 2 of the file is the generation champion's original, unpenalised fitness."""
    raw = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            p = line.split()
            if len(p) < 2 or not p[0][:1].isdigit():
                continue
            try:
                raw.append(float(p[1]))
            except ValueError:
                continue
    raw = np.array(raw, float)
    return raw, (np.maximum.accumulate(raw) if len(raw) else raw)


def robot_info(name):
    """What a robot file's name records: adjusted and original fitness, and the count the program
    calls voxelPenalty ('filled'): all voxels without a cost, actuated voxels under the
    actuated-voxel cost. The body measures do not use it; they count from the body itself."""
    m = ROBOT.search(name)
    if not m:
        return None
    return {'file': name, 'adjusted': float(m.group(1)), 'filled': int(m.group(2)), 'original': float(m.group(3))}


def pick_champion(names):
    """The robot with the highest adjusted fitness; ties go to the first file name in sorted order."""
    infos = [i for i in (robot_info(n) for n in sorted(names)) if i]
    return max(infos, key=lambda i: i['adjusted']) if infos else None


def body_measures(robot_text):
    """The protocol's body measures of one robot file, or None for an empty body."""
    grid = c13.grid_from_rows([m.group(2) for m in c13.LAYER.finditer(robot_text)])
    if not (grid != 0).any():
        return None
    m = body_metrics(grid)
    return {'voxels': m['vox'], 'footprint': m['footprint'], 'fill': m['fill'],
            'muscle': (m['mats'][0] + m['mats'][1]) / m['vox'], 'feet': m['feet'],
            'two_feet': bool(m['feet'] >= 2)}


def reference_scores(condition):
    return deposited_curves(f'2013-01-16-10^3-{condition}/')


def reference_champions(condition, robots=DEPOSITED_ROBOTS):
    """Final champion of every deposited run, measured the same way as an arm's."""
    out = []
    for run in sorted(glob.glob(os.path.join(robots, f'2013-01-16-10^3-{condition}', 'run_*'))):
        champion = pick_champion(glob.glob(os.path.join(run, f'Gen_{REFERENCE_GENERATION:04d}', '*.vxa')))
        if champion is None:
            continue
        with open(champion['file'], encoding='utf-8', errors='replace') as f:
            champion['body'] = body_measures(f.read())
        champion['run'] = os.path.basename(run)
        champion['file'] = os.path.basename(champion['file'])
        out.append(champion)
    if not out:
        raise SystemExit(f'The deposited robot files are not in {robots}. Extract softbots2013Gen1000.tgz there.')
    return out


def load_run(folder, seed):
    run = {'seed': seed, 'folder': folder, 'generations': 0, 'raw': None, 'best': None,
           'finished': os.path.exists(os.path.join(folder, 'finished')), 'failed': None, 'champion': None}
    if os.path.exists(os.path.join(folder, 'failed')):
        with open(os.path.join(folder, 'failed')) as f:
            run['failed'] = f.read().strip() or 'failed'
    if os.path.isfile(os.path.join(folder, 'curve.txt')):
        run['raw'], run['best'] = read_curve(os.path.join(folder, 'curve.txt'))
        run['generations'] = int(len(run['raw']))
    return run


def load_champion(run, generation):
    """Adds the run's champion at that generation, read from its Gen_XXXX.tgz, if it is there."""
    path = os.path.join(run['folder'], f'Gen_{generation:04d}.tgz')
    if not os.path.isfile(path):
        return
    with tarfile.open(path, 'r:gz') as t:
        members = {m.name: m for m in t if m.isfile() and m.name.endswith('.vxa')}
        champion = pick_champion(members)
        if champion is None:
            return
        champion['body'] = body_measures(t.extractfile(members[champion['file']]).read().decode('utf-8', 'replace'))
        champion['population'] = len(members)
        champion['file'] = os.path.basename(champion['file'])
    run['champion'] = champion


def is_complete(run, generations):
    return (run['finished'] and not run['failed'] and run['generations'] == generations
            and os.path.isfile(os.path.join(run['folder'], f'Gen_{generations:04d}.tgz')))


# --------------------------------------------------------------------------------------------
# the analysis
# --------------------------------------------------------------------------------------------
def analyse(runs, condition, generations, primary, body_generation, n_boot=None, seed=None):
    """runs: the loaded runs that enter the statistics. Returns the report as a dictionary."""
    ref = reference_scores(condition)
    report = {'reference': f'the {len(ref)} deposited 2013 runs, condition {condition}', 'scores': {}}
    for g in generations:
        x = [float(r['best'][g - 1]) for r in runs if r['generations'] >= g]
        y = [float(c[g - 1]) for c in ref]
        if len(x) < 3:
            continue
        report['scores'][str(g)] = ps.compare(x, y, n_boot, seed)
    if str(primary) in report['scores']:
        s = report['scores'][str(primary)]
        report['primary'] = {
            'generation': primary, 'verdict': ps.verdict(s['ratio_interval']), 'window': list(ps.CRITERION),
            'attainability': ps.attainability([float(c[primary - 1]) for c in ref], s['n_arm'], seed=seed),
            'holm_range': list(ps.holm_range(s['p'])), 'holm_family': ps.FAMILY,
        }

    champions = [r['champion'] for r in runs if r.get('champion') and r['champion']['body']]
    if body_generation and len(champions) >= 3:
        ref_champions = [c for c in reference_champions(condition) if c['body']]
        body = {'generation': body_generation, 'reference_generation': REFERENCE_GENERATION,
                'n_arm': len(champions), 'n_reference': len(ref_champions), 'measures': {}}
        for key, _, _ in BODY_MEASURES:
            body['measures'][key] = ps.compare([c['body'][key] for c in champions],
                                               [c['body'][key] for c in ref_champions], n_boot, seed, with_ratio=False)
        body['measures']['two_feet'] = ps.two_proportions(
            sum(c['body']['two_feet'] for c in champions), len(champions),
            sum(c['body']['two_feet'] for c in ref_champions), len(ref_champions))
        keys = [k for k, _, _ in BODY_MEASURES] + ['two_feet']
        for key, adjusted in zip(keys, ps.holm([body['measures'][k]['p'] for k in keys])):
            body['measures'][key]['p_holm'] = adjusted
        report['body'] = body

    report['per_seed'] = []
    for r in runs:
        row = {'seed': r['seed'], 'generations': r['generations'],
               'scores': {str(g): float(r['best'][g - 1]) for g in generations if r['generations'] >= g}}
        c = r.get('champion')
        if c:
            row['champion'] = {k: c[k] for k in ('file', 'adjusted', 'original', 'filled', 'population')}
            row['champion']['body'] = c['body']
            if r['generations'] >= body_generation:
                row['champion']['curve_agrees'] = bool(abs(r['raw'][body_generation - 1] - c['original'])
                                                       <= 1e-4 * max(1.0, abs(c['original'])))
        report['per_seed'].append(row)
    return report


def what_the_criterion_can_show(seed=None):
    designs = (('R and A: 35 runs, generation 1000, no cost', 'noCost', 1000, 35),
               ('Rc: 35 runs, generation 1000, actuated cost', 'costNumActuated', 1000, 35),
               ('D: 10 runs, generation 300, no cost', 'noCost', 300, 10))
    rows = []
    for title, condition, g, n in designs:
        y = [float(c[g - 1]) for c in reference_scores(condition)]
        same = ps.bootstrap_interval(ps.ratio_of_medians, y, y, seed=seed)
        rows.append({'design': title, 'attainability': ps.attainability(y, n, seed=seed),
                     'reference_against_itself': list(same)})
    return rows


# --------------------------------------------------------------------------------------------
# the report as text
# --------------------------------------------------------------------------------------------
def med(m, lo, hi, fmt='.2f'):
    return f'{m:{fmt}} ({lo:{fmt}}-{hi:{fmt}})'


def pv(p):
    """A p-value: four decimals, or powers of ten once it is too small for that."""
    return f'{p:.4f}' if p >= 0.0001 else f'{p:.1e}'


def render(report):
    L = [report['title'], f"Reference: {report['reference']}.",
         f"Made {report['made']} with code {report['code']}; {report['settings']['n_boot']} bootstrap resamples, seed "
         f"{report['settings']['seed']}.", '']
    for note in report.get('notes', []):
        L.append(f'NOTE: {note}')
    if report.get('notes'):
        L.append('')

    L.append("SCORES: the champion's original score, best so far")
    L.append(f"{'generation':>10}  {'':9}  {'runs':>4}  {'arm median (quartiles)':>24}  {'deposited median (quartiles)':>28}  "
             f"{'ratio':>5}  {'95% interval':>12}  {'A12 (95% interval)':>19}  {'p':>7}")
    primary = report.get('primary', {})
    for g, s in report['scores'].items():
        role = '' if not primary else 'primary' if int(g) == primary['generation'] else 'secondary'
        L.append(f"{g:>10}  {role:9}  {s['n_arm']:>4}  {med(s['arm_median'], s['arm_q25'], s['arm_q75']):>24}  "
                 f"{med(s['reference_median'], s['reference_q25'], s['reference_q75']):>28}  "
                 f"{s['ratio_of_medians']:>5.2f}  {s['ratio_interval'][0]:>5.2f}-{s['ratio_interval'][1]:<5.2f}   "
                 f"{s['a12']:.2f} ({s['a12_interval'][0]:.2f}-{s['a12_interval'][1]:.2f})  {pv(s['p']):>8}")
    if primary:
        s = report['scores'][str(primary['generation'])]
        lo, hi = primary['window']
        L.append('')
        L.append(f"Primary outcome, generation {primary['generation']}: ratio of medians {s['ratio_of_medians']:.3f}, "
                 f"95% interval {s['ratio_interval'][0]:.3f} to {s['ratio_interval'][1]:.3f}.")
        L.append({
            'reproduces': f"  REPRODUCES: the interval lies inside {lo:.2f} to {hi:.2f}, the criterion fixed in advance.",
            'not distinguishable': f"  NOT DISTINGUISHABLE from the deposited runs (the interval contains 1), but reproduction "
                                   f"within the criterion is not shown (the interval is not inside {lo:.2f} to {hi:.2f}).",
            'differs': "  DIFFERS from the deposited runs: the interval excludes 1.",
        }[primary['verdict']])
        L.append(f"  What the criterion can show here: a perfect reproduction with {s['n_arm']} runs would meet it in "
                 f"{100 * primary['attainability']:.0f}% of cases (estimated from the deposited runs alone).")
        L.append(f"  Mann-Whitney p = {pv(s['p'])}. Holm over the {primary['holm_family']} primary comparisons is final only "
                 f"when all arms are in; until then it lies between {pv(primary['holm_range'][0])} and {pv(primary['holm_range'][1])}.")

    body = report.get('body')
    if body:
        L += ['', f"BODY of each run's champion at generation {body['generation']} ({body['n_arm']} runs) against the deposited "
                  f"champions of generation {body['reference_generation']} ({body['n_reference']} runs)"]
        L.append(f"{'measure':>22}  {'arm median (quartiles)':>24}  {'deposited median (quartiles)':>28}  "
                 f"{'A12 (95% interval)':>19}  {'p':>7}  {'p (Holm)':>8}")
        for key, label, fmt in BODY_MEASURES:
            m = body['measures'][key]
            L.append(f"{label:>22}  {med(m['arm_median'], m['arm_q25'], m['arm_q75'], fmt):>24}  "
                     f"{med(m['reference_median'], m['reference_q25'], m['reference_q75'], fmt):>28}  "
                     f"{m['a12']:.2f} ({m['a12_interval'][0]:.2f}-{m['a12_interval'][1]:.2f})  {pv(m['p']):>8}  {pv(m['p_holm']):>8}")
        f2 = body['measures']['two_feet']
        L.append(f"{'two or more feet':>22}  {f2['arm_yes']:>17} of {f2['n_arm']:<4}  {f2['reference_yes']:>21} of {f2['n_reference']:<4}  "
                 f"{'(Fisher exact)':>19}  {pv(f2['p']):>8}  {pv(f2['p_holm']):>8}")

    L += ['', 'PER SEED']
    gens = list(report['scores'])
    L.append(f"{'seed':>4}  {'generations':>11}  " + '  '.join(f"{'score@' + g:>10}" for g in gens)
             + f"  {'voxels':>6}  {'footprint':>9}  {'fill':>5}  {'muscle':>6}  {'feet':>4}  note")
    for row in report['per_seed']:
        c = row.get('champion')
        b = c['body'] if c and c['body'] else None
        note = '' if not c or c.get('curve_agrees', True) else 'champion file and curve disagree'
        L.append(f"{row['seed']:>4}  {row['generations']:>11}  "
                 + '  '.join(f"{row['scores'][g]:>10.4f}" if g in row['scores'] else f"{'-':>10}" for g in gens)
                 + (f"  {b['voxels']:>6}  {b['footprint']:>9}  {b['fill']:>5.2f}  {b['muscle']:>6.2f}  {b['feet']:>4}  {note}"
                    if b else f"  {'-':>6}  {'-':>9}  {'-':>5}  {'-':>6}  {'-':>4}  {note}"))
    for row in report.get('left_out', []):
        L.append(f"{row['seed']:>4}  {row['generations']:>11}  LEFT OUT of the statistics: {row['why']}")
    return '\n'.join(L)


def code_version():
    try:
        return subprocess.run(['git', '-C', ROOT, 'describe', '--tags', '--always', '--dirty'], capture_output=True,
                              text=True, timeout=60).stdout.strip() or 'unknown'
    except Exception:                                        # noqa: BLE001
        return 'unknown'


def finish(report, name, out_dir):
    report['made'] = datetime.datetime.now().isoformat(timespec='minutes')
    report['code'] = code_version()
    report['settings'] = {'n_boot': ps.N_BOOT, 'seed': ps.SEED, 'criterion': list(ps.CRITERION)}
    text = render(report)
    print(text)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + '.txt'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1, default=float)
    print(f"\nWritten to {os.path.join(out_dir, name)}.txt and .json")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n\n', 1)[1])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument('--arm', choices=sorted(ARMS))
    what.add_argument('--pilot', metavar='PREFIX', help='runs that are not an arm: the start of their folder names')
    what.add_argument('--what-can-the-criterion-show', action='store_true')
    ap.add_argument('--failed-seeds', default='', help='arm only: seeds that failed for good (e.g. 17,23); they are '
                                                       'reported and left out of the statistics')
    ap.add_argument('--generation', type=int, help='pilot only: the generation to compare at')
    ap.add_argument('--condition', default='noCost', choices=['noCost', 'costNumActuated'], help='pilot only')
    ap.add_argument('--with-body', action='store_true', help='pilot only: also measure the champions of that generation')
    ap.add_argument('--results-dir', default=RERUNS, help=argparse.SUPPRESS)
    ap.add_argument('--out-dir', default=OUT, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')

    if a.what_can_the_criterion_show:
        print('How often a perfect reproduction would meet the criterion (interval of the ratio of medians inside '
              f'{ps.CRITERION[0]:.2f} to {ps.CRITERION[1]:.2f}),\nestimated from the deposited 2013 runs alone:')
        for row in what_the_criterion_can_show():
            print(f"  {row['design']:<46} {100 * row['attainability']:>4.0f}%   (deposit against itself: interval "
                  f"{row['reference_against_itself'][0]:.2f} to {row['reference_against_itself'][1]:.2f})")
        return 0

    if a.arm:
        arm = ARMS[a.arm]
        g = arm['generations']
        runs = {s: load_run(os.path.join(a.results_dir, f"{arm['prefix']}{s}"), s) for s in arm['seeds']}
        try:
            given_up = sorted({int(s) for s in a.failed_seeds.split(',') if s.strip()})
        except ValueError:
            ap.error('--failed-seeds takes seed numbers separated by commas')
        if any(s not in runs for s in given_up) or any(is_complete(runs[s], g) for s in given_up):
            ap.error('--failed-seeds names a seed that is not in the arm or that is complete')
        waiting = [s for s in arm['seeds'] if s not in given_up and not is_complete(runs[s], g)]
        if waiting:
            print(f"Arm {a.arm} is not complete: seeds {waiting} have not finished with {g} generations.\n"
                  f"An arm is analysed only as a whole (PROTOCOL.md, section 9). Nothing was computed.")
            return 2
        used = [runs[s] for s in arm['seeds'] if s not in given_up]
        for r in used:
            load_champion(r, g)
        report = analyse(used, arm['condition'], SCORE_GENERATIONS, SCORE_GENERATIONS[0], g)
        report['title'] = (f"ARM {a.arm}: {arm['title']}. Seeds {arm['seeds'][0]} to {arm['seeds'][-1]}, {g} generations; "
                           f"{len(used)} of {len(arm['seeds'])} runs in the statistics.")
        report['left_out'] = [{'seed': s, 'generations': runs[s]['generations'],
                               'why': f"failed for good ({runs[s]['failed'] or 'unfinished'})"} for s in given_up]
        report['notes'] = ([f"{len(given_up)} seed(s) failed for good and are left out of the statistics: {given_up}."]
                           if given_up else [])
        finish(report, f'arm_{a.arm}', a.out_dir)
        return 0

    if not a.generation:
        ap.error('--pilot needs --generation')
    found = {}
    for d in glob.glob(os.path.join(a.results_dir, a.pilot + '*')):
        tail = os.path.basename(d)[len(a.pilot):]
        if os.path.isdir(d) and tail.isdigit():
            found[int(tail)] = load_run(d, int(tail))
    used = [found[s] for s in sorted(found) if found[s]['generations'] >= a.generation]
    if len(used) < 3:
        print(f"Fewer than 3 runs named {a.pilot}<seed> have reached generation {a.generation}. Nothing was computed.")
        return 2
    if a.with_body:
        for r in used:
            load_champion(r, a.generation)
    report = analyse(used, a.condition, (a.generation,), a.generation, a.generation if a.with_body else None)
    report.pop('primary', None)
    report['title'] = (f"PILOT, not an arm of the campaign: runs {a.pilot}<seed>, {len(used)} runs at generation "
                       f"{a.generation}.")
    report['notes'] = ['A pilot. The reproduction criterion applies to complete arms only.']
    if a.with_body and a.generation != REFERENCE_GENERATION:
        report['notes'].append(f'The body table sets generation {a.generation} against the deposited generation '
                               f'{REFERENCE_GENERATION}: a test of the code, not a comparison.')
    finish(report, f'pilot_{a.pilot}_gen{a.generation}', a.out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
