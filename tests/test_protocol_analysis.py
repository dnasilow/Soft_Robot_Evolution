"""The analysis of the frozen protocol (paper/analysis/): its statistics, its readers, its refusal
to analyse an incomplete arm, and a dress rehearsal on arms built from the deposited 2013 data.
No run of any campaign arm is read here."""
import contextlib
import glob
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

import numpy as np
from scipy.stats import mannwhitneyu

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
import analyse_arm as aa            # noqa: E402
import protocol_stats as ps         # noqa: E402
from src.evolution import cheney2013 as c13   # noqa: E402

HAVE_DEPOSIT = os.path.isdir(os.path.join(aa.DEPOSITED_ROBOTS, '2013-01-16-10^3-noCost')) and os.path.exists(
    os.path.join(ROOT, 'research_reference', 'DRYAD_CheneyEtALL', 'softbots2013GenchampData.tgz'))


class TestStatistics(unittest.TestCase):
    def test_a12_known_values(self):
        self.assertEqual(ps.a12([5, 6, 7], [1, 2, 3]), 1.0)
        self.assertEqual(ps.a12([1, 2, 3], [5, 6, 7]), 0.0)
        self.assertEqual(ps.a12([1, 2, 3], [1, 2, 3]), 0.5)
        self.assertAlmostEqual(ps.a12([1, 2, 3], [2]), 0.5)
        self.assertAlmostEqual(ps.a12([3, 4], [1, 3, 5]), (1 + 0.5 + 2) / 6)

    def test_holm_known_example(self):
        self.assertEqual([round(v, 10) for v in ps.holm([0.01, 0.04, 0.03, 0.005])], [0.03, 0.06, 0.06, 0.02])
        self.assertEqual(ps.holm([0.5, 0.9]), [1.0, 1.0])
        self.assertEqual(ps.holm([0.2]), [0.2])

    def test_holm_stays_inside_its_range_whatever_the_rest_of_the_family_is(self):
        rng = np.random.default_rng(3)
        for _ in range(300):
            p = float(rng.uniform(0, 0.3))
            others = rng.uniform(0, 1, ps.FAMILY - 1) ** rng.integers(1, 6)
            lo, hi = ps.holm_range(p)
            adjusted = ps.holm([p] + list(others))[0]
            self.assertGreaterEqual(adjusted, lo - 1e-12)
            self.assertLessEqual(adjusted, hi + 1e-12)

    def test_verdict_is_read_three_ways(self):
        self.assertEqual(ps.verdict((0.93, 1.06)), 'reproduces')
        self.assertEqual(ps.verdict((0.90, 1.10)), 'reproduces')
        self.assertEqual(ps.verdict((1.02, 1.08)), 'reproduces')            # inside the window is what was fixed
        self.assertEqual(ps.verdict((0.88, 1.06)), 'not distinguishable')
        self.assertEqual(ps.verdict((0.95, 1.12)), 'not distinguishable')
        self.assertEqual(ps.verdict((0.70, 0.89)), 'differs')
        self.assertEqual(ps.verdict((1.11, 1.30)), 'differs')
        self.assertEqual(ps.verdict((0.80, 0.95)), 'differs')              # excludes 1, partly inside the window

    def test_bootstrap_is_the_formula_of_the_pilot_summary(self):
        rng = np.random.default_rng(11)
        x, y = rng.normal(4, 0.6, 12), rng.normal(4.4, 0.7, 35)
        r = np.random.default_rng(0)
        direct = [np.median(r.choice(x, len(x))) / np.median(r.choice(y, len(y))) for _ in range(10000)]
        lo, hi = ps.bootstrap_interval(ps.ratio_of_medians, x, y)
        self.assertEqual((lo, hi), (float(np.percentile(direct, 2.5)), float(np.percentile(direct, 97.5))))
        self.assertEqual((lo, hi), ps.bootstrap_interval(ps.ratio_of_medians, x, y))       # same seed, same result
        self.assertNotEqual((lo, hi), ps.bootstrap_interval(ps.ratio_of_medians, x, y, seed=1))

    def test_compare_reports_what_the_protocol_asks(self):
        rng = np.random.default_rng(5)
        x, y = rng.normal(4, 0.5, 35), rng.normal(4, 0.5, 35)
        c = ps.compare(x, y, n_boot=500)
        self.assertEqual((c['n_arm'], c['n_reference']), (35, 35))
        self.assertEqual(c['arm_median'], float(np.median(x)))
        self.assertEqual(c['ratio_of_medians'], float(np.median(x) / np.median(y)))
        self.assertEqual(c['p'], float(mannwhitneyu(x, y, alternative='two-sided').pvalue))
        self.assertLessEqual(c['ratio_interval'][0], c['ratio_of_medians'])
        self.assertGreaterEqual(c['ratio_interval'][1], c['ratio_of_medians'])
        self.assertLessEqual(c['a12_interval'][0], c['a12'])
        self.assertGreaterEqual(c['a12_interval'][1], c['a12'])
        self.assertNotIn('ratio_of_medians', ps.compare(x, y, n_boot=200, with_ratio=False))

    def test_identical_and_shifted_samples(self):
        y = np.linspace(4.0, 4.6, 35)
        same = ps.compare(y, y, n_boot=2000)
        self.assertEqual(same['ratio_of_medians'], 1.0)
        self.assertEqual(same['a12'], 0.5)
        self.assertEqual(ps.verdict(same['ratio_interval']), 'reproduces')
        lower = ps.compare(0.7 * y, y, n_boot=2000)
        self.assertAlmostEqual(lower['ratio_of_medians'], 0.7)
        self.assertEqual(ps.verdict(lower['ratio_interval']), 'differs')
        self.assertLess(lower['p'], 1e-6)

    def test_two_proportions(self):
        self.assertEqual(ps.two_proportions(1, 35, 1, 35)['p'], 1.0)
        self.assertLess(ps.two_proportions(12, 35, 0, 35)['p'], 0.001)
        self.assertEqual(ps.two_proportions(2, 35, 1, 35)['arm_yes'], 2)

    def test_attainability_knows_a_tight_reference_from_a_wide_one(self):
        tight = np.linspace(4.00, 4.08, 35)
        wide = np.concatenate([np.full(17, 2.0), [3.0], np.full(17, 4.0)])
        self.assertEqual(ps.attainability(tight, 35, trials=60, n_boot=300), 1.0)
        self.assertEqual(ps.attainability(wide, 35, trials=60, n_boot=300), 0.0)
        self.assertEqual(ps.attainability(tight, 35, trials=30, n_boot=200, seed=4),
                         ps.attainability(tight, 35, trials=30, n_boot=200, seed=4))

    def test_read_as_different_knows_no_difference_from_a_large_one(self):
        y = np.linspace(3.0, 4.4, 35)
        same = ps.read_as_different(y, 3, 10, 1.0, trials=200, n_boot=300)
        self.assertLess(same['interval_excludes_1'], 0.25)                  # false alarms: some, not many
        self.assertLessEqual(same['p_below_0.05'], 0.12)
        far = ps.read_as_different(y, 3, 10, 0.4, trials=200, n_boot=300)   # every drawn run below every other
        self.assertEqual((far['interval_excludes_1'], far['p_below_0.05']), (1.0, 1.0))
        self.assertEqual(ps.read_as_different(y, 3, None, 0.4, trials=100, n_boot=300)['interval_excludes_1'], 1.0)
        self.assertEqual(same, ps.read_as_different(y, 3, 10, 1.0, trials=200, n_boot=300))    # same seed, same result
        self.assertNotEqual(same, ps.read_as_different(y, 3, 10, 1.0, trials=200, n_boot=300, seed=7))

    def test_drawn_runs_have_no_ties_so_the_test_is_the_exact_one(self):
        """Three runs drawn from the reference and set against it: without the tie-breaking every
        drawn run would equal a reference run, and SciPy would leave its exact test."""
        y = np.linspace(3.0, 4.4, 35)
        calls = []
        real = ps.mannwhitneyu

        def watching(x, other, **kw):
            calls.append(len(set(np.asarray(x).tolist()) & set(np.asarray(other).tolist())) + len(x) - len(set(x.tolist())))
            return real(x, other, **kw)
        with mock.patch.object(ps, 'mannwhitneyu', watching):
            ps.read_as_different(y, 3, None, 1.0, trials=40, n_boot=50)
        self.assertEqual((len(calls), sum(calls)), (40, 0))

    def test_the_smallest_p_of_three_runs(self):
        y = np.linspace(3.0, 4.4, 35)
        self.assertAlmostEqual(ps.smallest_p(3, 35), 2 / 8436)
        self.assertAlmostEqual(ps.smallest_p(3, 10), 2 / 286)
        # three runs above every reference run: the analysis' own comparison gives exactly that p
        self.assertAlmostEqual(ps.compare([5.0, 5.1, 5.2], y, n_boot=200)['p'], ps.smallest_p(3, 35))
        self.assertAlmostEqual(ps.compare([1.0, 1.1, 1.2], y[:10], n_boot=200)['p'], ps.smallest_p(3, 10))


