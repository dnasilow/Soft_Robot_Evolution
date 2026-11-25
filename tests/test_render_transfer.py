"""The side-by-side video of a champion in the two simulators (paper/analysis/render_transfer.py):
the parts that need neither the 2013 simulator nor a graphics context, and the recording of the
MuJoCo evaluation."""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
import render_transfer as rt        # noqa: E402
import transfer_scores as ts        # noqa: E402
from src.evolution import cheney2013 as c13   # noqa: E402

MM = c13.VOXEL_SIZE_2013


def row(arm, seed, ratio, layer=0, placed=None):
    r = {'set': f'arm_{arm}', 'label': f'seed {seed}', 'ratio': ratio, 'lowest_layer': layer}
    if placed is not None:
        r['placed'] = {'ratio': placed}
    return r


def first_frame(cells, shift=(0.0, 0.0, 0.0)):
    """Voxel states as a simulator records them: centre (m), orientation, size."""
    f = np.zeros((len(cells), 10))
    f[:, 0:3] = (np.array(cells, float) + 0.5) * MM + np.array(shift)
    f[:, 3] = 1.0
    f[:, 7:10] = MM
    return f


class TestWhichRobots(unittest.TestCase):
    def test_the_median_is_the_lower_middle_one(self):
        self.assertEqual(rt.median_by([3, 1, 2], lambda v: v), 2)
        self.assertEqual(rt.median_by([4, 3, 1, 2], lambda v: v), 2)

    def test_one_champion_on_the_floor_per_arm_and_one_off_it_where_there_are_three(self):
        champions = [row('R', 1, 0.9), row('R', 2, 0.5), row('R', 3, 0.7), row('R', 4, 0.1, layer=1, placed=0.4),
                     row('Rc', 1, 0.6), row('Rc', 2, 0.8), row('Rc', 3, 0.2, layer=2, placed=0.9),
                     row('Rc', 4, 0.3, layer=1, placed=0.5), row('Rc', 5, 0.1, layer=3, placed=0.7),
                     {'set': 'deposit_noCost', 'label': 'run_1', 'ratio': 0.5, 'lowest_layer': 0}]
        chosen = [(r['set'], r['label'], how) for r, how in rt.choose(champions)]
        self.assertEqual(chosen, [('arm_R', 'seed 3', 'floor'),        # 0.5 0.7 0.9; one body off the floor is not shown
                                  ('arm_Rc', 'seed 1', 'floor'),       # 0.6 0.8
                                  ('arm_Rc', 'seed 5', 'placed')])     # as placed: 0.5 0.7 0.9

    def test_deposited_champions_are_not_shown(self):
        self.assertEqual(rt.choose([{'set': 'deposit_noCost', 'label': 'run_1', 'ratio': 0.5, 'lowest_layer': 0}]), [])


class TestTheSameBody(unittest.TestCase):
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 1, 2)]
    materials = np.array([1, 3, 2, 4, 1])

    def test_the_same_cells_and_materials_wherever_the_body_stands(self):
        a = first_frame(self.cells, shift=(3 * MM, 4 * MM, 2 * MM))
        b = first_frame(self.cells, shift=(-0.9 * MM, -0.63 * MM, 0.0))       # centred on its mean, on the floor
        self.assertTrue(rt.same_body(self.materials, a, self.materials, b))
        order = [4, 2, 0, 3, 1]                                                # the simulators list voxels in their own order
        self.assertTrue(rt.same_body(self.materials, a, self.materials[order], b[order]))

    def test_another_material_another_cell_or_swapped_axes_is_not_the_same_body(self):
        a = first_frame(self.cells)
        other = self.materials.copy()
        other[0] = 3
        self.assertFalse(rt.same_body(self.materials, a, other, a))
        moved = list(self.cells)
        moved[4] = (0, 1, 2)
        self.assertFalse(rt.same_body(self.materials, a, self.materials, first_frame(moved)))
        swapped = [(y, x, z) for x, y, z in self.cells]
        self.assertFalse(rt.same_body(self.materials, a, self.materials, first_frame(swapped)))
        self.assertFalse(rt.same_body(self.materials, a, self.materials[:4], a[:4]))


class TestMeasures(unittest.TestCase):
    def test_heading_per_cycle_and_lowest_point(self):
        times = np.linspace(0.0, 0.25, 101)
        cms = np.zeros((101, 3))
        cms[:, 1] = 0.04 * times / 0.25                       # 4 body lengths along +y in 10 cycles
        self.assertAlmostEqual(rt.heading(cms), 90.0)
        steps = rt.per_cycle(times, cms)
        self.assertEqual(len(steps), 10)
        for s in steps:
            self.assertAlmostEqual(s, 0.4, places=3)
        frames = np.zeros((2, 3, 10))
        frames[..., 2] = 0.5 * MM
        frames[..., 9] = MM
        frames[1, 2, 2] = 0.2 * MM                            # one voxel 0.3 of a voxel into the floor
        self.assertAlmostEqual(rt.lowest_point(frames), -0.3)

    def test_how_far_a_body_has_turned(self):
        cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 1, 2), (0, 1, 2)]
        start = first_frame(cells)
        frames = [start]
        for degrees in (30.0, 90.0, 170.0):
            a = np.radians(degrees)
            about_y = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])   # rolling forward
            f = start.copy()
            f[:, 0:3] = start[:, 0:3] @ about_y.T + np.array([0.004 * degrees, 0.0, 0.001])            # and moving on
            frames.append(f)
        angles = rt.turned(np.array(frames))
        for got, expected in zip(angles, (0.0, 30.0, 90.0, 170.0)):
            self.assertAlmostEqual(got, expected, places=6)
        squeezed = start.copy()
        squeezed[:, 0:3] *= 1.1                               # a body that only swells has not turned
        self.assertAlmostEqual(rt.turned(np.array([start, squeezed]))[1], 0.0, places=6)


class TestRecordingTheMuJoCoEvaluation(unittest.TestCase):
    def test_the_frames_come_from_the_evaluation_that_is_scored(self):
        g = np.zeros((10, 10, 10), np.int8)
        g[4:6, 4:7, 2:4] = 1                                  # two layers up, not touching the bottom
        g[4:6, 4:5, 2:4] = 2
        g[4, 6, 3] = 3
        g[5, 6, 3] = 4
        params = ts.worker_parameters(ts.evaluator_arguments())
        expected = ts.score_one(('k', g, params, 1.0))['score']
        score, blew_up, materials, times, cms, frames = rt.mujoco_frames(g, params, 0.0125)
        self.assertEqual(score, expected)                     # recording changes nothing
        self.assertFalse(blew_up)
        self.assertEqual(len(times), 21)
        self.assertEqual(frames.shape, (21, int((g != 0).sum()), 10))
        self.assertAlmostEqual(float(np.linalg.norm(cms[-1] - cms[0]) / (10 * MM)), score, places=9)
        self.assertAlmostEqual(float(frames[0][:, 2].min()), 0.5 * MM)        # set on the floor, in 2013 units
        self.assertEqual(sorted(set(materials.tolist())), [1, 2, 3, 4])       # 2013 numbering: 3 is the second muscle
        self.assertEqual(int((materials == 3).sum()), int((g == 2).sum()))
        # the same body, written as the 2013 simulator would hold it
        cells = np.argwhere(g != 0)
        as_2013 = np.array([int(c13.OURS_TO_2013[int(g[tuple(c)])]) for c in cells])
        self.assertTrue(rt.same_body(as_2013, first_frame([tuple(c) for c in cells]), materials, frames[0]))


if __name__ == '__main__':
    unittest.main()
