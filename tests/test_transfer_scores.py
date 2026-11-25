"""The transfer outcome (paper/analysis/transfer_scores.py, PROTOCOL.md section 9.4): that it
scores a robot exactly as the search does under the preset, reads the right champions, keeps
what it has scored, and computes the statistics it says it computes."""
import contextlib
import csv
import io
import json
import os
import pickle
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
import protocol_stats as ps         # noqa: E402
import transfer_scores as ts        # noqa: E402
import search_arm                   # noqa: E402,F401  (on the path through transfer_scores; patched below)
from src.evolution import cheney2013 as c13   # noqa: E402


def small_body(variant=0):
    """A few voxels in the 10^3 workspace: two muscle phases, one soft and one stiff voxel."""
    g = np.zeros((10, 10, 10), np.int8)
    g[4:6, 4:7, 0:2] = 1
    g[4:6, 4:5, 0:2] = 2
    g[4, 6, 1] = 3
    g[5, 6, 1] = 4
    if variant:
        g[4 + variant % 2, 7, 0] = 1 + variant % 2
    return g


def robot_text(grid):
    return '<VXA>\n' + ''.join(f'<Layer><![CDATA[{row}]]></Layer>\n' for row in c13.layer_rows(grid)) + '</VXA>\n'


def robot_name(run, fitness, voxels):
    return (f'Softbots--{run}--Gen_1000--Ind_0x1--adjFit_{fitness:.8f}--numFilled_{voxels:04d}'
            f'--origFit_{fitness:.8f}_genome.vxa')


class TestThePreset(unittest.TestCase):
    def test_arguments_are_the_presets(self):
        a = ts.evaluator_arguments()
        self.assertEqual((a['body'], a['materials'], a['floor_contact']), ('beam', 'cheney2013', 'voxelyze'))
        self.assertEqual((a['actuation_frequency'], a['actuation_amplitude']), (40.0, 0.14))
        self.assertEqual((a['simulation_time'], a['settle_time']), (0.25, 0.0))
        self.assertEqual((a['direction'], a['divide_by'], a['workspace_voxels']), ('any', 'workspace', 10))
        self.assertEqual((a['poisson'], a['global_damping'], a['fitness_mode']), (False, 0.001, 'forward'))
        self.assertEqual(a['friction'], {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01})
        self.assertEqual(a['early_term_threshold'], ts.NO_EARLY_STOP)
        self.assertIsNone(ts.evaluator_arguments(early_stop=True)['early_term_threshold'])

    def test_a_setting_the_script_does_not_know_stops_it(self):
        import run_tendon_evolution as runner
        original = runner._PRESETS[ts.PRESET]
        runner._PRESETS[ts.PRESET] = original + [('something_new', 1)]
        try:
            with self.assertRaises(SystemExit) as stop:
                ts.evaluator_arguments()
            self.assertIn('something_new', str(stop.exception))
        finally:
            runner._PRESETS[ts.PRESET] = original

    def test_workers_get_what_the_search_gives_them(self):
        p = ts.worker_parameters(ts.evaluator_arguments())
        self.assertEqual(p['materials'], 'cheney2013')
        self.assertEqual(p['early_term_threshold'], ts.NO_EARLY_STOP)
        self.assertEqual(p['voxel_size'], 0.01)
        json.dumps(p)                                         # plain values only


class TestScoringOneBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = ts.worker_parameters(ts.evaluator_arguments())
        cls.result = ts.score_one(('a', small_body(), cls.params, 1.0))

    def test_it_is_the_evaluation_of_the_search(self):
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        evaluator = MuJoCoTendonEvaluator(**ts.evaluator_arguments())
        try:
            self.assertEqual(self.result['score'], evaluator.evaluate_single(small_body()))
        finally:
            evaluator.close()

    def test_what_is_recorded(self):
        r = self.result
        self.assertIsNone(r['error'])
        self.assertFalse(r['blew_up'])
        self.assertGreater(r['score'], 0)
        self.assertTrue(r['consistent'])                      # the score is the distance moved
        self.assertAlmostEqual(float(np.linalg.norm(r['moved'])), r['score'], places=9)
        self.assertEqual(r['time_step'], r['normal_time_step'])
        self.assertEqual(r['steps'], int(0.25 / r['time_step']))
        self.assertTrue(-0.5 < r['sunk'] < 1.0)

    def test_a_shorter_time_step(self):
        r = ts.score_one(('b', small_body(), self.params, 0.5))
        self.assertAlmostEqual(r['time_step'], 0.5 * self.result['time_step'], places=12)
        self.assertEqual(r['normal_time_step'], self.result['time_step'])
        self.assertIn(r['steps'], (2 * self.result['steps'], 2 * self.result['steps'] + 1))
        self.assertGreater(r['score'], 0)

    def test_a_body_started_at_a_height_falls_that_far(self):
        """Section 9.4, point 9: the engine's own initial_height starts a body in the air, as the
        2013 simulator does with a body that does not touch the bottom of the workspace."""
        r = ts.score_one(('d', small_body(), dict(self.params, initial_height=0.02), 1.0))     # two voxels up
        self.assertIsNone(r['error'])
        self.assertTrue(r['consistent'])
        self.assertAlmostEqual(r['moved'][2], self.result['moved'][2] - 0.2, delta=0.03)       # in workspace widths
        self.assertGreater(r['score'], 0.15)

    def test_a_body_the_engine_cannot_build_scores_zero_and_says_why(self):
        r = ts.score_one(('c', np.zeros((10, 10, 10), np.int8), self.params, 1.0))
        self.assertEqual(r['score'], 0.0)
        self.assertIn('No voxels', r['error'])


class TestAgainstARealRunOfTheSearch(unittest.TestCase):
    def test_every_robot_of_a_preset_run_gets_the_score_the_run_gave_it(self):
        """The search's own command line under --preset cheney2013, then every robot of its final
        population scored here with the search's early stop left on: the same numbers. This is
        what entitles the script to say it scores in 'the MuJoCo engine with the preset'."""
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py'), '--preset', 'cheney2013',
                                '--no-age-pareto', '--gen', '1', '--pop', '4', '--workers', '1', '--grid-size', '5',
                                '--seed', '3', '--name', 'preset_run'], cwd=tmp, capture_output=True, text=True, timeout=1800)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            with open(os.path.join(tmp, 'results', 'preset_run', 'final_population.pkl'), 'rb') as f:
                population = pickle.load(f)
        params = ts.worker_parameters(ts.evaluator_arguments(early_stop=True, workspace=5))
        fitnesses = [float(v) for v in population['fitnesses']]
        self.assertGreater(max(fitnesses), 0)
        for i, (genome, fitness) in enumerate(zip(population['genomes'], fitnesses)):
            self.assertEqual(ts.score_one((str(i), np.asarray(genome), params, 1.0))['score'], fitness)