def robot_text(grid):
    return '<x>' + ''.join(f'<Layer><![CDATA[{row}]]></Layer>' for row in c13.layer_rows(grid)) + '</x>'


def robot_name(tag, generation, n, adjusted, original, filled=100):
    return (f'Softbots--{tag}--Gen_{generation:04d}--Ind_0x{n:07x}--adjFit_{adjusted:.8f}--numFilled_{filled:04d}'
            f'--origFit_{original:.8f}_genome.vxa')


class TestReading(unittest.TestCase):
    def test_curve_is_read_as_best_so_far_of_column_two(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'curve.txt')
            with open(path, 'w') as f:
                f.write('# 1. generation\n# 2. genChamp Original Fitness\n\n1 0.5 0.4 0.1 0.1 \n2 0.9 0.7 0.2 0.2 \n'
                        '3 0.8 0.75 0.2 0.2 \n4 1.25 0.9 0.3 0.3 \n')
            raw, best = aa.read_curve(path)
        self.assertEqual(raw.tolist(), [0.5, 0.9, 0.8, 1.25])
        self.assertEqual(best.tolist(), [0.5, 0.9, 0.9, 1.25])

    def test_robot_names_of_the_deposit_and_of_the_reruns(self):
        a = aa.robot_info('Softbots--foo--Gen_1000--Ind_0x17da420--adjFit_4.63638020--numFilled_0626--origFit_4.63638020_genome.vxa')
        self.assertEqual((a['adjusted'], a['original'], a['filled']), (4.6363802, 4.6363802, 626))
        b = aa.robot_info('Gen_0010/Softbots--det_P0_s1--Gen_0010--Ind_0x5c1e4e970990--adjFit_0.00010000--numFilled_0000--origFit_0.00100000_genome.vxa')
        self.assertEqual((b['adjusted'], b['original'], b['filled']), (0.0001, 0.001, 0))
        self.assertIsNone(aa.robot_info('fitness.xml'))

    def test_champion_is_the_highest_adjusted_fitness(self):
        names = [robot_name('t', 1000, 3, 2.0, 5.0), robot_name('t', 1000, 1, 3.0, 3.5), robot_name('t', 1000, 2, 3.0, 4.0),
                 'notes.txt']
        champion = aa.pick_champion(names)
        self.assertEqual(champion['adjusted'], 3.0)                  # not the one with the highest ORIGINAL fitness
        self.assertEqual(champion['file'], robot_name('t', 1000, 1, 3.0, 3.5))    # tie: first name in sorted order
        self.assertIsNone(aa.pick_champion(['a.txt']))

    def test_body_measures_of_a_known_body(self):
        g = np.zeros((10, 10, 10), np.int8)
        g[2:6, 2:6, 1] = 1            # a slab of 16 muscle voxels (phase 1) one layer up ...
        g[2, 2, 0] = 3                # ... standing on two separate feet: one soft,
        g[5, 5, 0] = 2                # one muscle (phase 2)
        m = aa.body_measures(robot_text(g))
        self.assertEqual((m['voxels'], m['footprint'], m['feet'], m['two_feet']), (18, 2, 2, True))
        self.assertAlmostEqual(m['muscle'], 17 / 18)
        self.assertAlmostEqual(m['fill'], 18 / (4 * 4 * 2))
        g[3:5, 3:5, 0] = 4            # fill the gap between the feet's corners? no: a separate stiff patch
        self.assertEqual(aa.body_measures(robot_text(g))['feet'], 3)
        g[2:6, 2:6, 0] = 4            # one solid bottom layer: one foot
        m = aa.body_measures(robot_text(g))
        self.assertEqual((m['feet'], m['two_feet'], m['footprint']), (1, False, 16))
        self.assertIsNone(aa.body_measures(robot_text(np.zeros((10, 10, 10), np.int8))))


