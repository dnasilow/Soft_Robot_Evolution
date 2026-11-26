"""Checks on arm A's result, made after its analysis. Arm A is this project's search in the
original 2013 simulator; its report is made by analyse_arm.py. This script changes nothing in
that report. It checks the report and the runs behind it, and makes the audit the protocol asks
of every champion (PROTOCOL.md, section 6): each champion simulated once more.

usage, from the project folder, after the arm's analysis:
    python paper/analysis/check_arm_A.py

What it checks
  by hand     the scores again from the raw files, with readers of its own: each run from its
              generation files, the deposited runs from their archive, arm R from its curve
              files; medians, ratios of medians and A12 against the report's
  runs        each run's record of itself (manifest.json): started once, the same command and
              settings but for the seed, the same code; its 1000 generations all there; and the
              launcher's record: the simulator and the settings template by their checksums,
              against those arms R and Rc ran with and against what is on this machine now
  pilot       seed 1 against the pilot of 21 November (pilot_vx2013_s1: 100 generations, 30
              simulations side by side, the code before the correction of section 9.3): every
              score of every generation
  champions   each run's champion as the analysis picks it, against the run's curve and against
              the run's own record of its best robot
  audit       each champion written to a robot file as the search wrote it and simulated again
              in the 2013 simulator, by the replay script that audited arms R and Rc

It writes, in results/analysis/: arm_A_checks.json, arm_A_champion_audit.csv, and the champions'
robot files in arm_A_champions/ (the video of the arm reads the same bodies).
"""
import csv
import glob
import hashlib
import json
import os
import pickle
import re
import shutil
import statistics
import subprocess
import sys
import tarfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))

from src.evolution import cheney2013 as c13                           # noqa: E402
from src.evolution.voxelyze2013_evaluator import TEMPLATE             # noqa: E402

ARM, PREFIX, SEEDS, GENERATIONS = 'A', 'armA_s', range(1, 36), 1000
CHECKED_AT = (1000, 300, 100)
RESULTS = os.path.join(ROOT, 'results')
OUT = os.path.join(RESULTS, 'analysis')
REPORT = os.path.join(ROOT, 'paper', 'outcomes', f'arm_{ARM}.json')
DEPOSIT = os.path.join(ROOT, 'research_reference', 'DRYAD_CheneyEtALL', 'softbots2013GenchampData.tgz')
ARM_R = os.path.join(RESULTS, 'rerun2013', 'armR_P0_s{seed}', 'curve.txt')
PILOT = os.path.join(RESULTS, 'pilot_vx2013_s1')
LAUNCHES = os.path.join(RESULTS, 'campaign', 'armA_launches.json')
EARLIER_LAUNCHES = {'R': os.path.join(RESULTS, 'rerun2013', 'armR_P0_launches.json'),
                    'Rc': os.path.join(RESULTS, 'rerun2013', 'armRc_P2_launches.json')}
CHAMPIONS = os.path.join(OUT, f'arm_{ARM}_champions')
AUDIT = os.path.join(OUT, f'arm_{ARM}_champion_audit.csv')
REPLAY_SCRIPT = os.path.join(ROOT, 'paper', 'reference_2013', 'replay_in_2013_simulator.sh')
SAME = 1e-12                    # two numbers computed twice from the same data


def wsl_path(path):
    p = os.path.abspath(path)
    return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')


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


def best_so_far(values, g):
    return max(values[:g])


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


def a12(x, y):
    """Vargha-Delaney: how often a run of x beats a run of y, ties counted half."""
    wins = sum((a > b) + 0.5 * (a == b) for a in x for b in y)
    return wins / (len(x) * len(y))