class TestReadingChampions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.tmp.name
        self.results, self.outcomes, self.deposit = (os.path.join(t, d) for d in ('results', 'outcomes', 'deposit'))
        self.replay = os.path.join(t, 'replay.csv')
        os.makedirs(self.outcomes)
        per_seed, self.bodies = [], {}
        for seed in (1, 2, 3):
            body = small_body(seed)
            name = robot_name(f'armR_P0_s{seed}', 2.0 + seed, int((body != 0).sum()))
            folder = os.path.join(self.results, f'armR_P0_s{seed}')
            os.makedirs(folder)
            with tarfile.open(os.path.join(folder, 'Gen_1000.tgz'), 'w:gz') as tar:
                for member, grid in ((name, body), (robot_name('other', 0.5, 3), small_body(seed + 5))):
                    data = robot_text(grid).encode()
                    info = tarfile.TarInfo(f'Gen_1000/{member}')
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            per_seed.append({'seed': seed, 'champion': {'file': name, 'original': 2.0 + seed,
                                                        'body': {'voxels': int((body != 0).sum())}}})
            self.bodies[seed] = body
        with open(os.path.join(self.outcomes, 'arm_R.json'), 'w') as f:
            json.dump({'per_seed': per_seed}, f)
        rows = []
        for k, run in enumerate(('run_1', 'run_2', 'run_3')):
            body = small_body(k + 10)
            folder = os.path.join(self.deposit, '2013-01-16-10^3-noCost', run, 'Gen_1000')
            os.makedirs(folder)
            for fitness, grid in ((3.0 + k, body), (1.0, small_body(k + 20))):
                name = robot_name('foo', fitness, int((grid != 0).sum()))
                with open(os.path.join(folder, name), 'w') as f:
                    f.write(robot_text(grid))
                rows.append({'condition': '2013-01-16-10^3-noCost', 'run': run, 'file': name,
                             'final_com_dist_m': f'{(fitness - 0.25) * 0.01:.7f}'})
            self.bodies[run] = body
        with open(self.replay, 'w', newline='') as f:
            w = csv.DictWriter(f, ['condition', 'run', 'file', 'final_com_dist_m'])
            w.writeheader()
            w.writerows(rows)

    def test_an_arms_champions_come_from_its_report(self):
        champions = ts.arm_champions('R', self.results, self.outcomes)
        self.assertEqual([c['label'] for c in champions], ['seed 1', 'seed 2', 'seed 3'])
        self.assertEqual([c['evolved'] for c in champions], [3.0, 4.0, 5.0])
        for seed, c in zip((1, 2, 3), champions):
            self.assertTrue((c['grid'] == self.bodies[seed]).all())
            self.assertIsNone(c['recorded_2013'])

    def test_an_arm_without_a_report_has_no_champions(self):
        self.assertIsNone(ts.arm_champions('Rc', self.results, self.outcomes))

    def test_a_body_that_is_not_the_reported_one_stops_it(self):
        with open(os.path.join(self.outcomes, 'arm_R.json')) as f:
            report = json.load(f)
        report['per_seed'][0]['champion']['body']['voxels'] += 1
        with open(os.path.join(self.outcomes, 'arm_R.json'), 'w') as f:
            json.dump(report, f)
        with self.assertRaises(SystemExit):
            ts.arm_champions('R', self.results, self.outcomes)

    def test_deposited_champions_take_their_score_from_this_campaigns_build(self):
        champions = ts.deposited_champions('noCost', self.deposit, self.replay)
        self.assertEqual([c['label'] for c in champions], ['run_1', 'run_2', 'run_3'])
        self.assertEqual([c['recorded_2013'] for c in champions], [3.0, 4.0, 5.0])
        for c, expected in zip(champions, (2.75, 3.75, 4.75)):
            self.assertAlmostEqual(c['evolved'], expected, places=6)
        self.assertTrue((champions[1]['grid'] == self.bodies['run_2']).all())

    def test_a_deposited_champion_missing_from_the_replay_stops_it(self):
        with open(self.replay, 'w', newline='') as f:
            csv.DictWriter(f, ['condition', 'run', 'file', 'final_com_dist_m']).writeheader()
        with self.assertRaises(SystemExit):
            ts.deposited_champions('noCost', self.deposit, self.replay)

    def test_rehearsal_reads_runs_that_are_not_an_arm(self):
        for seed in (1, 2, 3):
            folder = os.path.join(self.results, f'armR_P0_s{seed}')
            with open(os.path.join(folder, 'curve.txt'), 'w') as f:
                f.write('0 1.0\n')
        champions = ts.rehearsal_champions('armR_P0_s', 1000, self.results)
        self.assertEqual([c['label'] for c in champions], ['seed 1', 'seed 2', 'seed 3'])
        self.assertTrue((champions[2]['grid'] == self.bodies[3]).all())

    def run_main(self, arm, differs):
        out = io.StringIO()
        with mock.patch('search_arm.code_differs_from_tag', return_value=differs), contextlib.redirect_stdout(out):
            code = ts.main(['--arms', arm, '--results-dir', self.results, '--outcomes-dir', self.outcomes,
                            '--out-dir', os.path.join(self.tmp.name, 'out'), '--cache',
                            os.path.join(self.tmp.name, 'cache.json')])
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'cache.json')))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'out')))
        return code, out.getvalue()

    def test_an_arm_that_was_not_analysed_is_refused(self):
        code, said = self.run_main('Rc', None)
        self.assertEqual(code, 2)
        self.assertIn('has not been analysed', said)
        self.assertIn('Nothing was computed', said)

    def test_an_engine_that_is_not_the_campaigns_is_refused(self):
        code, said = self.run_main('R', 'run_tendon_evolution.py or src/ differ from the code tagged campaign-v2.')
        self.assertEqual(code, 2)
        self.assertIn('differ from the code tagged', said)
        self.assertIn('Nothing was computed', said)