class TestQuickSummaryAgrees(unittest.TestCase):
    """summarise_reruns.py is what the launcher prints when an arm ends. It must load, and it must
    take the runs in seed order so that its interval is the one of the protocol analysis."""

    def test_it_loads_and_orders_runs_by_seed_number(self):
        import summarise_reruns as sr
        folders = ['x/armR_P0_s10', 'x/armR_P0_s2', 'x/armR_P0_s1', 'x/armR_P0_s35', 'x/armR_P0_launcher.log']
        self.assertEqual(sorted(folders, key=sr.run_order),
                         ['x/armR_P0_launcher.log', 'x/armR_P0_s1', 'x/armR_P0_s2', 'x/armR_P0_s10', 'x/armR_P0_s35'])
        self.assertEqual(sr.a12([3, 4], [1, 3, 5]), ps.a12([3, 4], [1, 3, 5]))

    def test_p_values_are_printed_readably(self):
        self.assertEqual(aa.pv(0.3602), '0.3602')
        self.assertEqual(aa.pv(0.0001), '0.0001')
        self.assertEqual(aa.pv(3.2e-9), '3.2e-09')


def make_run(root, prefix, seed, scores, robots=None, generations=1000, finished=True, failed=None):
    """A collected run folder like collect_2013_runs.sh leaves it. scores: champion's original
    fitness per generation (a list, or a function of the generation)."""
    d = os.path.join(root, f'{prefix}{seed}')
    os.makedirs(d)
    with open(os.path.join(d, 'curve.txt'), 'w') as f:
        f.write('# 1. generation\n# 2. genChamp Original Fitness\n\n')
        for g in range(1, generations + 1):
            v = scores(g) if callable(scores) else scores[g - 1]
            f.write(f'{g} {v:.6g} {v:.6g} 0.1 0.1 \n')
    if finished:
        with open(os.path.join(d, 'finished'), 'w') as f:
            f.write('1\n')
    if failed:
        with open(os.path.join(d, 'failed'), 'w') as f:
            f.write(failed + '\n')
    if robots:
        with tarfile.open(os.path.join(d, f'Gen_{generations:04d}.tgz'), 'w:gz') as t:
            for name, text in robots.items():
                data = text.encode()
                info = tarfile.TarInfo(f'Gen_{generations:04d}/{name}')
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
    return d


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = aa.main(argv)
    return code, out.getvalue()


