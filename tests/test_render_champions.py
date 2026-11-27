"""The video maker for champions (paper/analysis/render_champions.py): the parts that need neither
the simulator nor a graphics context."""
import math
import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
import render_champions as rc       # noqa: E402


def write_trace(path, materials, frames):
    """frames: [(time, [(x, y, z), ...])] in metres; no rotation, size one millimetre."""
    with open(path, 'w') as f:
        f.write(f'voxels {len(materials)}\n')
        for m in materials:
            f.write(f'{m}\n')
        for t, positions in frames:
            cm = np.mean(positions, axis=0)
            f.write(f't {t} {cm[0]} {cm[1]} {cm[2]}\n')
            for x, y, z in positions:
                f.write(f'{x} {y} {z} 1 0 0 0 0.001 0.001 0.001\n')


class TestChoice(unittest.TestCase):
    def test_median_and_best_by_rule(self):
        champions = [(s, f'run {i}') for i, s in enumerate([4.2, 5.9, 3.4, 4.4, 4.9])]
        median, best = rc.median_and_best(champions)
        self.assertEqual((median[0], best[0]), (4.4, 5.9))
        median, best = rc.median_and_best([(float(s), s) for s in range(1, 36)])      # 35 runs: the 18th and the 35th
        self.assertEqual((median[0], best[0]), (18.0, 35.0))

    def test_an_arm_that_does_not_exist_is_refused(self):
        with self.assertRaises(SystemExit):
            import contextlib
            import io
            with contextlib.redirect_stderr(io.StringIO()):
                rc.main(['--arm', 'Z'])


class TestSearchChampion(unittest.TestCase):
    """Arm A's champions are bodies in a final population, not robot files."""

    def test_the_robot_file_is_that_body_in_the_2013_template(self):
        import pickle
        from src.evolution import cheney2013 as c13
        from src.evolution.voxelyze2013_evaluator import TEMPLATE
        rng = np.random.default_rng(3)
        bodies = [rng.integers(0, 5, (10, 10, 10)).astype(np.int8) for _ in range(3)]
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, 'final_population.pkl'), 'wb') as f:
                pickle.dump({'genomes': bodies, 'fitnesses': [1.0, 3.0, 2.0]}, f)
            text = rc.search_robot_text(folder, 'final_population.pkl, individual 1')
        rows = [m.group(2) for m in c13.LAYER.finditer(text)]
        np.testing.assert_array_equal(c13.grid_from_rows(rows), bodies[1])
        with open(TEMPLATE, encoding='iso-8859-1') as f:
            template = f.read()
        self.assertEqual(c13.LAYER.sub('', text), c13.LAYER.sub('', template))     # nothing but the body differs
        self.assertEqual(text, c13.fill_template(template, bodies[1]))             # what the search writes


