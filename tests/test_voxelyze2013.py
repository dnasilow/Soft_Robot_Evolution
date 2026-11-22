"""Tests for the 2013 rules (src/evolution/cheney2013.py) and for the evaluator that runs bodies in
the ORIGINAL 2013 simulator (src/evolution/voxelyze2013_evaluator.py).

The rule tests need nothing. The simulator tests are skipped unless the simulator has been built
(paper/reference_2013/build_2013_simulator.sh); the comparisons with deposited robots are skipped
unless those files are present under research_reference/ (which is not in the repository).

Run from the repo root:   python -m unittest discover -s tests -t . -v
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from src.evolution import cheney2013 as c13
from src.evolution.voxelyze2013_evaluator import TEMPLATE, Voxelyze2013Evaluator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRYAD = os.path.join(ROOT, 'research_reference', 'extracted', 'dryad_gen1000')
REPLAY = os.path.join(ROOT, 'paper', 'reference_2013', 'replay_2013_simulator.csv')
HAVE_SIM = Voxelyze2013Evaluator.available()
HAVE_DRYAD = os.path.isdir(os.path.join(DRYAD, '2013-01-16-10^3-noCost'))


def read_text(path):
    with open(path, encoding='iso-8859-1') as fh:
        return fh.read()


def walker():
    """A small two-footed body in the 10-voxel workspace: muscle phase 0 behind, phase pi in front."""
    g = np.zeros((10, 10, 10), np.int8)
    for x in range(5):
        for y in range(3):
            for z in range(3):
                if z > 0 or x in (0, 4):
                    g[x, y, z] = 1 if x < 2 else 2
    return g


def deposited(cond, pattern='run_10[0-2]', limit=None):
    """(file name, our grid, recorded original score, recorded adjusted score) of deposited robots."""
    out = []
    for f in sorted(glob.glob(os.path.join(DRYAD, cond, pattern, 'Gen_1000', '*.vxa'))):
        text = read_text(f)
        rows = [m.group(2).strip() for m in c13.LAYER.finditer(text)]
        if '5' in ''.join(rows):
            continue
        b = os.path.basename(f)
        out.append((b, c13.grid_from_rows(rows), rows,
                    float(re.search(r'origFit_([0-9.eE+-]+)_genome', b).group(1)),
                    float(re.search(r'adjFit_([0-9.eE+-]+)--', b).group(1))))
        if limit and len(out) >= limit:
            break
    return out


class TestRules(unittest.TestCase):
    """The 2013 rules, as read from HCUBE_SoftbotsExperiment.cpp."""

    def test_rows_round_trip_and_material_numbers(self):
        g = walker()
        g[2, 1, 3] = 3
        g[2, 1, 4] = 4
        rows = c13.layer_rows(g)
        self.assertEqual((len(rows), len(rows[0])), (10, 100))
        np.testing.assert_array_equal(c13.grid_from_rows(rows), g)
        # ours 1,2,3,4 -> 2013 file 1,3,2,4 ; x runs along a row, y selects the row block
        self.assertEqual(rows[1][0], '1')            # (x=0, y=0, z=1) muscle phase 0
        self.assertEqual(rows[1][4], '3')            # (x=4, y=0, z=1) muscle phase pi -> Active_-
        self.assertEqual(rows[3][12], '2')           # (x=2, y=1, z=3) soft -> Passive_Soft
        self.assertEqual(rows[4][12], '4')           # (x=2, y=1, z=4) stiff -> Passive_Hard

    def test_workspace_is_cut_out_unmoved(self):
        from src.evolution.genome_config import VOXEL_INTERIOR_MIN as i0
        big = np.zeros((20, 20, 20), np.int8)
        big[i0 + 3, i0 + 4, i0 + 5] = 2
        g = c13.workspace_grid(big)
        self.assertEqual(g.shape, (10, 10, 10))
        self.assertEqual(g[3, 4, 5], 2)
        self.assertEqual(int((g != 0).sum()), 1)
        np.testing.assert_array_equal(c13.workspace_grid(g), g)      # already a workspace
        big[i0 + 10, i0, i0] = 1                                      # just outside the workspace
        with self.assertRaises(ValueError):
            c13.workspace_grid(big)

    def test_counts(self):
        g = np.zeros((10, 10, 10), np.int8)
        g[0, 0, 0], g[1, 0, 0], g[1, 1, 0], g[5, 5, 5] = 1, 2, 3, 4
        self.assertEqual(c13.counts(g), {'voxels': 4, 'actuated': 2, 'connections': 2})
        self.assertEqual(c13.penalty_metric(g, 'none'), 4)
        self.assertEqual(c13.penalty_metric(g, 'actuated'), 2)

    def test_penalty_factor(self):
        g = np.zeros((10, 10, 10), np.int8)
        g[:5, :, :] = 1                                               # 500 muscle voxels
        self.assertEqual(c13.penalty_factor(g, 'none'), 1.0)
        self.assertAlmostEqual(c13.penalty_factor(g, 'actuated'), 0.5)
        self.assertAlmostEqual(c13.penalty_factor(g, 'voxels'), 0.5)
        self.assertAlmostEqual(c13.penalty_factor(g, 'voxels', exponent=2.0), 0.75)
        conn = c13.counts(g)['connections']
        self.assertEqual(conn, 4 * 100 + 2 * 5 * 90)                  # x faces + y and z faces
        self.assertAlmostEqual(c13.penalty_factor(g, 'connections'), 1 - conn / 2700)
        with self.assertRaises(ValueError):
            c13.penalty_metric(g, 'weight')

    def test_score_rules(self):
        self.assertAlmostEqual(c13.fitness_from_result('0.0310994'), 3.10994)
        self.assertAlmostEqual(c13.fitness_from_result('-0.02'), 2.0)   # fabs()
        self.assertEqual(c13.fitness_from_result(None), 0.001)          # no result file
        self.assertEqual(c13.fitness_from_result(''), 0.001)
        self.assertEqual(c13.fitness_from_result('nan'), 0.0001)
        self.assertEqual(c13.fitness_from_result('-nan'), 0.0001)
        self.assertEqual(c13.fitness_from_result('inf'), 0.0001)
        self.assertEqual(c13.fitness_from_result('0.0000001'), 0.0001)  # below the floor
        self.assertEqual(c13.fitness_from_result('50'), 0.0001)         # 5000 widths: absurd
        self.assertEqual(c13.clamp(float('nan')), 0.0001)
        g = np.zeros((10, 10, 10), np.int8)
        g[:5, :, :] = 1
        self.assertAlmostEqual(c13.penalised(3.0, g, 'actuated'), 1.5)
        self.assertEqual(c13.penalised(3.0, g, 'none'), 3.0)

    def test_template_holds_the_2013_settings(self):
        text = read_text(TEMPLATE)
        self.assertEqual(len(c13.LAYER.findall(text)), 10)
        for tag, value in (('SimStopTime', '0.25'), ('GravAcc', '-27.468'), ('TempAmp', '39'),
                           ('TempBase', '25'), ('TempPeriod', '0.025'), ('SlowDampingZ', '0.001'),
                           ('PoissonKickBackEnabled', '0'), ('DtFrac', '0.9'), ('Lattice_Dim', '0.001'),
                           ('X_Voxels', '10'), ('FitnessFileNm', 'fitness.xml')):
            self.assertIn(f'<{tag}>{value}</{tag}>', text)
        g = walker()
        filled = c13.fill_template(text, g)
        self.assertEqual([m.group(2) for m in c13.LAYER.finditer(filled)], c13.layer_rows(g))
        self.assertEqual(c13.LAYER.sub('', filled), c13.LAYER.sub('', text))   # nothing else changed

    @unittest.skipUnless(HAVE_DRYAD, 'deposited 2013 robots not present')
    def test_penalty_matches_the_deposited_cost_robots(self):
        """adjusted / original score of deposited actuated-cost robots = 1 - actuated / 1000."""
        robots = [r for r in deposited('2013-01-16-10^3-costNumActuated') if r[3] >= 0.01]
        self.assertGreater(len(robots), 50)
        for name, g, rows, orig, adj in robots:
            self.assertAlmostEqual(adj / orig, c13.penalty_factor(g, 'actuated'), places=6, msg=name)

    @unittest.skipUnless(HAVE_DRYAD, 'deposited 2013 robots not present')
    def test_template_reproduces_deposited_files(self):
        """Filling the template with a deposited body gives that deposited file back, apart from
        the name of its result file."""
        template = read_text(TEMPLATE)
        for name, g, rows, orig, adj in deposited('2013-01-16-10^3-noCost', limit=10):
            f = glob.glob(os.path.join(DRYAD, '*', '*', 'Gen_1000', name))[0]
            original = read_text(f).replace('\r\n', '\n')
            original = re.sub(r'<FitnessFileNm>.*?</FitnessFileNm>',
                              '<FitnessFileNm>fitness.xml</FitnessFileNm>', original)
            self.assertEqual(c13.fill_template(template, g), original, name)


@unittest.skipUnless(HAVE_SIM, '2013 simulator not built (paper/reference_2013/build_2013_simulator.sh)')
class TestEvaluator(unittest.TestCase):
    def test_runs_caches_and_is_deterministic(self):
        ev = Voxelyze2013Evaluator(n_workers=4)
        g = walker()
        a = ev.evaluate_batch([g, g, g[::-1].copy()])
        self.assertEqual(a.shape, (3,))
        self.assertGreater(a[0], 0.01)                    # it moves
        self.assertEqual(a[0], a[1])
        self.assertEqual((ev.n_simulated, ev.n_cached), (2, 1))
        self.assertEqual(ev.evaluate_single(g), a[0])     # from the cache
        self.assertEqual(ev.n_simulated, 2)
        fresh = Voxelyze2013Evaluator(n_workers=1)        # a new evaluator, one at a time
        self.assertEqual(fresh.evaluate_single(g), a[0])

    def test_accepts_our_genome_arrays(self):
        from src.evolution.genome_config import VOXEL_INTERIOR_MIN as i0
        big = np.zeros((20, 20, 20), np.int8)
        big[i0:i0 + 10, i0:i0 + 10, i0:i0 + 10] = walker()
        ev = Voxelyze2013Evaluator(n_workers=2)
        self.assertEqual(ev.evaluate_single(big), ev.evaluate_single(walker()))

    def test_bodies_the_2013_code_does_not_simulate(self):
        ev = Voxelyze2013Evaluator(n_workers=2)
        one = np.zeros((10, 10, 10), np.int8)
        one[0, 0, 0] = 1
        out = ev.evaluate_batch([one, np.zeros((10, 10, 10), np.int8)])
        np.testing.assert_array_equal(out, [0.0001, 0.0001])
        self.assertEqual((ev.n_simulated, ev.n_skipped), (0, 2))
        passive = walker()
        passive[passive != 0] = 3                         # no actuated voxel at all
        evp = Voxelyze2013Evaluator(n_workers=2, penalty='actuated')
        self.assertEqual(evp.evaluate_single(passive), 0.0001)
        self.assertEqual(evp.n_simulated, 0)

    def test_penalty_is_applied_to_the_original_score(self):
        g = walker()
        plain = Voxelyze2013Evaluator(n_workers=2)
        cost = Voxelyze2013Evaluator(n_workers=2, penalty='actuated')
        f0 = plain.evaluate_single(g)
        f1 = cost.evaluate_single(g)
        self.assertEqual(cost.last_original[0], f0)
        self.assertAlmostEqual(f1, f0 * (1 - c13.counts(g)['actuated'] / 1000), places=12)

    def test_what_it_cannot_do_is_refused(self):
        ev = Voxelyze2013Evaluator(n_workers=1)
        with self.assertRaises(NotImplementedError):
            ev.evaluate_batch([walker()], with_descriptors=True)
        with self.assertRaises(ValueError):
            ev.evaluate_batch([walker()], gait_params=[(1.0, 0.0, 0.0, 0.0)])
        with self.assertRaises(ValueError):
            Voxelyze2013Evaluator(workspace_voxels=5)
        with self.assertRaises(RuntimeError):
            Voxelyze2013Evaluator(binary='~/no_such_simulator')

    @unittest.skipUnless(HAVE_DRYAD and os.path.exists(REPLAY), 'deposited robots or reference replay not present')
    def test_same_scores_as_the_reference_replay(self):
        """The evaluator must give exactly what replaying the deposited files gave."""
        import csv
        with open(REPLAY, newline='') as fh:
            ref = {r['file']: r['final_com_dist_m'] for r in csv.DictReader(fh)}
        robots = deposited('2013-01-16-10^3-noCost', pattern='run_100', limit=12)
        ev = Voxelyze2013Evaluator(n_workers=8)
        got = ev.evaluate_batch([r[1] for r in robots])
        for (name, g, rows, orig, adj), f in zip(robots, got):
            want = c13.fitness_from_result(ref[name] if ref[name] not in ('NA', '') else None)
            self.assertAlmostEqual(f, want, places=9, msg=name)


class TestPenaltyWithOurEngine(unittest.TestCase):
    def test_mujoco_evaluator_applies_the_same_factor(self):
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        from src.evolution.genome_config import VOXEL_INTERIOR_MIN as i0
        big = np.zeros((20, 20, 20), np.int8)
        big[i0:i0 + 10, i0:i0 + 10, i0:i0 + 10] = walker()
        kw = dict(simulation_time=0.25, settle_time=0.0, actuation_amplitude=0.2, actuation_frequency=40.0,
                  n_workers=1, attach_controller=False, fitness_mode='forward', body='beam',
                  materials='cheney2013', floor_contact='voxelyze', direction='any',
                  divide_by='workspace', workspace_voxels=10,
                  friction={'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01})
        plain = MuJoCoTendonEvaluator(**kw).evaluate_single(big)
        cost = MuJoCoTendonEvaluator(penalty='actuated', **kw).evaluate_single(big)
        self.assertGreater(plain, 0)
        self.assertAlmostEqual(cost, plain * (1 - c13.counts(walker())['actuated'] / 1000), places=12)
        with self.assertRaises(ValueError):
            MuJoCoTendonEvaluator(penalty='actuated', n_workers=1)       # needs the workspace size
        with self.assertRaises(ValueError):
            MuJoCoTendonEvaluator(penalty='weight', n_workers=1, workspace_voxels=10)


def run_cli(args, cwd, timeout=300):
    return subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py')] + args,
                          cwd=cwd, capture_output=True, text=True, timeout=timeout)


class TestCommandLine(unittest.TestCase):
    def test_help_lists_the_flags(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py'), '--help'],
                           capture_output=True, text=True, timeout=60)
        self.assertIn('--simulator {mujoco,voxelyze2013}', r.stdout)
        self.assertIn('--penalty {none,voxels,actuated,connections}', r.stdout)

    def test_options_the_2013_simulator_cannot_honour_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = ['--simulator', 'voxelyze2013', '--gen', '1', '--pop', '2', '--workers', '1',
                    '--name', 'vx_reject']
            for extra, text in ((['--amp', '0.2'], '--amp 0.2 (the 2013 value is 0.14)'),
                                (['--body', 'beam'], '--body'),
                                (['--damping-global', '0.01'], '--damping-global'),
                                (['--map-elites'], '--map-elites'),
                                (['--preset', 'cheney2013'], '--preset'),
                                (['--grid-size', '5'], '--grid-size 5')):
                r = run_cli(base + extra, tmp)
                self.assertIn('with --simulator voxelyze2013', r.stdout + r.stderr, extra)
                self.assertIn(text, r.stdout + r.stderr, extra)
            self.assertFalse(os.path.exists(os.path.join(tmp, 'results')), 'a refused run created output')

    def test_resume_checks_simulator_and_penalty(self):
        sys.path.insert(0, ROOT)
        import run_tendon_evolution as R
        base = {'friction': None, 'body': 'springs', 'sim_time': 0.25, 'settle_time': 0.0}

        def ok(ck, phys):
            try:
                R._check_resume_physics(ck, phys)
                return True
            except SystemExit:
                return False
        vx = {**base, 'simulator': 'voxelyze2013', 'penalty': 'none', 'penalty_exp': 1.0}
        mj = {**base, 'simulator': 'mujoco', 'penalty': 'none', 'penalty_exp': 1.0}
        self.assertTrue(ok({'physics': vx}, vx))
        self.assertFalse(ok({'physics': vx}, mj))
        self.assertFalse(ok({'physics': vx}, {**vx, 'penalty': 'actuated'}))
        self.assertTrue(ok({'physics': base}, mj))        # checkpoints before the flags: MuJoCo, no penalty
        self.assertFalse(ok({'physics': base}, vx))

    @unittest.skipUnless(HAVE_SIM, '2013 simulator not built')
    def test_a_run_in_the_2013_simulator(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_cli(['--simulator', 'voxelyze2013', '--no-age-pareto', '--gen', '2', '--pop', '4',
                         '--workers', '4', '--penalty', 'actuated', '--name', 'vx_run'], tmp)
            self.assertIn('EVOLUTION COMPLETE', r.stdout, r.stderr[-800:])
            self.assertIn('Simulator  : the ORIGINAL 2013 simulator', r.stdout)
            self.assertIn('Penalty    : fitness x (1 - (actuated / maximum)^1)', r.stdout)
            self.assertIn('Actuation  : 40.0Hz  +-14%', r.stdout)
            self.assertIn('per FIXED workspace width of 10 voxels [W]', r.stdout)
            self.assertRegex(r.stdout, r'Gen   2/2  best=\d+\.\d{4}W  mean=')
            with open(os.path.join(tmp, 'results', 'vx_run', 'manifest.json')) as fh:
                s = json.load(fh)['invocations'][0]['settings']
            self.assertEqual((s['simulator'], s['penalty'], s['amp'], s['grid_size'], s['no_trim']),
                             ('voxelyze2013', 'actuated', 0.14, 10, True))


if __name__ == '__main__':
    unittest.main()