class TestArmIsAnalysedOnlyAsAWhole(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        g = np.zeros((10, 10, 10), np.int8)
        g[2:6, 2:6, 0:3] = 1
        self.robots = lambda s: {robot_name('fake', 1000, 1, 4.0 + 0.01 * s, 4.0 + 0.01 * s): robot_text(g),
                                 robot_name('fake', 1000, 2, 1.0, 1.0): robot_text(g)}
        self.argv = ['--arm', 'R', '--results-dir', os.path.join(self.tmp, 'runs'), '--out-dir', os.path.join(self.tmp, 'out')]

    def build(self, special=None):
        for s in range(1, 36):
            kw = dict(scores=lambda gen, s=s: (4.0 + 0.01 * s) * min(1.0, gen / 500), robots=self.robots(s))
            kw.update((special or {}).get(s, {}))
            make_run(os.path.join(self.tmp, 'runs'), 'armR_P0_s', s, **kw)

    def assert_refused(self, seeds):
        code, text = run_main(self.argv)
        self.assertEqual(code, 2)
        self.assertIn(f'seeds {seeds} have not finished', text)
        for word in ('SCORES', 'median', 'ratio of', 'interval', 'A12'):
            self.assertNotIn(word, text)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'out')))

    def test_a_run_short_of_its_generations_stops_the_analysis(self):
        self.build({7: {'generations': 999}})
        self.assert_refused([7])

    def test_an_unfinished_or_failed_or_uncollected_run_stops_the_analysis(self):
        self.build({3: {'finished': False}, 9: {'failed': 'exit 139'}, 20: {'robots': None}})
        self.assert_refused([3, 9, 20])

    def test_a_missing_run_stops_the_analysis(self):
        self.build()
        shutil.rmtree(os.path.join(self.tmp, 'runs', 'armR_P0_s35'))
        self.assert_refused([35])

    def test_a_seed_that_failed_for_good_is_reported_and_left_out(self):
        if not HAVE_DEPOSIT:
            self.skipTest('deposited 2013 data not present')
        self.build({9: {'failed': 'exit 139', 'generations': 412}})
        with mock.patch.object(ps, 'N_BOOT', 300), mock.patch.object(ps, 'ATTAIN_TRIALS', 20), \
                mock.patch.object(ps, 'ATTAIN_BOOT', 200):
            code, text = run_main(self.argv + ['--failed-seeds', '9'])
        self.assertEqual(code, 0)
        self.assertIn('34 of 35 runs in the statistics', text)
        self.assertIn('LEFT OUT of the statistics: failed for good (exit 139)', text)
        report = load_json(os.path.join(self.tmp, 'out', 'arm_R.json'))
        self.assertEqual(report['scores']['1000']['n_arm'], 34)
        self.assertEqual([r['seed'] for r in report['left_out']], [9])

    def test_a_complete_seed_cannot_be_declared_failed(self):
        self.build()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            run_main(self.argv + ['--failed-seeds', '9'])