class TestRecordingAsRead(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'trace.txt')
        # two voxels side by side on the floor, moving 30 mm along the diagonal between x and y, rising 1 mm
        start = np.array([[0.0005, 0.0005, 0.0005], [0.0015, 0.0005, 0.0005]])
        frames = []
        for k in range(11):
            shift = np.array([0.003 * k / math.sqrt(2), 0.003 * k / math.sqrt(2), 0.0001 * k])
            frames.append((0.025 * k, start + shift))
        write_trace(self.path, [1, 3], frames)

    def test_read(self):
        materials, times, cms, frames = rc.read_trace(self.path)
        self.assertEqual(materials.tolist(), [1, 3])
        self.assertEqual(frames.shape, (11, 2, 10))
        self.assertAlmostEqual(times[-1], 0.25)
        np.testing.assert_allclose(cms[0], [0.001, 0.0005, 0.0005])

    def test_shown_travelling_to_the_right_in_voxels(self):
        materials, times, cms, frames = rc.read_trace(self.path)
        pos, quat, size, cm = rc.for_display(cms, frames)
        np.testing.assert_allclose(cm[0], [0, 0, 0.5], atol=1e-9)             # starts at the origin, on the floor
        np.testing.assert_allclose(cm[-1], [30, 0, 1.5], atol=1e-6)           # 30 voxels to the right, no sideways drift
        np.testing.assert_allclose(size, 1.0)
        np.testing.assert_allclose(np.linalg.norm(quat, axis=-1), 1.0)
        # distances between voxels are untouched by the turn
        np.testing.assert_allclose(np.linalg.norm(pos[:, 0] - pos[:, 1], axis=-1), 1.0, atol=1e-9)

    def test_the_checks(self):
        materials, times, cms, frames = rc.read_trace(self.path)
        robot = {'row': 're-run 2026, arm R', 'who': 'seed 1', 'column': 'median of 35', 'recorded': 3.0, 'ours': True}
        true_distance = float(np.linalg.norm(cms[-1] - cms[0]))
        c = rc.describe(robot, materials, times, cms, frames, true_distance, true_distance)
        self.assertEqual((c['voxels'], c['materials'], c['frames']), (2, {'1': 1, '3': 1}, 11))
        self.assertAlmostEqual(c['score_from_first_and_last_frame'], true_distance / 0.01)
        self.assertAlmostEqual(c['lowest_point_voxels'], 0.0)
        self.assertEqual(len(c['body_lengths_per_cycle']), 10)
        self.assertAlmostEqual(sum(c['body_lengths_per_cycle']), 3.0, places=2)
        self.assertTrue(c['all_numbers_finite'])

    def test_quaternions_multiply(self):
        quarter = np.array([math.cos(math.pi / 4), 0, 0, math.sin(math.pi / 4)])
        half = rc.quat_mul(quarter, quarter)
        np.testing.assert_allclose(half, [0, 0, 0, 1], atol=1e-12)
        np.testing.assert_allclose(rc.quat_mul(np.array([1.0, 0, 0, 0]), quarter), quarter)

    def test_windows_path_as_wsl_sees_it(self):
        if os.name == 'nt':
            self.assertEqual(rc.wsl_path(r'C:\SoftRobotEvolution\results\x.vxa'), '/mnt/c/SoftRobotEvolution/results/x.vxa')


