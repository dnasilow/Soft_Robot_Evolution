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


if __name__ == '__main__':
    unittest.main()