def make_search_run(root, name, scores, population=None, finished=True, checkpoint=False):
    """A run folder as run_tendon_evolution.py leaves it. population: [(grid, fitness), ...]."""
    import pickle
    d = os.path.join(root, name)
    os.makedirs(d)
    for g, v in enumerate(scores, start=1):
        with open(os.path.join(d, f'gen_{g:03d}.json'), 'w') as f:
            json.dump({'generation': g, 'best_fitness': v, 'fitnesses': [v]}, f)
    if finished:
        population = population or [(np.ones((10, 10, 10), np.int8), max(scores))]
        with open(os.path.join(d, 'final_population.pkl'), 'wb') as f:
            pickle.dump({'genomes': [g for g, _ in population], 'fitnesses': [v for _, v in population]}, f)
        with open(os.path.join(d, 'best_robot.pkl'), 'wb') as f:
            pickle.dump({'fitness': max(v for _, v in population)}, f)
    if checkpoint:
        with open(os.path.join(d, 'checkpoint.pkl'), 'wb') as f:
            f.write(b'x')
    return d


class TestReadingRunsOfThisProjectsSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_scores_come_from_the_numbered_generation_files(self):
        d = make_search_run(self.tmp, 'armA_s1', [0.5, 0.9, 0.8, 1.25])
        with open(os.path.join(d, 'history.json'), 'w') as f:        # a resumed run repeats a generation here
            json.dump({'best_fitness': [0.5, 0.9, 0.9, 0.8, 1.25]}, f)
        run = aa.load_search_run(d, 1)
        self.assertEqual(run['raw'].tolist(), [0.5, 0.9, 0.8, 1.25])
        self.assertEqual(run['best'].tolist(), [0.5, 0.9, 0.9, 1.25])
        self.assertEqual((run['generations'], run['finished']), (4, True))
        self.assertTrue(aa.is_complete(run, 4))
        self.assertFalse(aa.is_complete(run, 5))

    def test_a_gap_or_a_checkpoint_means_not_complete(self):
        d = make_search_run(self.tmp, 'armA_s2', [1.0] * 6)
        os.remove(os.path.join(d, 'gen_004.json'))
        self.assertEqual(aa.load_search_run(d, 2)['generations'], 3)
        d = make_search_run(self.tmp, 'armA_s3', [1.0] * 6, checkpoint=True)
        run = aa.load_search_run(d, 3)
        self.assertFalse(run['finished'])
        self.assertFalse(aa.is_complete(run, 6))
        d = make_search_run(self.tmp, 'armA_s4', [1.0] * 6, finished=False)
        self.assertFalse(aa.is_complete(aa.load_search_run(d, 4), 6))

    def test_champion_is_the_best_of_the_final_population(self):
        slab = np.zeros((10, 10, 10), np.int8)
        slab[2:6, 2:6, 0:2] = 1
        legs = np.zeros((10, 10, 10), np.int8)
        legs[2:6, 2:6, 1] = 3
        legs[2, 2, 0] = legs[5, 5, 0] = 2
        d = make_search_run(self.tmp, 'armA_s5', [1.0, 2.5], [(slab, 1.5), (legs, 2.5), (slab, 2.5)])
        run = aa.load_search_run(d, 5)
        aa.load_search_champion(run)
        c = run['champion']
        self.assertEqual((c['adjusted'], c['original'], c['population']), (2.5, 2.5, 3))
        self.assertIn('individual 1', c['file'])                       # the first of the two that tie
        self.assertEqual((c['body']['voxels'], c['body']['feet'], c['body']['two_feet']), (18, 2, True))
        self.assertAlmostEqual(c['body']['muscle'], 2 / 18)

    def test_an_unfinished_arm_a_is_refused(self):
        for s in range(1, 36):
            make_search_run(os.path.join(self.tmp, 'runs'), f'armA_s{s}', [1.0] * 1000, checkpoint=(s == 11))
        code, text = run_main(['--arm', 'A', '--results-dir', os.path.join(self.tmp, 'runs'),
                               '--out-dir', os.path.join(self.tmp, 'out')])
        self.assertEqual(code, 2)
        self.assertIn('seeds [11] have not finished', text)
        self.assertNotIn('SCORES', text)