class TestKeepingWhatWasScored(unittest.TestCase):
    def test_nothing_is_scored_twice(self):
        calls = []

        def fake(job):
            calls.append(job[0])
            return {'key': job[0], 'score': 1.0, 'blew_up': False, 'error': None, 'seconds': 0.0}

        with tempfile.TemporaryDirectory() as tmp:
            cache = os.path.join(tmp, 'sub', 'cache.json')
            jobs = [(k, None, {}, 1.0, k) for k in ('a', 'b')]
            first = ts.evaluate_all(jobs, 1, cache, evaluate=fake, say=lambda *_: None)
            self.assertEqual(sorted(calls), ['a', 'b'])
            again = ts.evaluate_all(jobs + [('c', None, {}, 0.25, 'c')], 1, cache, evaluate=fake, say=lambda *_: None)
            self.assertEqual(sorted(calls), ['a', 'b', 'c'])
            self.assertEqual(first['a'], again['a'])
            self.assertEqual(sorted(again), ['a', 'b', 'c'])

    def test_no_more_workers_than_the_memory_allows(self):
        """25 November 2026: fourteen workers on champion-sized bodies used up the machine's memory
        while an arm was running, and 86 evaluations failed. The number of workers now follows the
        memory that is free, and a failed allocation stops a run instead of counting as a score."""
        quiet = lambda *_: None
        per, keep = ts.GB_PER_WORKER, ts.KEEP_FREE_GB
        self.assertEqual(ts.workers_that_fit(10, free=keep + 4 * per + 0.5, say=quiet), 4)
        self.assertEqual(ts.workers_that_fit(3, free=keep + 40 * per, say=quiet), 3)
        with mock.patch.object(ts, 'free_commit_gb', return_value=None):      # a system that cannot be asked
            self.assertEqual(ts.workers_that_fit(5, say=quiet), 5)
        with self.assertRaises(SystemExit) as stop:
            ts.workers_that_fit(4, free=keep + 0.5 * per, say=quiet)
        self.assertIn('Nothing was started', str(stop.exception))
        if sys.platform.startswith('win'):
            self.assertGreater(ts.free_commit_gb(), 0)

    def test_running_out_of_memory_is_not_a_score(self):
        self.assertTrue(ts.out_of_memory(MemoryError('Unable to allocate 4.02 MiB for an array')))
        self.assertTrue(ts.out_of_memory(ValueError('Error: engine error: Could not allocate memory')))
        self.assertFalse(ts.out_of_memory(ValueError('No voxels in grid!')))
        from src.evolution import mujoco_tendon_evaluator as evaluation
        params = ts.worker_parameters(ts.evaluator_arguments())
        with mock.patch.object(evaluation, '_make_engine', side_effect=MemoryError('Unable to allocate 1 GiB')):
            with self.assertRaises(RuntimeError) as stop:
                ts.score_one(('k', small_body(), params, 1.0))
        self.assertIn('out of memory', str(stop.exception))

    def test_the_key_follows_body_settings_and_step(self):
        p = {'a': 1}
        k = ts.evaluation_key(small_body(), p, 1.0, 'tag')
        self.assertEqual(k, ts.evaluation_key(small_body(), dict(p), 1.0, 'tag'))
        self.assertNotEqual(k, ts.evaluation_key(small_body(1), p, 1.0, 'tag'))
        self.assertNotEqual(k, ts.evaluation_key(small_body(), {'a': 2}, 1.0, 'tag'))
        self.assertNotEqual(k, ts.evaluation_key(small_body(), p, 0.25, 'tag'))
        self.assertNotEqual(k, ts.evaluation_key(small_body(), p, 1.0, 'other'))


