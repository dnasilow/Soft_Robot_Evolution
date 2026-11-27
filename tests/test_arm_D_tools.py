"""The two tools for arm D's champions (PROTOCOL.md, section 9.7), written on 27 November 2026
while the arm was running and before any score of it had been read:

  paper/analysis/check_arm_D.py      the checks on the arm's report and the audit of its champions
  paper/analysis/transfer_to_2013.py the champions scored in the original 2013 simulator

Everything here runs on made-up runs or on a small run made for the test; nothing reads arm D.
"""
import contextlib
import csv
import io
import json
import os
import pickle
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))
import check_arm_D as cd                                          # noqa: E402
import protocol_stats as ps                                       # noqa: E402
import search_arm                                                 # noqa: E402
import transfer_scores as ts                                      # noqa: E402
import transfer_to_2013 as t13                                    # noqa: E402
from src.evolution import cheney2013 as c13                       # noqa: E402
from src.evolution.genome_config import VOXEL_GRID_SHAPE, VOXEL_INTERIOR_MIN   # noqa: E402

PREFIX, STEM, GENERATIONS, SEEDS = 'madeD_s', 'madeD', 4, [1, 2, 3, 4, 5]


def body(variant=0, up=0):
    """A small body in the 10^3 workspace."""
    g = np.zeros((10, 10, 10), np.int8)
    g[4:6, 4:7, up:up + 2] = 1
    g[4:6, 4:5, up:up + 2] = 2
    g[4, 6, up + 1] = 3
    if variant:                                      # two more voxels, placed and filled by the variant
        g[4 + variant % 2, 7, up] = 1 + variant % 2
        g[3, 4 + variant % 3, up] = 1 + (variant // 3) % 2
    return g


def genome_of(grid):
    """The body as a run stores it: inside the larger genome array."""
    big = np.zeros(VOXEL_GRID_SHAPE, np.int8)
    i = VOXEL_INTERIOR_MIN
    big[i:i + 10, i:i + 10, i:i + 10] = grid
    return big


def spec():
    return {'name': 'made-up arm', 'prefix': PREFIX, 'seeds': list(SEEDS), 'generations': GENERATIONS,
            'checked_at': (GENERATIONS, 2), 'runner': ['--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '30'],
            'code_tag': 'campaign-v4', 'report': None, 'stem': 'made', 'is_arm': False}


def scores_of(seed):
    """Three robots per generation; the champion's score rises with the generation and the seed."""
    return [[0.1 * seed + 0.25 * g, 0.05 * seed, 0.0] for g in range(1, GENERATIONS + 1)]


def invocation(seed, started='2026-11-27 15:03:58', workers=3, **changed):
    settings = {'preset': 'cheney2013-floor', 'pop': 30, 'gen': GENERATIONS, 'workers': workers, 'seed': seed,
                'name': f'{PREFIX}{seed}', 'floor_contact': 'rule2013', 'start': 'workspace', 'amp': 0.14}
    settings.update(changed.pop('settings', {}))
    import run_tendon_evolution as runner
    i = {'started': started,
         'command': ['run_tendon_evolution.py', '--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '30', '--gen',
                     str(GENERATIONS), '--workers', str(workers), '--seed', str(seed), '--name', f'{PREFIX}{seed}'],
         'settings': settings, 'preset_applied': dict(runner._PRESETS['cheney2013-floor']), 'git_commit': 'a' * 40,
         'git_modified': ['MUJOCO_LOG.TXT'], 'python': '3.13', 'mujoco': '3.4.0', 'numpy': '2.2.6', 'platform': 'Windows',
         'threads': dict(search_arm.ONE_THREAD)}
    i.update(changed)
    return i


def invocation_of(arm, prefix, seed, workers=3, **changed):
    """What a run made with the command of that arm records of one start of itself."""
    import run_tendon_evolution as runner
    preset, given = search_arm.engine_options(search_arm.ARMS[arm])
    entries = dict(runner._PRESETS[preset])
    applied = {k: v for k, v in entries.items() if k not in given}
    settings = dict(applied, preset=preset, pop=30, gen=GENERATIONS, workers=workers, seed=seed, name=f'{prefix}{seed}')
    settings.update({k: type(entries[k])(v) for k, v in given.items()})
    settings.update(changed.pop('settings', {}))
    i = {'started': '2026-11-30 09:00:00',
         'command': ['run_tendon_evolution.py'] + list(search_arm.ARMS[arm]['runner']) + [
             '--gen', str(GENERATIONS), '--workers', str(workers), '--seed', str(seed), '--name', f'{prefix}{seed}'],
         'settings': settings, 'preset_applied': applied, 'git_commit': 'a' * 40, 'git_modified': ['MUJOCO_LOG.TXT'],
         'python': '3.13', 'mujoco': '3.4.0', 'numpy': '2.2.6', 'platform': 'Windows',
         'threads': dict(search_arm.ONE_THREAD)}
    i.update(changed)
    return i


def make_run(results, seed, starts=None, checkpoint=False, tie=False, prefix=PREFIX, scale=1.0):
    folder = os.path.join(results, f'{prefix}{seed}')
    os.makedirs(folder)
    curve = [[scale * v for v in row] for row in scores_of(seed)]
    for g, fitnesses in enumerate(curve, start=1):
        with open(os.path.join(folder, f'gen_{g:03d}.json'), 'w') as f:
            json.dump({'generation': g, 'best_fitness': max(fitnesses), 'fitnesses': fitnesses}, f)
    top = max(curve[-1])
    population = [(genome_of(body(seed)), scale * 0.05 * seed), (genome_of(body(seed + 10)), top)]
    if tie:
        population.append((genome_of(body(seed + 20)), top))
    with open(os.path.join(folder, 'final_population.pkl'), 'wb') as f:
        pickle.dump({'genomes': [g for g, _ in population], 'fitnesses': [v for _, v in population]}, f)
    with open(os.path.join(folder, 'best_robot.pkl'), 'wb') as f:
        pickle.dump({'genome': genome_of(body(seed + 10)), 'fitness': top}, f)
    with open(os.path.join(folder, 'history.json'), 'w') as f:
        json.dump({'best_fitness': [max(v) for v in curve]}, f)
    with open(os.path.join(folder, 'manifest.json'), 'w') as f:
        json.dump({'invocations': starts or [invocation(seed)]}, f)
    if checkpoint:
        with open(os.path.join(folder, 'checkpoint.pkl'), 'wb') as f:
            f.write(b'x')
    return folder


def make_report(deposit, wrong=False):
    """What analyse_arm.py would report for the made-up runs, computed with the analysis' own
    statistics; by_hand must arrive at the same numbers with arithmetic of its own."""
    report = {'scores': {}, 'per_seed': []}
    for g in (GENERATIONS, 2):
        x = [max(max(f) for f in scores_of(s)[:g]) for s in SEEDS]
        y = [max(c[:g]) for c in deposit]
        report['scores'][str(g)] = ps.compare(x, y, 200, 0)
    if wrong:
        report['scores'][str(GENERATIONS)]['arm_median'] += 0.001
    for s in SEEDS:
        top = max(scores_of(s)[-1])
        report['per_seed'].append({'seed': s, 'scores': {str(g): max(max(f) for f in scores_of(s)[:g])
                                                         for g in (GENERATIONS, 2)},
                                   'champion': {'file': 'final_population.pkl, individual 1', 'original': top,
                                                'body': {'voxels': int((body(s + 10) != 0).sum())}}})
    return report


DEPOSIT = [[0.2 + 0.1 * k + 0.2 * g for g in range(1, 6)] for k in range(7)]


class TestChecksOnMadeUpRuns(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.results = self.tmp.name
        os.makedirs(os.path.join(self.results, 'campaign', f'{STEM}_logs'))

    def build(self, **per_seed):
        for s in SEEDS:
            make_run(self.results, s, **per_seed.get(f's{s}', {}))

    def records(self, same_code=lambda commit, tag: True):
        return cd.runs(spec(), self.results, same_code=same_code)

    def test_by_hand_arrives_at_the_reports_numbers(self):
        self.build()
        hand, curves = cd.by_hand(spec(), make_report(DEPOSIT), self.results, deposit=DEPOSIT)
        self.assertTrue(hand['agrees_with_the_report'])
        self.assertEqual(hand['seeds_whose_scores_agree_with_the_report'], len(SEEDS))
        self.assertEqual(sorted(hand['generations']), ['2', str(GENERATIONS)])
        self.assertAlmostEqual(hand['generations'][str(GENERATIONS)]['arm_median'], 0.1 * 3 + 0.25 * GENERATIONS)
        self.assertEqual(curves[2], [max(f) for f in scores_of(2)])
        wrong, _ = cd.by_hand(spec(), make_report(DEPOSIT, wrong=True), self.results, deposit=DEPOSIT)
        self.assertFalse(wrong['agrees_with_the_report'])

    def test_a_run_with_a_generation_missing_stops_it(self):
        self.build()
        os.remove(os.path.join(self.results, f'{PREFIX}3', 'gen_002.json'))
        with self.assertRaises(SystemExit):
            cd.by_hand(spec(), make_report(DEPOSIT), self.results, deposit=DEPOSIT)

    def test_clean_runs_have_no_problems(self):
        self.build()
        r = self.records()
        self.assertEqual(r['problems'], [])
        self.assertEqual((r['runs'], r['started_more_than_once'], r['evaluations_at_a_time']), (5, {}, [3]))
        self.assertEqual(r['code_commits'], {'aaaaaaa': True})
        self.assertEqual((r['bodies_the_engine_refused'], r['runs_that_stopped_themselves']), ({}, {}))

    def test_a_run_started_twice_is_reported_and_is_no_problem(self):
        again = [invocation(2), invocation(2, started='2026-11-28 02:10:00', workers=2)]
        self.build(s2={'starts': again})
        with open(os.path.join(self.results, 'campaign', f'{STEM}_launcher.log'), 'w') as f:
            f.write("[28 Nov 02:10] madeD_s2: ended with code 1 at generation 2: an evaluation failed for a reason that is "
                    "not the robot's and was not scored (MemoryError: Unable to allocate 4.91 MiB); continuing it from its "
                    "checkpoint (start 2 of 6). Its last lines: Gen   2/4  best=(not shown)W\n"
                    "[28 Nov 05:00] madeD_s4 has recorded no new generation for 2.1 h: its processes are ended, and the run "
                    "is then continued from its checkpoint.\n")
        with open(os.path.join(self.results, 'campaign', f'{STEM}_logs', f'{PREFIX}2.log'), 'w') as f:
            f.write("  [Evaluator] A robot failed and scores 0: ValueError: No voxels in grid!\n"
                    "Traceback (most recent call last):\n"
                    "src.evolution.mujoco_tendon_evaluator.EvaluationStopped: An evaluation ended in an error that is not a "
                    "result of the robot, so it was not scored: MemoryError: Unable to allocate 4.91 MiB\n")
        r = self.records()
        self.assertEqual(r['problems'], [])
        self.assertEqual(list(r['started_more_than_once']), ['2'])
        self.assertEqual(r['evaluations_at_a_time'], [2, 3])                  # the number of workers is not a setting
        early = r['runs_that_ended_early_by_the_launcher_log']
        self.assertEqual((early[0]['seed'], early[0]['code'], early[0]['generation']), (2, 1, 2))
        self.assertIn('MemoryError: Unable to allocate 4.91 MiB', early[0]['why'])
        self.assertNotIn('last lines', early[0]['why'])
        self.assertEqual(r['runs_that_stood_still'], ['madeD_s4 has recorded no new generation for 2.1 h'])
        self.assertEqual(r['bodies_the_engine_refused'], {'2': {'bodies': 1, 'reasons': ['ValueError: No voxels in grid!']}})
        self.assertEqual(r['runs_that_stopped_themselves'], {'2': 1})

    def test_what_counts_as_a_problem(self):
        self.build(s1={'starts': [invocation(1, settings={'amp': 0.2})]},                     # another setting
                   s2={'starts': [invocation(2, threads={'OPENBLAS_NUM_THREADS': None})]},   # not one thread
                   s3={'checkpoint': True},                                                   # not finished cleanly
                   s4={'starts': [invocation(4, git_modified=['MUJOCO_LOG.TXT', 'src/physics/mujoco_beam_physics.py'])]},
                   s5={'starts': [invocation(5, preset_applied={'body': 'beam'})]})
        problems = ' | '.join(self.records()['problems'])
        self.assertIn('seed 2, start 1: settings or libraries differ', problems)       # seed 1 came first; 2 differs from it
        self.assertIn('seed 2, start 1: thread settings', problems)
        self.assertIn('seed 3: a checkpoint is left over', problems)
        self.assertIn('seed 4, start 1: files that compute a run differed from the commit', problems)
        self.assertIn("seed 5, start 1: the preset was not applied as the arm's command has it", problems)

    def test_code_that_is_not_the_tags_is_a_problem(self):
        self.build()
        r = self.records(same_code=lambda commit, tag: False)
        self.assertEqual(r['code_commits'], {'aaaaaaa': False})
        self.assertIn('are not those of campaign-v4', ' '.join(r['problems']))
        self.assertEqual(cd.touches_the_code(['MUJOCO_LOG.TXT', 'paper/PLAN.md']), [])
        self.assertEqual(cd.touches_the_code(['run_tendon_evolution.py']), ['run_tendon_evolution.py'])

    def test_the_real_tag_is_recognised(self):
        self.assertTrue(cd.same_code_as_tag('campaign-v4', 'campaign-v4'))
        self.assertFalse(cd.same_code_as_tag('campaign-v3', 'campaign-v4'))

    def test_champions_are_picked_as_the_analysis_picks_them(self):
        self.build(s3={'tie': True})
        s = spec()
        _, curves = cd.by_hand(s, make_report(DEPOSIT), self.results, deposit=DEPOSIT)
        rows, stored = cd.champions(s, make_report(DEPOSIT), curves, self.results)
        self.assertEqual([r['individual'] for r in rows], [1] * 5)                 # the first of those that tie
        for key in ('the_one_the_report_measured', 'is_the_last_point_of_the_curve', 'is_the_best_of_the_whole_run',
                    'is_the_run_s_recorded_best_robot'):
            self.assertTrue(all(r[key] for r in rows), key)
        self.assertEqual([r['different_bodies_among_them'] for r in rows], [1, 1, 2, 1, 1])
        self.assertEqual(stored[2].shape, tuple(VOXEL_GRID_SHAPE))                # the body as the run stored it
        self.assertTrue(np.array_equal(c13.workspace_grid(stored[2]), body(12)))

    def audit_with(self, again, quarter):
        self.build()
        s = spec()
        _, curves = cd.by_hand(s, make_report(DEPOSIT), self.results, deposit=DEPOSIT)
        rows, stored = cd.champions(s, make_report(DEPOSIT), curves, self.results)
        asked = []

        def evaluate_all(jobs, workers, cache):
            asked.extend(jobs)
            out = {}
            for key, genome, params, fraction, name in jobs:
                seed = int(name.split('seed ')[1].split(',')[0])
                score = (again if fraction == 1.0 else quarter)(seed, max(scores_of(seed)[-1]))
                out[key] = {'key': key, 'score': score, 'blew_up': False, 'error': None, 'moved': [score, 0.0, -0.01],
                            'time_step': 3.5e-5 * fraction, 'steps': int(7100 / fraction), 'sunk': 0.7 + 0.01 * seed,
                            'seconds': 1.0}
            return out
        audited = cd.audit(s, rows, stored, evaluate_all=evaluate_all, params={'voxel_size': 0.01})
        return audited, asked, stored

    def test_the_audit_asks_for_each_stored_body_twice(self):
        audited, asked, stored = self.audit_with(lambda seed, v: v, lambda seed, v: v * 1.05)
        self.assertEqual(len(asked), 10)
        self.assertEqual(sorted(j[3] for j in asked), [0.25] * 5 + [1.0] * 5)
        self.assertTrue(all(j[1].shape == tuple(VOXEL_GRID_SHAPE) for j in asked))
        self.assertTrue(np.array_equal(asked[0][1], stored[1]))
        s = cd.audit_summary(audited)
        self.assertEqual((s['champions'], s['reproduced'], s['quarter_change_over_10_percent']), (5, 5, 0))
        self.assertAlmostEqual(s['quarter_change_median'], 0.05)
        self.assertAlmostEqual(s['sank'][0], 0.73)

    def test_a_score_that_is_not_reproduced_to_the_last_digit_is_said(self):
        audited, _, _ = self.audit_with(lambda seed, v: v + (1e-13 if seed == 4 else 0.0),
                                        lambda seed, v: v * (1.5 if seed == 2 else 0.97))
        self.assertEqual([a['reproduced'] for a in audited], [True, True, True, False, True])
        s = cd.audit_summary(audited)
        self.assertEqual((s['reproduced'], s['quarter_change_over_10_percent'], s['quarter_change_largest_seed']), (4, 1, 2))
        self.assertAlmostEqual(s['quarter_change_largest'], 0.5)
        path = os.path.join(self.results, 'audit.csv')
        cd.write_audit(path, audited)
        with open(path, newline='') as f:
            table = list(csv.DictReader(f))
        self.assertEqual((len(table), table[3]['reproduced'], table[1]['seed']), (5, 'False', '2'))

    def test_the_arm_is_the_one_of_the_launcher(self):
        s = cd.arm_spec()
        self.assertEqual((s['prefix'], s['seeds'], s['generations'], s['checked_at'], s['code_tag']),
                         ('armD_s', list(range(1, 11)), 300, (300, 100), 'campaign-v4'))
        self.assertEqual(cd.preset_of(s), 'cheney2013-floor')
        self.assertEqual(cd.expected_command(s, 7, 3), ['run_tendon_evolution.py', '--preset', 'cheney2013-floor',
                                                         '--no-age-pareto', '--pop', '30', '--gen', '300', '--workers', '3',
                                                         '--seed', '7', '--name', 'armD_s7'])
        self.assertTrue(s['report'].endswith(os.path.join('paper', 'outcomes', 'arm_D.json')))


class TestTheAuditOnARealRun(unittest.TestCase):
    """A run of the search's own command line under the preset of arm D, small enough to take
    seconds. Its champion, evaluated again from the body the run stored, must get the recorded
    score to the last digit: that is what the audit's first line claims."""

    def test_the_recorded_score_is_reproduced(self):
        runner = ['--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '4', '--grid-size', '5']
        s = {'name': 'a small run', 'prefix': 'small_s', 'seeds': [3], 'generations': 2, 'checked_at': (2,),
             'runner': runner, 'code_tag': 'campaign-v4', 'report': None, 'stem': 'small', 'is_arm': False}
        with tempfile.TemporaryDirectory() as tmp:
            command = cd.expected_command(s, 3, 1)
            r = subprocess.run([sys.executable, os.path.join(ROOT, command[0])] + command[1:], cwd=tmp,
                               env=search_arm.run_environment(), capture_output=True, text=True, timeout=1800)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            results = os.path.join(tmp, 'results')
            curves = {3: [max(f['fitnesses']) for _, f in sorted(cd.generation_files(os.path.join(results, 'small_s3')).items())]}
            report = {'per_seed': []}                                 # no report: the champion is checked against the run
            rows, stored = cd.champions(s, report, curves, results)
            self.assertTrue(rows[0]['is_the_last_point_of_the_curve'] and rows[0]['is_the_run_s_recorded_best_robot'])
            params = ts.worker_parameters(ts.evaluator_arguments(early_stop=True, workspace=5, preset='cheney2013-floor'))
            audited = cd.audit(s, rows, stored, workers=1, cache=os.path.join(tmp, 'audit.json'), params=params)
        a = audited[0]
        self.assertGreater(a['recorded'], 0)
        self.assertTrue(a['reproduced'], f"recorded {a['recorded']!r}, evaluated again {a['again']!r}")
        self.assertEqual(a['difference'], 0.0)
        self.assertAlmostEqual(a['quarter_time_step'], cd.QUARTER * a['time_step'], places=12)
        self.assertTrue(a['quarter'] > 0 and a['sank'] is not None)


E_ARMS = ('E1', 'E2', 'E3')


def e_spec(arm, prefix, against_prefix='madeBase_s'):
    """A made-up arm of three runs made with the command of arm E1, E2 or E3, set against a
    made-up arm D of five."""
    return {'name': f'made-up arm {arm}', 'prefix': prefix, 'seeds': [1, 2, 3], 'generations': GENERATIONS,
            'checked_at': (GENERATIONS, 2), 'runner': list(search_arm.ARMS[arm]['runner']), 'code_tag': 'campaign-v4',
            'report': None, 'stem': f'made_{arm}', 'is_arm': False,
            'against': {'arm': 'D', 'prefix': against_prefix, 'seeds': list(SEEDS), 'generations': GENERATIONS}}


class TestArmsE(unittest.TestCase):
    """Arms E1 to E3 get arm D's checks and audit with their own settings (PROTOCOL.md, section
    9.7, point 7, and section 9.8). Written on 27 November 2026, before any of them was started."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.results = self.tmp.name

    def build(self, arm, prefix, starts=None, scale=0.5):
        for s in (1, 2, 3):
            make_run(self.results, s, prefix=prefix, scale=scale,
                     starts=(starts or {}).get(s) or [invocation_of(arm, prefix, s)])

    def test_the_arms_are_those_of_the_launcher_and_of_the_analysis(self):
        self.assertEqual(cd.engine_arms(), ['D', 'E1', 'E2', 'E3'])
        floors = {}
        for arm in E_ARMS:
            s = cd.arm_spec(arm)
            self.assertEqual((s['prefix'], s['seeds'], s['generations'], s['checked_at'], s['code_tag'], s['stem']),
                             (f'arm{arm}_s', [1, 2, 3], 300, (300, 100), 'campaign-v4', f'arm_{arm}'))
            self.assertTrue(s['report'].endswith(os.path.join('paper', 'outcomes', f'arm_{arm}.json')))
            self.assertEqual(s['against'], {'arm': 'D', 'prefix': 'armD_s', 'seeds': list(range(1, 11)), 'generations': 300})
            self.assertEqual(cd.engine_of(s), search_arm.engine_options(search_arm.ARMS[arm]))
            self.assertEqual(cd.expected_command(s, 2, 3)[1:-8], search_arm.ARMS[arm]['runner'])
            floors[arm] = cd.floor_of(s)
        self.assertEqual(floors, {'E1': 'rule2013', 'E2': 'rule2013', 'E3': 'voxelyze'})
        d = cd.arm_spec()                                                 # arm D, the default, is what it was
        self.assertEqual((d['prefix'], d['seeds'], cd.engine_of(d), cd.floor_of(d)),
                         ('armD_s', list(range(1, 11)), ('cheney2013-floor', {}), 'rule2013'))
        self.assertNotIn('against', d)
        r = cd.rehearsal_spec('trialE2_s', [101, 102, 103], 2, arm='E2')
        self.assertEqual((cd.engine_of(r), r['is_arm'], r['checked_at']), (('cheney2013-floor', {'amp': '0.2', 'poisson': 'on'}),
                                                                         False, (2,)))
        self.assertNotIn('against', r)

    def test_clean_runs_of_each_arm_have_no_problems(self):
        for arm in E_ARMS:
            prefix = f'made{arm}_s'
            self.build(arm, prefix)
            r = cd.runs(e_spec(arm, prefix), self.results, same_code=lambda commit, tag: True)
            self.assertEqual(r['problems'], [], arm)
            self.assertEqual((r['runs'], r['evaluations_at_a_time']), (3, [3]))

    def test_runs_made_with_another_arm_s_settings_are_a_problem(self):
        # runs made with arm D's command, checked as arm E1: the command, the preset and the damping are wrong
        self.build('D', 'madeX_s')
        problems = ' | '.join(cd.runs(e_spec('E1', 'madeX_s'), self.results, same_code=lambda c, t: True)['problems'])
        self.assertIn('seed 1, start 1: command', problems)
        self.assertIn("seed 1, start 1: the preset was not applied as the arm's command has it", problems)
        self.assertIn("seed 1, start 1: damping_global is 0.001, the arm's command says 0.01", problems)
        # the right command, but a run whose record says the volumetric law was off
        wrong = {2: [invocation_of('E2', 'madeY_s', 2, settings={'poisson': 'off'})]}
        self.build('E2', 'madeY_s', starts=wrong)
        found = cd.runs(e_spec('E2', 'madeY_s'), self.results, same_code=lambda c, t: True)['problems']
        self.assertIn("seed 2, start 1: poisson is 'off', the arm's command says 'on'", found)
        self.assertEqual([p for p in found if not p.startswith('seed 2,')], [])      # the other two runs are in order
        # runs of the hard floor checked as arm D
        self.build('E3', 'madeZ_s')
        d_like = dict(e_spec('D', 'madeZ_s'))
        problems = ' | '.join(cd.runs(d_like, self.results, same_code=lambda c, t: True)['problems'])
        self.assertIn("the preset was not applied as the arm's command has it", problems)

    def report_of(self, prefix, base, deposit, scale):
        """What analyse_arm.py would report: against the deposit and against the other arm."""
        report = {'scores': {}, 'per_seed': [], 'against': {'arm': 'D', 'scores': {}}}
        for g in (GENERATIONS, 2):
            x = [scale * max(max(f) for f in scores_of(s)[:g]) for s in (1, 2, 3)]
            report['scores'][str(g)] = ps.compare(x, [max(c[:g]) for c in deposit], 200, 0)
            report['against']['scores'][str(g)] = ps.compare(x, [max(max(f) for f in scores_of(s)[:g]) for s in SEEDS], 200, 0)
        for s in (1, 2, 3):
            report['per_seed'].append({'seed': s, 'scores': {str(g): scale * max(max(f) for f in scores_of(s)[:g])
                                                             for g in (GENERATIONS, 2)}})
        return report

    def test_by_hand_sets_the_arm_against_arm_d_from_the_raw_files_of_both(self):
        for s in SEEDS:
            make_run(self.results, s, prefix='madeBase_s')                 # the made-up arm D
        self.build('E1', 'madeE1_s', scale=0.5)
        spec_ = e_spec('E1', 'madeE1_s')
        report = self.report_of('madeE1_s', 'madeBase_s', DEPOSIT, 0.5)
        hand, curves = cd.by_hand(spec_, report, self.results, deposit=DEPOSIT)
        self.assertTrue(hand['agrees_with_the_report'])
        block = hand['against']
        self.assertEqual((block['arm'], block['runs'], block['the_report_has_this_comparison']), ('D', 5, True))
        final = block['generations'][str(GENERATIONS)]
        self.assertAlmostEqual(final['other_median'], 0.1 * 3 + 0.25 * GENERATIONS)        # the made-up arm D's median
        self.assertAlmostEqual(final['arm_median'], 0.5 * (0.1 * 2 + 0.25 * GENERATIONS))
        self.assertAlmostEqual(final['ratio_to_the_other_arm'], final['arm_median'] / final['other_median'])
        self.assertLessEqual(final['largest_difference_from_the_report'], 1e-9)
        # a report whose comparison with arm D is off, or is not there, does not pass
        report['against']['scores'][str(GENERATIONS)]['reference_median'] += 0.001
        self.assertFalse(cd.by_hand(spec_, report, self.results, deposit=DEPOSIT)[0]['agrees_with_the_report'])
        del report['against']
        hand, _ = cd.by_hand(spec_, report, self.results, deposit=DEPOSIT)
        self.assertFalse(hand['agrees_with_the_report'])
        self.assertFalse(hand['against']['the_report_has_this_comparison'])

    def test_the_audit_takes_the_arm_s_own_settings(self):
        seen = {}

        def evaluate_all(jobs, workers, cache):
            seen['params'] = jobs[0][2]
            return {key: {'key': key, 'score': 1.0, 'blew_up': False, 'error': None, 'moved': [1.0, 0.0, 0.0],
                          'time_step': 3e-5 * fraction, 'steps': 100, 'sunk': 0.1, 'seconds': 1.0}
                    for key, genome, params, fraction, name in jobs}
        expected = {'E1': {'global_damping': 0.01}, 'E2': {'actuation_amplitude': 0.2, 'poisson': True},
                    'E3': {'floor_contact': 'voxelyze', 'start': 'floor'}}
        base = ts.worker_parameters(ts.evaluator_arguments(early_stop=True, preset='cheney2013-floor'))
        rows = [{'seed': 1, 'voxels': 14, 'lowest_layer': 0, 'fitness': 1.0}]
        for arm in E_ARMS:
            cd.audit(e_spec(arm, 'x_s'), rows, {1: genome_of(body(1))}, evaluate_all=evaluate_all,
                     cache=os.path.join(self.results, f'{arm}.json'))
            differs = {k: v for k, v in seen['params'].items() if base.get(k) != v}
            self.assertEqual(differs, expected[arm], arm)


class TestTheAuditOnRealRunsOfTheEArms(unittest.TestCase):
    """For each of the three settings a run of the search's own command line, small enough to take
    a minute. Its record of itself must pass the checks made of an arm's runs, and its champion,
    evaluated again from the stored body with the settings read back from the launcher's command,
    must get the recorded score to the last digit. That is what makes the audit of an E arm the
    evaluation of its runs."""

    def run_small(self, arm):
        words = list(search_arm.ARMS[arm]['runner'])
        runner = words[:words.index('--pop')] + ['--pop', '4', '--grid-size', '5']
        s = {'name': f'a small run with the settings of arm {arm}', 'prefix': 'small_s', 'seeds': [101], 'generations': 2,
             'checked_at': (2,), 'runner': runner, 'code_tag': 'campaign-v4', 'report': None, 'stem': 'small', 'is_arm': False}
        with tempfile.TemporaryDirectory() as tmp:
            command = cd.expected_command(s, 101, 1)
            r = subprocess.run([sys.executable, os.path.join(ROOT, command[0])] + command[1:], cwd=tmp,
                               env=search_arm.run_environment(), capture_output=True, text=True, timeout=3600)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            results = os.path.join(tmp, 'results')
            os.makedirs(os.path.join(results, 'campaign'), exist_ok=True)
            records = cd.runs(s, results, same_code=lambda commit, tag: True)
            curves = {101: [max(f['fitnesses']) for _, f in sorted(cd.generation_files(os.path.join(results, 'small_s101')).items())]}
            rows, stored = cd.champions(s, {'per_seed': []}, curves, results)
            preset, given = search_arm.engine_options(search_arm.ARMS[arm])
            params = ts.worker_parameters(ts.evaluator_arguments(early_stop=True, workspace=5, preset=preset, given=given))
            audited = cd.audit(s, rows, stored, workers=1, cache=os.path.join(tmp, 'audit.json'), params=params)
        return records, rows[0], audited[0], params

    def check(self, arm, **settings):
        records, row, a, params = self.run_small(arm)
        self.assertEqual(records['problems'], [], arm)                    # the run recorded the arm's settings
        for key, value in settings.items():
            self.assertEqual(params[key], value)
        self.assertTrue(row['is_the_last_point_of_the_curve'] and row['is_the_run_s_recorded_best_robot'])
        self.assertGreater(a['recorded'], 0)
        self.assertTrue(a['reproduced'], f"arm {arm}: recorded {a['recorded']!r}, evaluated again {a['again']!r}")
        self.assertAlmostEqual(a['quarter_time_step'], cd.QUARTER * a['time_step'], places=12)
        return a

    def test_arm_e1_global_damping(self):
        self.check('E1', global_damping=0.01, floor_contact='rule2013')

    def test_arm_e2_amplitude_and_volumetric_law(self):
        self.check('E2', actuation_amplitude=0.2, poisson=True, floor_contact='rule2013')

    def test_arm_e3_hard_floor(self):
        self.check('E3', floor_contact='voxelyze', start='floor')


def stand_in_score(grid):
    """A fixed function of the body that differs from body to body."""
    g = c13.workspace_grid(np.asarray(grid))
    return 0.001 * float((np.argwhere(g != 0) * [1, 2, 3]).sum() + g.sum())


class StandInSimulator:
    """Takes the place of the 2013 simulator. special: {a body's bytes: the score it gets instead}."""
    def __init__(self, special=None):
        self.special, self.asked = special or {}, []

    def evaluate_batch(self, genomes):
        self.asked.append(len(genomes))
        return np.array([self.special.get(c13.workspace_grid(np.asarray(g)).tobytes(), stand_in_score(g)) for g in genomes])


def champion(k, evolved):
    return {'set': 'arm_D', 'label': f'seed {k}', 'file': f'final_population.pkl, individual {k}', 'evolved': evolved,
            'recorded_2013': None, 'grid': body(k, up=k % 3)}


class TestTransferTo2013(unittest.TestCase):
    def test_one_simulation_per_champion_and_the_ratio(self):
        simulator = StandInSimulator()
        rows = t13.score_in_2013([champion(k, 0.2 + 0.1 * k) for k in (1, 2, 3, 4)], evaluator=simulator)
        self.assertEqual(simulator.asked, [4])
        for k, r in zip((1, 2, 3, 4), rows):
            grid = body(k, up=k % 3)
            self.assertEqual((r['label'], r['voxels'], r['lowest_layer']), (f'seed {k}', int((grid != 0).sum()), k % 3))
            self.assertAlmostEqual(r['score'], stand_in_score(grid))
            self.assertAlmostEqual(r['ratio'], stand_in_score(grid) / (0.2 + 0.1 * k))
            self.assertFalse(r['blew_up'])
        self.assertEqual(len({r['score'] for r in rows}), 4)

    def test_a_simulation_without_a_usable_result_is_counted_and_kept(self):
        simulator = StandInSimulator({body(1).tobytes(): c13.MISSING_FITNESS, body(2).tobytes(): c13.FLOOR_FITNESS})
        rows = t13.score_in_2013([champion(k, 1.0) | {'grid': body(k)} for k in (1, 2, 3)], evaluator=simulator)
        self.assertEqual([(r['no_result'], r['not_usable'], r['blew_up']) for r in rows],
                         [(True, False, True), (False, True, True), (False, False, False)])
        report = t13.build_report(rows, n_boot=200, seed=0)
        self.assertEqual(report['without_a_usable_result'], {'no_result': 1, 'not_usable': 1})
        self.assertEqual((report['set']['n'], report['set']['blew_up']), (3, 2))

    def test_a_champion_without_a_score_has_no_ratio(self):
        with self.assertRaises(SystemExit):
            t13.score_in_2013([champion(1, 0.0)], evaluator=StandInSimulator())

    def test_the_statistics_and_the_comparison(self):
        rows = t13.score_in_2013([champion(k, 0.3 + 0.05 * k) for k in range(1, 9)], evaluator=StandInSimulator())
        reference = [0.9, 1.1, 1.2, 1.3, 0.8, 1.0, 1.4]
        report = t13.build_report(rows, reference, n_boot=300, seed=0)
        s = report['set']
        ratios = sorted(r['ratio'] for r in rows)
        self.assertEqual(s['n'], 8)
        self.assertAlmostEqual(s['ratio'][0], (ratios[3] + ratios[4]) / 2)
        self.assertTrue(s['ratio_median_interval'][0] <= s['ratio'][0] <= s['ratio_median_interval'][1])
        self.assertTrue(-1 <= s['rank_correlation'] <= 1)
        c = report['comparison']
        self.assertEqual(c['n_reference'], 7)
        self.assertAlmostEqual(c['result']['a12'], ps.a12([r['ratio'] for r in rows], reference))
        self.assertNotIn('comparison', t13.build_report(rows, None, n_boot=300, seed=0))

    def test_the_reference_is_the_deposit_under_the_preset_of_arm_d(self):
        self.assertEqual((t13.REFERENCE_REPORT, t13.REFERENCE_SET), ('transfer_floor2013.json', 'deposit_noCost'))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(t13.reference_ratios(tmp))
            with open(os.path.join(tmp, 'transfer_floor2013.json'), 'w') as f:
                json.dump({'champions': [{'set': 'deposit_noCost', 'ratio': 1.16}, {'set': 'arm_R', 'ratio': 1.02},
                                         {'set': 'deposit_noCost', 'ratio': 0.76}]}, f)
            self.assertEqual(t13.reference_ratios(tmp), [1.16, 0.76])

    def run_main(self, argv, **more):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = t13.main(argv, **more)
        return code, out.getvalue()

    def test_an_arm_that_was_not_analysed_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, said = self.run_main(['--arm', 'D', '--outcomes-dir', tmp, '--out-dir', os.path.join(tmp, 'out')],
                                       evaluator=StandInSimulator())
            self.assertEqual(code, 2)
            self.assertIn('has not been analysed', said)
            self.assertFalse(os.path.exists(os.path.join(tmp, 'out')))

    def test_a_rehearsal_on_made_up_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = os.path.join(tmp, 'results')
            for s in SEEDS:
                make_run(results, s, checkpoint=(s == 5))                     # seed 5 is not complete
            same = {'simulator_sha256': 'a' * 64, 'template_sha256': 'b' * 64}
            with open(os.path.join(tmp, 'arm_A_checks.json'), 'w') as f:
                json.dump({'runs': same}, f)
            code, said = self.run_main(['--rehearsal', PREFIX, '--generation', str(GENERATIONS), '--results-dir', results,
                                        '--outcomes-dir', tmp, '--out-dir', os.path.join(tmp, 'out')],
                                       evaluator=StandInSimulator(), simulator=lambda: dict(same))
            self.assertEqual(code, 0, said)
            name = f'transfer_to_2013_rehearsal_{PREFIX}{GENERATIONS}'
            with open(os.path.join(tmp, 'out', name + '.json')) as f:
                report = json.load(f)
            self.assertEqual([r['label'] for r in report['champions']], ['seed 1', 'seed 2', 'seed 3', 'seed 4'])
            self.assertEqual(report['champions'][1]['evolved'], max(scores_of(2)[-1]))
            self.assertTrue(report['simulator']['same_simulator'] and report['simulator']['same_template'])
            self.assertIn('REHEARSAL, not an arm', said)
            self.assertIn('is that of the program arms R, Rc and A ran with', said)
            self.assertIn('is not in', said)                                  # no reference report in the made-up folder
            with open(os.path.join(tmp, 'out', name + '_champions.csv'), newline='') as f:
                self.assertEqual(len(list(csv.DictReader(f))), 4)
            code, said = self.run_main(['--rehearsal', PREFIX, '--generation', '9', '--results-dir', results,
                                        '--outcomes-dir', tmp, '--out-dir', os.path.join(tmp, 'out2')],
                                       evaluator=StandInSimulator(), simulator=lambda: dict(same))
            self.assertEqual(code, 2)

    def test_another_simulator_is_said(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = os.path.join(tmp, 'results')
            for s in SEEDS:
                make_run(results, s)
            with open(os.path.join(tmp, 'arm_A_checks.json'), 'w') as f:
                json.dump({'runs': {'simulator_sha256': 'a' * 64, 'template_sha256': 'b' * 64}}, f)
            code, said = self.run_main(['--rehearsal', PREFIX, '--generation', str(GENERATIONS), '--results-dir', results,
                                        '--outcomes-dir', tmp, '--out-dir', os.path.join(tmp, 'out')],
                                       evaluator=StandInSimulator(),
                                       simulator=lambda: {'simulator_sha256': 'c' * 64, 'template_sha256': 'b' * 64})
            self.assertEqual(code, 0)
            self.assertIn('IS NOT that of the program arms R, Rc and A ran with', said)
            self.assertIn('NOTE: The 2013 simulator on this machine is not', said)


def simulator_there():
    try:
        from src.evolution.voxelyze2013_evaluator import Voxelyze2013Evaluator
        return Voxelyze2013Evaluator.available()
    except Exception:                                             # noqa: BLE001
        return False


@unittest.skipUnless(simulator_there(), 'the 2013 simulator is not built on this machine')
class TestTransferInTheRealSimulator(unittest.TestCase):
    def test_it_is_the_evaluation_of_arm_a_s_search(self):
        from src.evolution.voxelyze2013_evaluator import Voxelyze2013Evaluator
        direct = Voxelyze2013Evaluator(n_workers=2)
        champions = [champion(k, 1.0) | {'grid': genome_of(body(k))} for k in (1, 2)]
        rows = t13.score_in_2013(champions, workers=2)
        for k, r in zip((1, 2), rows):
            self.assertEqual(r['score'], direct.evaluate_single(genome_of(body(k))))
            self.assertGreater(r['score'], c13.MISSING_FITNESS)
        now = t13.simulator_now()
        self.assertEqual((len(now['simulator_sha256']), len(now['template_sha256'])), (64, 64))


if __name__ == '__main__':
    unittest.main()