@unittest.skipUnless(HAVE_DEPOSIT and os.path.isfile(os.path.join(aa.OUTCOMES, 'arm_R.json')),
                     'deposited 2013 data or the report of arm R not present')
class TestArmAReport(unittest.TestCase):
    """Arm A's report on made-up runs: the deposited COST curves stand in for its scores."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        body = np.zeros((10, 10, 10), np.int8)
        body[1:9, 1:9, 0:5] = 1
        for seed, curve in enumerate(aa.reference_scores('costNumActuated'), start=1):
            make_search_run(os.path.join(cls.tmp, 'runs'), f'armA_s{seed}', [float(v) for v in curve],
                            [(body, float(curve[-1])), (body, 0.5)])
        with mock.patch.object(ps, 'N_BOOT', 600), mock.patch.object(ps, 'ATTAIN_TRIALS', 50), \
                mock.patch.object(ps, 'ATTAIN_BOOT', 300):
            cls.code, cls.text = run_main(['--arm', 'A', '--results-dir', os.path.join(cls.tmp, 'runs'),
                                           '--out-dir', os.path.join(cls.tmp, 'out')])
            cls.code2, cls.text2 = run_main(['--arm', 'A', '--results-dir', os.path.join(cls.tmp, 'runs'),
                                             '--out-dir', os.path.join(cls.tmp, 'out2'),
                                             '--outcomes-dir', os.path.join(cls.tmp, 'no_outcomes')])
        cls.report = load_json(os.path.join(cls.tmp, 'out', 'arm_A.json'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_against_the_deposit(self):
        self.assertEqual(self.code, 0, self.text)
        s = self.report['scores']['1000']
        self.assertEqual(s['n_arm'], 35)
        self.assertAlmostEqual(s['arm_median'], 3.41, places=2)
        self.assertEqual(self.report['primary']['verdict'], 'differs')
        self.assertEqual(len(self.report['per_seed']), 35)
        self.assertTrue(all(r['champion']['curve_agrees'] for r in self.report['per_seed']))
        self.assertEqual(self.report['body']['measures']['voxels']['arm_median'], 320)

    def test_against_arm_r_and_the_floor(self):
        block = self.report['against']
        self.assertEqual((block['arm'], block['n_other'], block['generation']), ('R', 35, 1000))
        s = block['scores']['1000']
        self.assertAlmostEqual(s['reference_median'], 4.41, places=2)        # arm R's own median
        self.assertLess(s['ratio_of_medians'], 0.85)
        self.assertLess(s['p'], 1e-4)
        self.assertEqual(sorted(block['scores']), ['100', '1000', '300'])
        self.assertEqual(block['floor']['verdict'], 'reproduces')
        self.assertAlmostEqual(block['floor']['ratio_of_medians'], 1.004, places=3)
        self.assertIn('AGAINST ARM R', self.text)
        self.assertIn('The floor, measured for the original code itself', self.text)

    def test_without_the_report_of_arm_r_it_says_so(self):
        self.assertEqual(self.code2, 0, self.text2)
        self.assertIn('The report of arm R is not in', self.text2)
        self.assertNotIn('AGAINST ARM R', self.text2)


@unittest.skipUnless(HAVE_DEPOSIT, 'deposited 2013 data not present')
class TestArmDReport(unittest.TestCase):
    """Arm D's report on made-up runs: the first 300 generations of ten deposited no-cost runs
    stand in for its scores. Written on 27 November 2026, before the arm was started."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        body = np.zeros((10, 10, 10), np.int8)
        body[1:9, 1:9, 0:5] = 1
        for seed, curve in enumerate(aa.reference_scores('noCost')[:10], start=1):
            make_search_run(os.path.join(cls.tmp, 'runs'), f'armD_s{seed}', [float(v) for v in curve[:300]],
                            [(body, float(curve[299])), (body, 0.5)])
        with mock.patch.object(ps, 'N_BOOT', 600), mock.patch.object(ps, 'ATTAIN_TRIALS', 50), \
                mock.patch.object(ps, 'ATTAIN_BOOT', 300):
            cls.code, cls.text = run_main(['--arm', 'D', '--results-dir', os.path.join(cls.tmp, 'runs'),
                                           '--out-dir', os.path.join(cls.tmp, 'out')])
        cls.report = load_json(os.path.join(cls.tmp, 'out', 'arm_D.json'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_the_arm_is_the_one_of_the_protocol(self):
        arm = aa.ARMS['D']
        self.assertEqual((arm['kind'], arm['prefix'], arm['seeds'], arm['generations'], arm['condition']),
                         ('search', 'armD_s', list(range(1, 11)), 300, 'noCost'))
        self.assertEqual(arm['score_generations'], (300, 100))            # primary at 300, secondary at 100
        self.assertNotIn('against', arm)                                  # the fifth primary comparison is A against R

    def test_the_primary_outcome_is_at_generation_300(self):
        self.assertEqual(self.code, 0, self.text)
        self.assertEqual(sorted(self.report['scores']), ['100', '300'])
        self.assertEqual(self.report['primary']['generation'], 300)
        s = self.report['scores']['300']
        self.assertEqual((s['n_arm'], s['n_reference']), (10, 35))
        reference = sorted(float(c[299]) for c in aa.reference_scores('noCost'))
        self.assertAlmostEqual(s['reference_median'], reference[17], places=9)     # the deposit at generation 300
        self.assertTrue(0.8 < s['ratio_of_medians'] < 1.25)               # ten of the deposit's own runs
        self.assertIn(self.report['primary']['verdict'], ('reproduces', 'not distinguishable', 'differs'))
        self.assertIn('Primary outcome, generation 300', self.text)
        self.assertNotIn('AGAINST ARM', self.text)
        self.assertNotIn('against', self.report)

    def test_the_body_table_says_which_generations_it_sets_against_each_other(self):
        body = self.report['body']
        self.assertEqual((body['generation'], body['reference_generation'], body['n_arm'], body['n_reference']),
                         (300, 1000, 10, 35))
        self.assertEqual(body['measures']['voxels']['arm_median'], 320)
        self.assertIn("this arm's champions of generation 300 against the deposited champions of generation 1000", self.text)
        self.assertIn('BODY of each run\'s champion at generation 300 (10 runs)', self.text)

    def test_every_seed_is_there(self):
        self.assertEqual([r['seed'] for r in self.report['per_seed']], list(range(1, 11)))
        self.assertTrue(all(r['generations'] == 300 and r['champion']['curve_agrees'] for r in self.report['per_seed']))
        self.assertIn('Seeds 1 to 10, 300 generations; 10 of 10 runs in the statistics', self.text)

    def test_an_unfinished_arm_d_is_refused(self):
        runs = os.path.join(self.tmp, 'short')
        for seed in range(1, 11):
            make_search_run(runs, f'armD_s{seed}', [1.0] * (300 if seed != 4 else 299))
        code, text = run_main(['--arm', 'D', '--results-dir', runs, '--out-dir', os.path.join(self.tmp, 'out_short')])
        self.assertEqual(code, 2)
        self.assertIn('seeds [4] have not finished with 300 generations', text)
        self.assertNotIn('SCORES', text)


@unittest.skipUnless(HAVE_DEPOSIT, 'deposited 2013 data not present')
class TestWhatThreeRunsCanShow(unittest.TestCase):
    """PROTOCOL.md, section 9.8, point 5: from the deposited runs alone."""

    def test_the_design_is_that_of_the_e_arms(self):
        few = aa.what_three_runs_can_show(trials=60, n_boot=200)
        self.assertEqual((few['runs'], few['generation'], few['deposited_runs'], few['runs_of_the_other_arm']), (3, 300, 35, 10))
        self.assertEqual([r['true_ratio'] for r in few['rows']], [1.0, 0.9, 0.75, 0.5])
        none, half = few['rows'][0], few['rows'][-1]
        for against in ('against_the_deposit', 'against_another_arm'):
            self.assertLess(none[against]['interval_excludes_1'], 0.35)
            self.assertGreater(half[against]['interval_excludes_1'], 0.95)
        self.assertAlmostEqual(few['smallest_p_against_the_deposit'], 2 / 8436)
        self.assertAlmostEqual(few['smallest_p_against_the_other_arm'], 2 / 286)

    def test_the_designs_of_the_earlier_arms_are_still_there(self):
        with mock.patch.object(ps, 'ATTAIN_TRIALS', 30), mock.patch.object(ps, 'ATTAIN_BOOT', 200):
            rows = aa.what_the_criterion_can_show()
        self.assertEqual([r['design'].split(':')[0] for r in rows], ['R and A', 'Rc', 'D', 'E1 to E3'])


@unittest.skipUnless(HAVE_DEPOSIT, 'deposited 2013 data not present')
class TestDressRehearsalOnTheDeposit(unittest.TestCase):
    """Arms built from the deposited runs themselves: the whole path, with answers known in advance."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.reports = {}
        for condition in ('noCost', 'costNumActuated'):
            runs = os.path.join(cls.tmp, condition, 'runs')
            curves = aa.reference_scores(condition)
            folders = sorted(glob.glob(os.path.join(aa.DEPOSITED_ROBOTS, f'2013-01-16-10^3-{condition}', 'run_*')))
            for seed, (curve, folder) in enumerate(zip(curves, folders), start=1):
                robots = {}
                for path in glob.glob(os.path.join(folder, 'Gen_1000', '*.vxa')):
                    with open(path, encoding='utf-8', errors='replace') as f:
                        robots[os.path.basename(path)] = f.read()
                make_run(runs, 'armR_P0_s', seed, list(curve), robots)
            with mock.patch.object(ps, 'N_BOOT', 1000), mock.patch.object(ps, 'ATTAIN_TRIALS', 100), \
                    mock.patch.object(ps, 'ATTAIN_BOOT', 500):
                code, text = run_main(['--arm', 'R', '--results-dir', runs, '--out-dir', os.path.join(cls.tmp, condition, 'out')])
            assert code == 0, text
            cls.reports[condition] = (load_json(os.path.join(cls.tmp, condition, 'out', 'arm_R.json')), text)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_the_deposit_against_itself_reproduces(self):
        report, text = self.reports['noCost']
        s = report['scores']['1000']
        self.assertEqual((s['n_arm'], s['n_reference']), (35, 35))
        self.assertAlmostEqual(s['arm_median'], 4.393, places=2)        # the known deposited median
        self.assertEqual(s['ratio_of_medians'], 1.0)
        self.assertEqual(s['a12'], 0.5)
        self.assertEqual(report['primary']['verdict'], 'reproduces')
        self.assertIn('REPRODUCES', text)
        self.assertAlmostEqual(report['scores']['100']['arm_median'], 3.26, places=2)
        self.assertAlmostEqual(report['scores']['300']['arm_median'], 3.70, places=2)

    def test_the_deposited_champions_measure_as_on_18_november(self):
        body = self.reports['noCost'][0]['body']
        self.assertEqual((body['n_arm'], body['n_reference']), (35, 35))
        self.assertEqual(body['measures']['voxels']['reference_median'], 652)
        self.assertEqual(body['measures']['footprint']['reference_median'], 26)
        self.assertAlmostEqual(body['measures']['muscle']['reference_median'], 1.0)
        self.assertEqual((body['measures']['two_feet']['arm_yes'], body['measures']['two_feet']['reference_yes']), (1, 1))
        for m in body['measures'].values():
            self.assertEqual(m['p'], 1.0)                               # identical on both sides
            self.assertEqual(m['p_holm'], 1.0)

    def test_every_seed_is_listed_with_its_champion(self):
        report, text = self.reports['noCost']
        self.assertEqual([r['seed'] for r in report['per_seed']], list(range(1, 36)))
        for r in report['per_seed']:
            self.assertEqual(r['generations'], 1000)
            self.assertEqual(r['champion']['population'], 30)
            self.assertEqual(r['champion']['adjusted'], r['champion']['original'])     # no cost in this condition
        self.assertIn('PER SEED', text)

    def test_the_cost_condition_set_against_the_no_cost_deposit_differs(self):
        report, text = self.reports['costNumActuated']       # analysed as arm R, i.e. against the no-cost runs
        s = report['scores']['1000']
        self.assertAlmostEqual(s['arm_median'], 3.41, places=2)
        self.assertAlmostEqual(s['reference_median'], 4.393, places=2)
        self.assertEqual(report['primary']['verdict'], 'differs')
        self.assertIn('DIFFERS', text)
        self.assertLess(s['p'], 1e-4)
        self.assertLess(s['a12'], 0.2)
        body = report['body']['measures']
        self.assertLess(body['voxels']['arm_median'], body['voxels']['reference_median'])
        self.assertLess(body['muscle']['arm_median'], 0.9)
        self.assertLess(body['voxels']['p_holm'], 0.01)
        self.assertGreaterEqual(body['voxels']['p_holm'], body['voxels']['p'])


if __name__ == '__main__':
    unittest.main()