def by_hand(report):
    arm = {}
    for seed in SEEDS:
        files = generation_files(os.path.join(RESULTS, f'{PREFIX}{seed}'))
        if sorted(files) != list(range(1, GENERATIONS + 1)):
            raise SystemExit(f'Seed {seed}: its generation files are not 1 to {GENERATIONS}.')
        # the champion's score of a generation is the largest of that generation's 30 scores
        arm[seed] = [max(files[g]['fitnesses']) for g in range(1, GENERATIONS + 1)]
        if any(abs(arm[seed][g - 1] - files[g]['best_fitness']) > SAME for g in files):
            raise SystemExit(f'Seed {seed}: a generation file states a best score that is not its largest score.')
    deposit = []
    with tarfile.open(DEPOSIT, 'r:gz') as t:
        for m in t:
            if m.isfile() and '2013-01-16-10^3-noCost/' in m.name and m.name.endswith('.txt'):
                rows = column_two(t.extractfile(m).read().decode('utf-8', 'replace').splitlines())
                if rows:
                    deposit.append(rows)
    arm_r = []
    for seed in SEEDS:
        with open(ARM_R.format(seed=seed), encoding='utf-8', errors='replace') as f:
            arm_r.append(column_two(f))
    out = {'runs': {'arm_A': len(arm), 'deposited': len(deposit), 'arm_R': len(arm_r)}, 'generations': {}}
    agrees = True
    for g in CHECKED_AT:
        x = [best_so_far(arm[s], g) for s in SEEDS]
        y = [best_so_far(c, g) for c in deposit]
        r = [best_so_far(c, g) for c in arm_r]
        mine = {'arm_median': statistics.median(x), 'deposited_median': statistics.median(y),
                'arm_R_median': statistics.median(r), 'ratio_to_deposited': statistics.median(x) / statistics.median(y),
                'ratio_to_arm_R': statistics.median(x) / statistics.median(r),
                'a12_against_deposited': a12(x, y), 'a12_against_arm_R': a12(x, r)}
        s, t = report['scores'][str(g)], report['against']['scores'][str(g)]
        theirs = {'arm_median': s['arm_median'], 'deposited_median': s['reference_median'],
                  'arm_R_median': t['reference_median'], 'ratio_to_deposited': s['ratio_of_medians'],
                  'ratio_to_arm_R': t['ratio_of_medians'], 'a12_against_deposited': s['a12'],
                  'a12_against_arm_R': t['a12']}
        mine['largest_difference_from_the_report'] = max(abs(mine[k] - theirs[k]) for k in theirs)
        agrees = agrees and mine['largest_difference_from_the_report'] <= 1e-9
        out['generations'][str(g)] = mine
    per_seed = {row['seed']: row['scores'] for row in report['per_seed']}
    out['seeds_whose_scores_agree_with_the_report'] = int(sum(
        all(abs(best_so_far(arm[s], g) - per_seed[s][str(g)]) <= SAME for g in CHECKED_AT) for s in SEEDS))
    out['agrees_with_the_report'] = bool(agrees and out['seeds_whose_scores_agree_with_the_report'] == len(arm))
    return out, arm


# --------------------------------------------------------------------------------------------
# the runs' records
# --------------------------------------------------------------------------------------------
def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def runs():
    first, problems, started = None, [], []
    for seed in SEEDS:
        folder = os.path.join(RESULTS, f'{PREFIX}{seed}')
        with open(os.path.join(folder, 'manifest.json'), encoding='utf-8') as f:
            invocations = json.load(f)['invocations']
        if len(invocations) != 1:
            problems.append(f'seed {seed}: started {len(invocations)} times')
        i = invocations[0]
        started.append(i['started'])
        expected = ['run_tendon_evolution.py', '--simulator', 'voxelyze2013', '--no-age-pareto', '--pop', '30', '--gen',
                    str(GENERATIONS), '--workers', '1', '--seed', str(seed), '--name', f'{PREFIX}{seed}']
        if i['command'] != expected:
            problems.append(f"seed {seed}: command {i['command']}")
        same = {k: v for k, v in i['settings'].items() if k not in ('seed', 'name')}
        rest = {k: i[k] for k in ('git_commit', 'git_modified', 'python', 'mujoco', 'numpy', 'platform', 'preset_applied')}
        if i['settings'].get('seed') != seed or i['settings'].get('name') != f'{PREFIX}{seed}':
            problems.append(f'seed {seed}: its settings name another seed or run')
        if first is None:
            first = (same, rest)
        elif (same, rest) != first:
            problems.append(f'seed {seed}: settings or code differ from seed {SEEDS[0]}')
        with open(os.path.join(folder, 'history.json'), encoding='utf-8') as f:
            history = json.load(f)
        if len(history['best_fitness']) != GENERATIONS:       # a continued run lists a generation twice
            problems.append(f"seed {seed}: history.json has {len(history['best_fitness'])} entries")
        for name in ('final_population.pkl', 'best_robot.pkl'):
            if not os.path.isfile(os.path.join(folder, name)):
                problems.append(f'seed {seed}: {name} is missing')
        if os.path.isfile(os.path.join(folder, 'checkpoint.pkl')):
            problems.append(f'seed {seed}: a checkpoint is left over')

    with open(LAUNCHES, encoding='utf-8') as f:
        launches = json.load(f)
    record = launches[-1]
    earlier = {}
    for arm, path in EARLIER_LAUNCHES.items():
        with open(path, encoding='utf-8') as f:
            earlier[arm] = sorted({launch['programs']['sha256']['voxelize'] for launch in json.load(f)})
    import start_arm as core
    now = core.programs()['sha256']['voxelize']
    out = {'runs': len(SEEDS), 'problems': problems, 'first_start': min(started), 'last_start': max(started),
           'code_commit': first[1]['git_commit'], 'files_that_differed_from_the_commit': first[1]['git_modified'],
           'code_described_by_the_launcher': record['git']['describe'], 'launches': len(launches),
           'simulator_sha256': record['simulator_sha256'], 'simulator_of_arms_R_and_Rc': earlier,
           'simulator_on_this_machine_now': now, 'template_sha256': record['template_sha256'],
           'template_now': sha256(TEMPLATE)}
    out['same_simulator'] = bool(all(v == [record['simulator_sha256']] for v in earlier.values())
                                 and now == record['simulator_sha256'])
    out['same_template'] = bool(out['template_now'] == record['template_sha256'])
    return out