def small_body(variant=0):
    g = np.zeros((10, 10, 10), np.int8)
    g[4:6, 4:7, 0:2] = 1
    g[4:6, 4:5, 0:2] = 2
    g[4, 6, 1] = 3
    if variant:
        g[4 + variant % 2, 7, 0] = 1 + variant % 2
        g[3, 4 + variant % 3, 0] = 1 + (variant // 3) % 2
    return g


def as_stored(grid):
    """The body inside the larger array a run of the search stores."""
    from src.evolution.genome_config import VOXEL_GRID_SHAPE, VOXEL_INTERIOR_MIN
    big = np.zeros(VOXEL_GRID_SHAPE, np.int8)
    i = VOXEL_INTERIOR_MIN
    big[i:i + 10, i:i + 10, i:i + 10] = grid
    return big


def make_runs(results, prefix, scores, generations=2):
    """Run folders as the search leaves them, one per seed, each with a champion of that score."""
    import json
    import pickle
    for seed, score in scores.items():
        folder = os.path.join(results, f'{prefix}{seed}')
        os.makedirs(folder)
        for g in range(1, generations + 1):
            with open(os.path.join(folder, f'gen_{g:03d}.json'), 'w') as f:
                json.dump({'generation': g, 'best_fitness': score, 'fitnesses': [score, 0.1]}, f)
        with open(os.path.join(folder, 'final_population.pkl'), 'wb') as f:
            pickle.dump({'genomes': [as_stored(small_body(seed + 10)), as_stored(small_body(seed))],
                         'fitnesses': [0.1, score]}, f)
        with open(os.path.join(folder, 'best_robot.pkl'), 'wb') as f:
            pickle.dump({'genome': as_stored(small_body(seed)), 'fitness': score}, f)


class TestArmsEvolvedInTheEngine(unittest.TestCase):
    """Arm D: this project's search in its own MuJoCo engine (27 November 2026). Its champions
    are shown in that engine, and once more in the 2013 simulator."""

    DEPOSIT = [(4.2, 'run 7', 'folder', 'a.vxa'), (5.9, 'run 9', 'folder', 'b.vxa'), (3.1, 'run 2', 'folder', 'c.vxa')]

    def setUp(self):
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (('deposited', lambda condition: list(self.DEPOSIT)),
                            ('deposited_robot_text', lambda folder, name: f'<the robot file {name}>')):
            patcher = mock.patch.object(rc, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.scores = {101: 1.3, 102: 1.7, 103: 2.4, 104: 1.5}
        make_runs(self.tmp.name, 'trialX_s', self.scores)

    def test_which_arms(self):
        self.assertTrue(rc.evolved_in_the_engine('D'))
        self.assertFalse(rc.evolved_in_the_engine('A'))
        self.assertFalse(rc.evolved_in_the_engine('R'))

    def test_the_median_of_an_even_number_is_the_lower_middle_one(self):
        median, best = rc.median_and_best([(float(s), s) for s in range(1, 11)])        # arm D has ten runs
        self.assertEqual((median[0], best[0]), (5.0, 10.0))

    def test_six_robots_in_three_rows(self):
        from src.evolution import cheney2013 as c13
        robots = rc.rehearsal_robots('trialX_s', 2, self.tmp.name)
        self.assertEqual([(r['simulator'], r['column']) for r in robots],
                         [('2013', 'median of 3'), ('2013', 'best of 3'), ('mujoco', 'median of 4'), ('mujoco', 'best of 4'),
                          ('2013', 'median of 4'), ('2013', 'best of 4')])
        self.assertEqual([r['who'] for r in robots], ['run 7', 'run 9', 'seed 104', 'seed 103', 'seed 104', 'seed 103'])
        self.assertEqual([r['recorded'] for r in robots[:4]], [4.2, 5.9, 1.5, 2.4])
        self.assertIn('not an arm', robots[2]['row'])
        # in the engine: the body as its run stored it, in the larger array
        np.testing.assert_array_equal(robots[2]['genome'], as_stored(small_body(104)))
        # in the 2013 simulator: the same body, written into the 2013 settings file
        rows = [m.group(2) for m in c13.LAYER.finditer(robots[4]['vxa'])]
        np.testing.assert_array_equal(c13.grid_from_rows(rows), small_body(104))
        # no score in the 2013 simulator is on record before the transfer has been computed
        self.assertEqual([(r['recorded'], r['ours'], r['evolved_score']) for r in robots[4:]],
                         [(None, False, 1.5), (None, False, 2.4)])

    def test_the_transfer_score_must_repeat_once_it_is_on_record(self):
        ours = [(s, f'seed {k}', os.path.join(self.tmp.name, f'trialX_s{k}'), 'final_population.pkl, individual 1')
                for k, s in self.scores.items()]
        robots = rc.engine_robots(ours, 'own search 2026, arm D, in the MuJoCo engine', 'noCost',
                                  transfer={'seed 104': 0.9, 'seed 103': 1.8})
        self.assertEqual([(r['recorded'], r['ours']) for r in robots[4:]], [(0.9, True), (1.8, True)])
        import json
        with open(os.path.join(self.tmp.name, 'transfer_arm_D.json'), 'w') as f:
            json.dump({'champions': [{'label': 'seed 1', 'score': 2.5}, {'label': 'seed 2', 'score': 3.5}]}, f)
        self.assertEqual(rc.transfer_scores_of('D', self.tmp.name), {'seed 1': 2.5, 'seed 2': 3.5})
        self.assertEqual(rc.transfer_scores_of('D', os.path.join(self.tmp.name, 'nowhere')), {})

    def test_fewer_than_three_runs_are_not_shown(self):
        with self.assertRaises(SystemExit):
            rc.rehearsal_robots('trialX_s', 9, self.tmp.name)             # no run has nine generations

    def frames_of_a_straight_walk(self, distance=0.03):
        """Two voxels moving `distance` metres (of the 2013 scale) in 10 cycles."""
        start = np.array([[0.0005, 0.0005, 0.0005], [0.0015, 0.0005, 0.0005]])
        times = np.array([0.025 * k for k in range(11)])
        frames = np.array([np.hstack([start + [distance * k / 10, 0, 0], np.tile([1.0, 0, 0, 0], (2, 1)),
                                      np.full((2, 3), 0.001)]) for k in range(11)])
        return np.array([1, 3]), times, frames[:, :, 0:3].mean(axis=1), frames

    def test_the_frames_must_be_the_evaluation_that_was_scored(self):
        from unittest import mock
        materials, times, cms, frames = self.frames_of_a_straight_walk()
        robot = {'row': 'own search 2026, arm D, in the MuJoCo engine', 'who': 'seed 4', 'column': 'median of 10',
                 'recorded': 3.0, 'simulator': 'mujoco', 'genome': None, 'ours': True}
        true_score = float(np.linalg.norm(cms[-1] - cms[0]) / rc.BODY)
        with mock.patch.object(rc, 'record_in_the_engine', return_value=(true_score, False, materials, times, cms, frames)):
            check, *_ = rc.simulate(dict(robot, recorded=true_score), 'x', 0.025)
            self.assertTrue(check['identical_to_the_last_digit'])
            self.assertEqual((check['voxels'], check['frames'], len(check['body_lengths_per_cycle'])), (2, 11, 10))
            self.assertAlmostEqual(check['score_from_first_and_last_frame'], 3.0)
            first, second = rc.captions(dict(robot, recorded=true_score), check)
            self.assertIn('seed 4 (median of 10)', first)
            self.assertIn('3.00 body lengths in 10 cycles (its recorded score), 2 voxels', second)
            with self.assertRaises(SystemExit) as stop:                     # a recorded score that differs in the last digits
                rc.simulate(dict(robot, recorded=true_score + 1e-12), 'x', 0.025)
            self.assertIn('would not be the evaluation that was scored', str(stop.exception))
        with mock.patch.object(rc, 'record_in_the_engine', return_value=(2.0, False, materials, times, cms, frames)):
            with self.assertRaises(SystemExit):                             # frames that do not give the score
                rc.simulate(dict(robot, recorded=2.0), 'x', 0.025)

    def test_the_caption_of_a_robot_in_the_simulator_it_was_not_evolved_in(self):
        check = {'score_in_the_campaign_simulator': 1.2, 'voxels': 500, 'from_a_run_of_this_project': False,
                 'recorded_score': None, 'robot': 'x'}
        robot = {'row': 'the same robot in the 2013 simulator', 'who': 'seed 4', 'column': 'median of 10',
                 'simulator': '2013', 'evolved_score': 2.4}
        first, second = rc.captions(robot, check)
        self.assertEqual(first, 'the same robot in the 2013 simulator, seed 4')
        self.assertIn('1.20 body lengths in 10 cycles, 0.50 of its score in the engine', second)
        # the captions of the arms shown before are what they were
        old = {'score_in_the_campaign_simulator': 4.22, 'voxels': 652, 'from_a_run_of_this_project': False,
               'recorded_score': 4.39, 'robot': '2013 original, run 101 (median of 35)'}
        self.assertEqual(rc.captions({'row': '2013 original', 'who': 'run 101', 'column': 'median of 35'}, old),
                         ('2013 original, run 101 (median of 35)',
                          '4.22 body lengths in 10 cycles (recorded as 4.39 by the 2013 build), 652 voxels'))

    def test_three_rows_on_one_sheet(self):
        w, h = rc.PANEL
        blank = np.full((h, w, 3), 255, np.uint8)
        sheets = rc.assemble([[blank, blank]] * 6, [('a', 'b')] * 6, [0.0, 0.125], 24.0)
        self.assertEqual((len(sheets), sheets[0].size), (2, (2 * w + 6, 3 * h + 12)))
        sheets = rc.assemble([[blank]] * 4, [('a', 'b')] * 4, [0.0], 24.0)             # four robots: as before
        self.assertEqual(sheets[0].size, (2 * w + 6, 2 * h + 6))


class TestArmsWithOneSettingUndone(unittest.TestCase):
    """Arms E1 to E3 (27 November 2026, before any of them was started): shown next to arm D, each
    robot in the engine of its own arm, and none in the 2013 simulator."""

    DEPOSIT = [(4.2, 'run 7', 'folder', 'a.vxa'), (5.9, 'run 9', 'folder', 'b.vxa'), (3.1, 'run 2', 'folder', 'c.vxa')]
    D_SCORES = {k: 1.0 + 0.1 * ((k * 7) % 10) for k in range(1, 11)}        # ten different scores, not in seed order
    E_SCORES = {1: 0.9, 2: 0.4, 3: 0.6}

    def setUp(self):
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (('deposited', lambda condition: list(self.DEPOSIT)),
                            ('deposited_robot_text', lambda folder, name: f'<the robot file {name}>')):
            patcher = mock.patch.object(rc, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        make_runs(self.tmp.name, 'armD_s', self.D_SCORES)
        for arm in ('E1', 'E2', 'E3'):
            make_runs(self.tmp.name, f'arm{arm}_s', self.E_SCORES)

    def report(self, scores):
        return {'per_seed': [{'seed': k, 'champion': {'original': v, 'file': 'final_population.pkl, individual 1'}}
                             for k, v in scores.items()]}

    def robots_of(self, arm, reports):
        from unittest import mock
        with mock.patch.object(rc.aa, 'finished_arm', side_effect=lambda name, *a: reports.get(name)), \
                mock.patch.object(rc.aa, 'SEARCH_RUNS', self.tmp.name):
            return rc.robots_of(arm)

    def test_which_arms(self):
        for arm in ('E1', 'E2', 'E3'):
            self.assertTrue(rc.evolved_in_the_engine(arm))

    def test_six_robots_the_arm_below_arm_d(self):
        robots = self.robots_of('E1', {'D': self.report(self.D_SCORES), 'E1': self.report(self.E_SCORES)})
        self.assertEqual([(r['simulator'], r['column'], r.get('engine')) for r in robots],
                         [('2013', 'median of 3', None), ('2013', 'best of 3', None),
                          ('mujoco', 'median of 10', 'D'), ('mujoco', 'best of 10', 'D'),
                          ('mujoco', 'median of 3', 'E1'), ('mujoco', 'best of 3', 'E1')])
        ranked = sorted(self.D_SCORES, key=self.D_SCORES.get)
        self.assertEqual([r['who'] for r in robots],
                         ['run 7', 'run 9', f'seed {ranked[4]}', f'seed {ranked[9]}', 'seed 3', 'seed 1'])
        self.assertEqual([r['recorded'] for r in robots[2:]],
                         [self.D_SCORES[ranked[4]], self.D_SCORES[ranked[9]], 0.6, 0.9])
        self.assertEqual((robots[2]['row'], robots[4]['row']), ('arm D', 'arm E1: global damping back to 0.01'))
        # each from the body its own run stored
        np.testing.assert_array_equal(robots[2]['genome'], as_stored(small_body(ranked[4])))
        np.testing.assert_array_equal(robots[5]['genome'], as_stored(small_body(1)))
        # nothing is shown in a simulator it was not evolved in: no transfer outcome for these arms
        self.assertFalse(any('evolved_score' in r for r in robots))

    def test_every_e_arm_names_what_it_undoes(self):
        reports = {'D': self.report(self.D_SCORES)}
        rows = {}
        for arm in ('E1', 'E2', 'E3'):
            robots = self.robots_of(arm, dict(reports, **{arm: self.report(self.E_SCORES)}))
            rows[arm] = robots[4]['row']
            self.assertEqual({r['engine'] for r in robots[4:]}, {arm})
        self.assertEqual(rows, {'E1': 'arm E1: global damping back to 0.01',
                                'E2': 'arm E2: amplitude 20% with the volumetric law',
                                'E3': 'arm E3: hard floor, bodies set on it'})
        for row in rows.values():                                     # the longest caption fits a panel
            line = f'{row}, seed 10 (median of 3)'
            self.assertLessEqual(rc.fitting(line, rc.PANEL[0] - 16).getlength(line), rc.PANEL[0] - 16)

    def test_an_e_arm_is_shown_only_when_both_arms_have_their_reports(self):
        with self.assertRaises(SystemExit) as stop:
            self.robots_of('E2', {'E2': self.report(self.E_SCORES)})
        self.assertIn('Arm D has no report', str(stop.exception))
        with self.assertRaises(SystemExit) as stop:
            self.robots_of('E2', {'D': self.report(self.D_SCORES)})
        self.assertIn('Arm E2 has no report', str(stop.exception))

    def test_arm_d_s_own_video_is_what_it_was(self):
        robots = self.robots_of('D', {'D': self.report(self.D_SCORES)})
        self.assertEqual([(r['simulator'], r['column']) for r in robots],
                         [('2013', 'median of 3'), ('2013', 'best of 3'), ('mujoco', 'median of 10'), ('mujoco', 'best of 10'),
                          ('2013', 'median of 10'), ('2013', 'best of 10')])
        self.assertEqual(robots[2]['row'], 'own search, arm D, MuJoCo engine')
        self.assertEqual({r.get('engine') for r in robots[2:4]}, {'D'})
        self.assertTrue(all('evolved_score' in r for r in robots[4:]))

    def test_each_robot_is_simulated_with_the_settings_of_its_own_arm(self):
        from unittest import mock
        import render_transfer as rt
        d = rc.engine_parameters()
        self.assertEqual(d, rc.engine_parameters('D'))
        differs = {arm: {k: v for k, v in rc.engine_parameters(arm).items() if d.get(k) != v} for arm in ('E1', 'E2', 'E3')}
        self.assertEqual(differs, {'E1': {'global_damping': 0.01}, 'E2': {'actuation_amplitude': 0.2, 'poisson': True},
                                   'E3': {'floor_contact': 'voxelyze', 'start': 'floor'}})
        with mock.patch.object(rt, 'mujoco_frames', side_effect=lambda genome, params, every: params):
            self.assertEqual(rc.record_in_the_engine({'genome': None, 'engine': 'E2'}, 0.01)['actuation_amplitude'], 0.2)
            self.assertEqual(rc.record_in_the_engine({'genome': None}, 0.01), d)                  # arm D unless it says
            self.assertEqual(rc.record_in_the_engine({'genome': None, 'engine': 'E2'}, 0.01, d), d)   # or as handed over

    def test_a_rehearsal_with_an_e_arm_s_settings_has_two_rows(self):
        make_runs(self.tmp.name, 'trialE3_s', {101: 1.3, 102: 1.7, 103: 2.4})
        robots = rc.rehearsal_robots('trialE3_s', 2, self.tmp.name, settings_of='E3')
        self.assertEqual([(r['simulator'], r.get('engine')) for r in robots],
                         [('2013', None), ('2013', None), ('mujoco', 'E3'), ('mujoco', 'E3')])
        self.assertIn('not an arm', robots[2]['row'])
        self.assertEqual(len(rc.rehearsal_robots('trialE3_s', 2, self.tmp.name)), 6)          # arm D's settings: three rows


class TestRecordingTheEngine(unittest.TestCase):
    def test_under_the_settings_of_each_e_arm_too(self):
        """The same for the three settings of arms E1 to E3: higher damping, the larger amplitude
        with the volumetric law, and the hard floor with the body set on it."""
        from src.evolution import mujoco_tendon_evaluator as evaluation
        genome = as_stored(small_body(3))
        scores = {}
        for arm in ('D', 'E1', 'E2', 'E3'):
            params = rc.engine_parameters(arm)
            recorded = float(evaluation._eval_worker((genome, None, None, params)))
            robot = {'row': f'a small body with the settings of arm {arm}', 'who': 'seed 0', 'column': 'median of 1',
                     'recorded': recorded, 'simulator': 'mujoco', 'genome': genome, 'ours': True, 'engine': arm}
            check, materials, times, cms, frames = rc.simulate(robot, 'x', 0.0125, params)
            self.assertTrue(check['identical_to_the_last_digit'], arm)
            self.assertAlmostEqual(check['score_from_first_and_last_frame'], recorded, places=6)
            self.assertFalse(check['blew_up'])
            scores[arm] = recorded
        self.assertEqual(len(set(scores.values())), 4)       # four settings, four different evaluations of one body

    def test_the_recorded_evaluation_is_the_one_a_run_makes(self):
        """A small body, stored as a run stores it, through the search's own evaluation under the
        preset of arm D and through the recording used for the video: the same score to the last
        digit, and frames that give that score."""
        from src.evolution import mujoco_tendon_evaluator as evaluation
        genome = as_stored(small_body(3))
        params = rc.engine_parameters()
        recorded = float(evaluation._eval_worker((genome, None, None, params)))
        self.assertGreater(recorded, 0.0)                   # a slow body: the search's early stop may end it early
        robot = {'row': 'a small body in the MuJoCo engine', 'who': 'seed 0', 'column': 'median of 1', 'recorded': recorded,
                 'simulator': 'mujoco', 'genome': genome, 'ours': True}
        check, materials, times, cms, frames = rc.simulate(robot, 'x', 0.0125, params)
        self.assertTrue(check['identical_to_the_last_digit'])
        self.assertEqual(check['score_of_the_recorded_evaluation'], recorded)
        self.assertAlmostEqual(check['score_from_first_and_last_frame'], recorded, places=6)
        self.assertEqual((len(materials), frames.shape[1:]), (int((small_body(3) != 0).sum()), (len(materials), 10)))
        self.assertFalse(check['blew_up'])


if __name__ == '__main__':
    unittest.main()