def rows(evolved, scores, name='arm_R', recorded=False):
    return [{'set': name, 'label': f'seed {i + 1}', 'evolved': e, 'score': s, 'ratio': s / e, 'blew_up': False,
             'error': None, 'recorded_2013': (e * 1.25 if recorded else None), 'moved': [s, 0.0, 0.0], 'sunk': 0.1,
             'time_step': 1e-5} for i, (e, s) in enumerate(zip(evolved, scores))]


class TestStatistics(unittest.TestCase):
    def test_median_interval(self):
        self.assertEqual(ps.median_interval([2.0] * 9), (2.0, 2.0, 2.0))
        m, lo, hi = ps.median_interval(np.arange(1.0, 36.0))
        self.assertEqual(m, 18.0)
        self.assertTrue(lo < 18.0 < hi and lo >= 1.0 and hi <= 35.0)
        self.assertEqual(ps.median_interval(np.arange(1.0, 36.0)), (m, lo, hi))       # the seed is fixed

    def test_rank_correlation(self):
        a = np.arange(1.0, 21.0)
        for value in ps.rank_correlation(a, a ** 3, n=200):
            self.assertAlmostEqual(value, 1.0)
        rho, lo, hi = ps.rank_correlation(a, -a, n=200)
        self.assertAlmostEqual(rho, -1.0)
        self.assertAlmostEqual(hi, -1.0)
        rng = np.random.default_rng(1)
        rho, lo, hi = ps.rank_correlation(a, rng.normal(size=20), n=500)
        self.assertTrue(lo < rho < hi and lo < 0 < hi)
        self.assertTrue(np.isnan(ps.rank_correlation(a, np.ones(20), n=50)[0]))       # nothing to rank
        with self.assertRaises(ValueError):
            ps.rank_correlation([1, 2, 3], [1, 2])

    def test_one_set(self):
        s = ts.summarise(rows([2.0, 4.0, 5.0, 8.0, 10.0], [1.0, 2.0, 5.0, 4.0, 15.0], recorded=True), n_boot=500)
        self.assertEqual((s['n'], s['blew_up'], s['failed']), (5, 0, 0))
        self.assertEqual(s['ratio'][0], 0.5)                  # ratios 0.5 0.5 1.0 0.5 1.5
        self.assertEqual(s['kept_all_or_more'], 2)
        self.assertEqual(s['evolved'][0], 5.0)
        self.assertEqual(s['score'][0], 4.0)
        self.assertTrue(s['ratio_median_interval'][0] <= 0.5 <= s['ratio_median_interval'][1])
        self.assertAlmostEqual(s['rank_correlation'], 0.9)
        self.assertEqual(s['recorded_2013'][0], 6.25)
        self.assertAlmostEqual(s['ratio_to_recorded_2013'][0], 0.4)
        self.assertEqual(s['vertical_share'][0], 0.0)

    def test_blow_ups_stay_in_the_statistics(self):
        r = rows([2.0, 4.0, 6.0], [1.0, 0.0, 3.0])
        r[1]['blew_up'] = True
        s = ts.summarise(r, n_boot=200)
        self.assertEqual((s['n'], s['blew_up']), (3, 1))
        self.assertEqual(sorted(x['ratio'] for x in r), [0.0, 0.5, 0.5])

    def test_two_sets_that_are_the_same_do_not_differ(self):
        x = rows([2.0, 4.0, 6.0, 8.0], [1.0, 3.0, 2.0, 8.0])
        c = ts.compare_sets(x, x, n_boot=200)
        self.assertEqual(c['a12'], 0.5)
        self.assertGreater(c['p'], 0.99)
        self.assertNotIn('ratio_of_medians', c)

    def test_the_report(self):
        """Made-up evaluations through the whole report: sets, comparison, step check, text, CSV."""
        sets, results, keys = {}, {}, {}
        for name, evolved, scores, recorded in (('arm_R', [4.0, 5.0, 6.0, 7.0], [2.0, 5.5, 3.0, 3.5], None),
                                                ('deposit_noCost', [4.0, 4.4, 5.0, 6.0], [3.0, 2.2, 4.0, 3.0], 1.1)):
            sets[name] = []
            for i, (e, s) in enumerate(zip(evolved, scores)):
                label = f'seed {i + 1}' if recorded is None else f'run_{i + 1}'
                sets[name].append({'set': name, 'label': label, 'file': f'{label}.vxa', 'evolved': e,
                                   'recorded_2013': None if recorded is None else e * recorded, 'grid': small_body(i)})
                for which in (('floor', 'short') if i < 2 else ('floor',)):
                    key = f'{name}/{label}/{which}'
                    keys[(name, label, which)] = key
                    results[key] = {'key': key, 'score': s * (1.0 if which == 'floor' else 1.1), 'blew_up': False,
                                    'error': None, 'moved': [s, 0.0, 0.0], 'time_step': 1e-5, 'steps': 100,
                                    'sunk': 0.12, 'consistent': True, 'seconds': 1.0}
        # one champion of the arm does not touch the bottom and has a second evaluation, started at its height
        keys[('arm_R', 'seed 3', 'placed')] = 'placed'
        results['placed'] = {'key': 'placed', 'score': 9.0, 'blew_up': False, 'error': None, 'moved': [8.9, 0.0, -0.3],
                             'time_step': 1e-5, 'steps': 100, 'sunk': 0.2, 'consistent': True, 'seconds': 1.0}
        report = ts.build_report(sets, results, keys, n_boot=300, arms=('R',))
        self.assertEqual(list(report['sets']), ['arm_R', 'deposit_noCost'])
        self.assertEqual(report['sets']['arm_R']['ratio'][0], 0.5)                    # 0.5 1.1 0.5 0.5
        self.assertEqual([(c['set'], c['reference']) for c in report['comparisons']], [('arm_R', 'deposit_noCost')])
        self.assertEqual(report['off_the_floor'], {'arm_R': 1, 'deposit_noCost': 0})
        self.assertAlmostEqual(report['sets_as_placed']['arm_R']['ratio'][0], 0.8)    # 0.5 1.1 1.5 0.5
        self.assertEqual(report['sets_as_placed']['deposit_noCost'], report['sets']['deposit_noCost'])
        self.assertEqual([(c['set'], c['reference']) for c in report['comparisons_as_placed']],
                         [('arm_R', 'deposit_noCost')])
        self.assertEqual(report['champions'][2]['score'], 3.0)                        # the floor score is untouched
        self.assertEqual(len(report['step_check']), 4)
        for r in report['step_check']:
            self.assertAlmostEqual(r['change'], 0.1)
        self.assertEqual(report['champions'][0]['lowest_layer'], 0)
        self.assertEqual(report['champions'][0]['voxels'], int((small_body() != 0).sum()))
        report.update(title='TITLE', notes=['a note'], made='now', code='code',
                      settings={'n_boot': 300, 'seed': 0})
        text = ts.render(report)
        for expected in ('TITLE', 'NOTE: a note', 'arm R against deposited 2013, no cost', 'TIME-STEP CHECK',
                         'PER CHAMPION', '+10.0%', 'deposited 2013, no cost', 'started where it is in the workspace',
                         'arm R 1 of 4'):
            self.assertIn(expected, text)
        with tempfile.TemporaryDirectory() as tmp:
            ts.write_csv(os.path.join(tmp, 'c.csv'), report['champions'])
            with open(os.path.join(tmp, 'c.csv'), newline='') as f:
                table = list(csv.DictReader(f))
        self.assertEqual(len(table), 8)
        self.assertEqual(float(table[0]['ratio']), 0.5)
        self.assertEqual(float(table[0]['score_short_step']), 2.2)
        self.assertEqual(table[3]['score_short_step'], '')
        self.assertEqual((float(table[2]['score_as_placed']), float(table[2]['ratio_as_placed'])), (9.0, 1.5))
        self.assertEqual(table[0]['score_as_placed'], '')

    def test_no_body_off_the_floor_no_second_table(self):
        sets = {'arm_R': [{'set': 'arm_R', 'label': f'seed {i}', 'file': 'f', 'evolved': 2.0, 'recorded_2013': None,
                           'grid': small_body(i)} for i in range(3)]}
        keys = {('arm_R', f'seed {i}', 'floor'): str(i) for i in range(3)}
        results = {str(i): {'key': str(i), 'score': 1.0 + i, 'blew_up': False, 'error': None, 'moved': None,
                            'time_step': 1e-5, 'steps': 1, 'sunk': None, 'consistent': None, 'seconds': 0.0}
                   for i in range(3)}
        report = ts.build_report(sets, results, keys, n_boot=100)
        self.assertNotIn('sets_as_placed', report)
        self.assertEqual(report['comparisons'], [])

    def test_lowest_layer_and_as_placed(self):
        g = np.zeros((10, 10, 10), np.int8)
        g[3, 3, 2:5] = 1
        self.assertEqual(ts.lowest_layer(g), 2)
        self.assertEqual(ts.lowest_layer(small_body()), 0)
        floor = {'label': 'a', 'score': 1.0, 'ratio': 0.5, 'blew_up': False, 'error': None, 'moved': [1, 0, 0], 'sunk': 0.1}
        both = dict(floor, label='b', placed={'score': 3.0, 'ratio': 1.5, 'blew_up': True, 'error': None,
                                              'moved': [2, 0, -1], 'sunk': 0.3, 'consistent': True, 'seconds': 1.0})
        placed = ts.as_placed([floor, both])
        self.assertIs(placed[0], floor)
        self.assertEqual((placed[1]['score'], placed[1]['ratio'], placed[1]['blew_up']), (3.0, 1.5, True))
        self.assertEqual(both['score'], 1.0)                  # the rows given are not changed

    def test_arm_a_is_also_set_against_arm_r(self):
        sets, results, keys = {}, {}, {}
        for name in ('arm_A', 'deposit_noCost', 'arm_R'):
            sets[name] = []
            for i in range(3):
                label = f'seed {i + 1}'
                sets[name].append({'set': name, 'label': label, 'file': 'f', 'evolved': 2.0 + i, 'recorded_2013': None,
                                   'grid': small_body(i)})
                keys[(name, label, 'floor')] = f'{name}{i}'
                results[f'{name}{i}'] = {'key': f'{name}{i}', 'score': 1.0 + i, 'blew_up': False, 'error': None,
                                         'moved': None, 'time_step': 1e-5, 'steps': 1, 'sunk': None, 'consistent': None,
                                         'seconds': 0.0}
        report = ts.build_report(sets, results, keys, n_boot=100, arms=('A',))
        self.assertEqual([(c['set'], c['reference']) for c in report['comparisons']],
                         [('arm_A', 'deposit_noCost'), ('arm_A', 'arm_R')])

    def test_against_the_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'd.json')
            with open(path, 'w') as f:
                json.dump({'his': [5.0, 6.25, 7.5], 'configs': {'D settings': {'ours': [1.0, 2.0, 3.5]}},
                           'cost_D': {'his': [1.0], 'ours': [1.0]}}, f)
            found = ts.against_diagnostic({'deposit_noCost': rows([4.0, 5.0, 6.0], [1.0, 2.0, 3.0], recorded=True)}, path)
            self.assertEqual(found, {'deposit_noCost': {'compared': 3, 'identical': 2, 'largest_difference': 0.5}})
            self.assertIsNone(ts.against_diagnostic({'arm_R': rows([4.0], [1.0])}, path))
            self.assertIsNone(ts.against_diagnostic({}, os.path.join(tmp, 'missing.json')))


if __name__ == '__main__':
    unittest.main()