# --------------------------------------------------------------------------------------------
# seed 1 against the pilot
# --------------------------------------------------------------------------------------------
def pilot():
    mine = generation_files(os.path.join(RESULTS, f'{PREFIX}1'))
    theirs = generation_files(PILOT)
    with open(os.path.join(PILOT, 'manifest.json'), encoding='utf-8') as f:
        command = json.load(f)['invocations'][0]['command']
    identical = [g for g in sorted(theirs) if mine[g]['fitnesses'] == theirs[g]['fitnesses']]
    return {'pilot': os.path.basename(PILOT), 'pilot_command': command, 'generations_in_the_pilot': len(theirs),
            'generations_with_all_scores_identical': len(identical), 'scores_compared': 30 * len(theirs),
            'identical': bool(len(identical) == len(theirs) and len(theirs) > 0)}


# --------------------------------------------------------------------------------------------
# the champions, and their audit
# --------------------------------------------------------------------------------------------
def champions(report, curves):
    """Each run's champion, picked here as the analysis picks it (the highest fitness of the final
    population, the first on ties), written to a robot file exactly as the search wrote it."""
    with open(TEMPLATE, encoding='iso-8859-1') as f:
        template = f.read()
    shutil.rmtree(CHAMPIONS, ignore_errors=True)
    rows = []
    for seed, reported in zip(SEEDS, report['per_seed']):
        folder = os.path.join(RESULTS, f'{PREFIX}{seed}')
        with open(os.path.join(folder, 'final_population.pkl'), 'rb') as f:
            population = pickle.load(f)
        with open(os.path.join(folder, 'best_robot.pkl'), 'rb') as f:
            best = pickle.load(f)
        fitnesses = [float(v) for v in population['fitnesses']]
        index = max(range(len(fitnesses)), key=lambda k: (fitnesses[k], -k))
        fitness = fitnesses[index]
        grid = c13.workspace_grid(np.asarray(population['genomes'][index]))
        tied = [k for k, v in enumerate(fitnesses) if v == fitness]
        bodies = {'|'.join(c13.layer_rows(c13.workspace_grid(np.asarray(population['genomes'][k])))) for k in tied}
        name = (f'{PREFIX}{seed}--Gen_{GENERATIONS:04d}--Ind_{index:02d}--adjFit_{fitness:.8f}--numFilled_'
                f'{int((grid != 0).sum()):04d}--origFit_{fitness:.8f}_genome.vxa')
        path = os.path.join(CHAMPIONS, f'arm{ARM}', f'{PREFIX}{seed}', f'Gen_{GENERATIONS:04d}', name)
        os.makedirs(os.path.dirname(path))
        with open(path, 'w', encoding='iso-8859-1', newline='\n') as f:
            f.write(c13.fill_template(template, grid))
        c = reported['champion']
        rows.append({
            'seed': seed, 'individual': index, 'fitness': fitness, 'voxels': int((grid != 0).sum()), 'file': name,
            'the_one_the_report_measured': bool(reported['seed'] == seed and c['file'].endswith(f'individual {index}')
                                                and abs(c['original'] - fitness) <= SAME
                                                and c['body']['voxels'] == int((grid != 0).sum())),
            'is_the_last_point_of_the_curve': bool(abs(curves[seed][GENERATIONS - 1] - fitness) <= SAME),
            'is_the_best_of_the_whole_run': bool(abs(max(curves[seed]) - fitness) <= SAME),
            'is_the_run_s_recorded_best_robot': bool(
                abs(float(best['fitness']) - fitness) <= SAME
                and np.array_equal(c13.workspace_grid(np.asarray(best['genome'])), grid)),
            'individuals_with_that_fitness': len(tied), 'different_bodies_among_them': len(bodies),
            'lowest_layer': int(np.argwhere(grid != 0)[:, 2].min()),
        })
    return rows


def audit(rows):
    """Every champion's robot file simulated again in the 2013 simulator by the replay script."""
    name = f'arm_{ARM}_champion_audit.csv'
    written = os.path.join(ROOT, 'paper', 'reference_2013', name)
    command = (f"tr -d '\\r' < {wsl_path(REPLAY_SCRIPT)} | SRC={wsl_path(CHAMPIONS)} NAME={name} bash")
    r = subprocess.run(['wsl', '-d', os.environ.get('VOXELYZE2013_WSL_DISTRO', 'Ubuntu'), '--', 'bash', '-c', command],
                       capture_output=True, timeout=3600)
    if r.returncode != 0 or not os.path.isfile(written):
        raise SystemExit(f"The replay did not run: {r.stdout.decode('utf-8', 'replace')[-300:]} "
                         f"{r.stderr.decode('utf-8', 'replace')[-300:]}")
    os.replace(written, AUDIT)
    with open(AUDIT, newline='', encoding='utf-8') as f:
        replayed = {row['file']: row for row in csv.DictReader(f)}
    out = []
    for row in rows:
        again = replayed.get(row['file'])
        score = c13.fitness_from_result(None if again is None or again['final_com_dist_m'] == 'NA'
                                        else again['final_com_dist_m'])
        out.append({'seed': row['seed'], 'recorded': row['fitness'], 'simulated_again': score,
                    'distance_as_printed': None if again is None else again['final_com_dist_m'],
                    'identical': bool(abs(score - row['fitness']) <= SAME)})
    return out


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    if not os.path.isfile(REPORT):
        raise SystemExit(f'There is no report of arm {ARM} in paper/outcomes yet. These checks follow its analysis.')
    with open(REPORT, encoding='utf-8') as f:
        report = json.load(f)

    hand, curves = by_hand(report)
    print('BY HAND, from the raw files')
    for g, v in hand['generations'].items():
        print(f"  generation {g:>4}: arm A {v['arm_median']:.4f}, deposited {v['deposited_median']:.4f}, arm R "
              f"{v['arm_R_median']:.4f}; ratios {v['ratio_to_deposited']:.4f} and {v['ratio_to_arm_R']:.4f}; A12 "
              f"{v['a12_against_deposited']:.4f} and {v['a12_against_arm_R']:.4f}; largest difference from the report "
              f"{v['largest_difference_from_the_report']:.1e}")
    print(f"  seeds whose three scores are the report's: {hand['seeds_whose_scores_agree_with_the_report']} of "
          f"{hand['runs']['arm_A']}")

    records = runs()
    print('\nTHE RUNS')
    print(f"  {records['runs']} runs, started {records['first_start']} to {records['last_start']}, code "
          f"{records['code_commit'][:7]} ({records['code_described_by_the_launcher']}), launched {records['launches']} time(s)")
    print(f"  problems: {records['problems'] or 'none'}")
    print(f"  the simulator is the one of arms R and Rc and the one on this machine now: {records['same_simulator']} "
          f"({records['simulator_sha256'][:12]}); the settings template is unchanged: {records['same_template']}")

    with_pilot = pilot()
    print(f"\nSEED 1 AGAINST THE PILOT ({with_pilot['pilot']}): {with_pilot['generations_with_all_scores_identical']} of "
          f"{with_pilot['generations_in_the_pilot']} generations identical in all 30 scores")

    rows = champions(report, curves)
    print('\nTHE CHAMPIONS')
    for key in ('the_one_the_report_measured', 'is_the_last_point_of_the_curve', 'is_the_best_of_the_whole_run',
                'is_the_run_s_recorded_best_robot'):
        print(f"  {key.replace('_', ' ')}: {sum(r[key] for r in rows)} of {len(rows)}")
    print(f"  runs in which different bodies share the top fitness: {sum(r['different_bodies_among_them'] > 1 for r in rows)}")
    print(f"  champions that do not touch the bottom of the workspace: {sum(r['lowest_layer'] > 0 for r in rows)}")

    again = audit(rows)
    print(f"\nAUDIT: {sum(a['identical'] for a in again)} of {len(again)} champions get their recorded score when "
          f"simulated again")
    for a in again:
        if not a['identical']:
            print(f"  seed {a['seed']}: recorded {a['recorded']:.6f}, simulated again {a['simulated_again']:.6f}")

    out = {'arm': ARM, 'by_hand': hand, 'runs': records, 'pilot': with_pilot, 'champions': rows, 'audit': again}
    with open(os.path.join(OUT, f'arm_{ARM}_checks.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    print(f"\nWritten to {os.path.relpath(os.path.join(OUT, f'arm_{ARM}_checks.json'), ROOT)} and "
          f"{os.path.relpath(AUDIT, ROOT)}")
    good = (hand['agrees_with_the_report'] and not records['problems'] and records['same_simulator']
            and records['same_template'] and with_pilot['identical'] and all(a['identical'] for a in again)
            and all(r['the_one_the_report_measured'] and r['is_the_last_point_of_the_curve'] for r in rows))
    print('ALL CHECKS HOLD' if good else 'A CHECK DOES NOT HOLD: see above')
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
