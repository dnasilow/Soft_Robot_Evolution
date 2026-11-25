"""The emulation of the 2013 simulator's floor rule used by the exploratory floor test
(paper/diagnostics_2026-11-25/floor_softness.py): the spring, the brake, the stop, and that the
engine's own code and floor are left alone for the other floors."""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'diagnostics_2026-11-25'))
import floor_softness as fs         # noqa: E402
import transfer_scores as ts        # noqa: E402

SPRING = 5000.0                      # N/m: E x size / 2 for the soft and the muscle material
WEIGHT = 1e-3 * 274.68               # N: one voxel in the engine's units (1 g at the rescaled 2.8 g)


def block(shape, material=3, at=(3, 3, 0)):
    g = np.zeros((10, 10, 10), np.int8)
    g[at[0]:at[0] + shape[0], at[1]:at[1] + shape[1], at[2]:at[2] + shape[2]] = material
    return g


class TestTheSpring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = ts.worker_parameters(ts.evaluator_arguments())

    def lowest(self, floor):
        _, _, frames, blew_up = fs.run_engine(block((3, 3, 3)), self.params, floor, 0.15, 0.01, 0.0)
        self.assertFalse(blew_up)
        return float(frames[-1][:, 2].min() / fs.VOXEL)        # height of the lowest voxel centres, in voxels

    def test_a_block_rests_where_the_spring_says(self):
        """27 voxels on 9: three voxel weights on each spring, 0.0165 of a voxel. The 2013
        simulator itself gives 0.4835 for this block (floor_checks.json)."""
        expected = 0.5 - 3 * WEIGHT / SPRING / 0.01
        self.assertAlmostEqual(expected, 0.4835, places=4)
        self.assertAlmostEqual(self.lowest('rule2013'), expected, delta=0.0005)

    def test_the_presets_floor_does_not_give(self):
        self.assertGreater(self.lowest('hard'), 0.4995)


class TestTheFrictionRule(unittest.TestCase):
    """One step of the rule on a column of two voxels pushed 0.001 m into the floor: 5 N of normal
    force on the lower voxel."""
    def setUp(self):
        import mujoco
        from src.evolution import mujoco_tendon_evaluator as evaluation
        self.mujoco = mujoco
        params = ts.worker_parameters(ts.evaluator_arguments())
        self.engine = evaluation._make_engine(params)
        self.engine.load_robot(block((1, 1, 2)), voxel_size=0.01, initial_height=0.0, gait_params=None)
        self.plain = self.engine.forces
        fs.install_2013_floor(self.engine)
        self.dof = np.asarray(self.engine.model.jnt_dofadr[:2])
        self.low = int(np.argmin(self.engine.data.xpos[1:, 2]))
        adr = self.engine.model.jnt_qposadr[:2]
        self.engine.data.qpos[adr + 2] -= 0.001               # the whole column 1 mm into the floor

    def floor_effect(self, velocity):
        """What the rule adds to the engine's own forces when both voxels move at this velocity."""
        data = self.engine.data
        for k in range(2):
            data.qvel[self.dof[k]:self.dof[k] + 3] = velocity
        self.mujoco.mj_forward(self.engine.model, data)
        strain = self.engine.voxel_strain(0.0)
        own, _ = self.plain(strain)
        own = own.copy()
        with_floor, _ = self.engine.forces(strain)
        return with_floor - own, own, data.qvel[self.dof[self.low]:self.dof[self.low] + 3].copy()

    def test_mujocos_contact_is_off(self):
        self.assertTrue(self.engine.model.opt.disableflags & int(self.mujoco.mjtDisableBit.mjDSBL_CONTACT))

    def test_the_spring_and_the_brake_on_a_fast_voxel(self):
        added, _, velocity = self.floor_effect([1.0, 0.0, 0.0])
        self.assertAlmostEqual(added[self.low, 2], SPRING * 0.001, places=6)          # 5 N up, no vertical speed
        self.assertAlmostEqual(added[self.low, 0], -0.5 * SPRING * 0.001, places=6)   # braked with half of it
        self.assertAlmostEqual(added[self.low, 1], 0.0, places=9)
        self.assertEqual(velocity[0], 1.0)                                             # still sliding
        self.assertTrue(np.allclose(added[1 - self.low], 0.0))                         # the upper voxel is not on the floor

    def test_the_brake_acts_against_the_motion(self):
        added, _, _ = self.floor_effect([-0.6, 0.8, 0.0])
        self.assertAlmostEqual(added[self.low, 0], +0.6 * 2.5, places=6)
        self.assertAlmostEqual(added[self.low, 1], -0.8 * 2.5, places=6)

    def test_a_slow_voxel_is_stopped_dead_and_held(self):
        # the brake (2.5 N) would stop a 1 g voxel at 1e-4 m/s within one step: momentum zero, force cancelled
        added, own, velocity = self.floor_effect([1e-4, -1e-4, 0.0])
        self.assertEqual((velocity[0], velocity[1]), (0.0, 0.0))
        self.assertTrue(np.allclose((own + added)[self.low, :2], 0.0))
        # at rest and not pulled harder than its normal force: it stays held
        added, own, velocity = self.floor_effect([0.0, 0.0, 0.0])
        self.assertTrue(np.allclose((own + added)[self.low, :2], 0.0))
        self.assertEqual((velocity[0], velocity[1]), (0.0, 0.0))

    def test_damping_on_the_vertical_speed(self):
        still, _, _ = self.floor_effect([0.0, 0.0, 0.0])
        sinking, _, _ = self.floor_effect([0.0, 0.0, -0.1])
        damping = fs.COL_DAMP * 2 * 1e-3 * np.sqrt(1e4 / 1e-3)                        # 0.8 x 2 m sqrt(E size / m)
        self.assertAlmostEqual(sinking[self.low, 2] - still[self.low, 2], damping * 0.1, places=6)


class TestTheFloors(unittest.TestCase):
    def test_which_floor_does_what(self):
        params = {'voxel_size': 0.01, 'floor_contact': 'voxelyze', 'initial_height': 0.0}
        self.assertEqual(fs.floor_settings('hard', params), (params, None))
        settings, prepare = fs.floor_settings('default', params)
        self.assertEqual((settings['floor_contact'], prepare), ('mujoco', None))
        self.assertIs(fs.floor_settings('matched', params)[1], fs.soften_contact)
        self.assertIs(fs.floor_settings('rule2013', params)[1], fs.install_2013_floor)
        up = block((2, 2, 2), at=(3, 3, 3))
        settings, prepare = fs.floor_settings(fs.PLACED, params, up)
        self.assertAlmostEqual(settings['initial_height'], 0.03)
        self.assertIs(prepare, fs.install_2013_floor)
        self.assertEqual(params['initial_height'], 0.0)       # the settings given are not changed
        with self.assertRaises(ValueError):
            fs.floor_settings('ice', params)

    def test_a_body_on_the_bottom_has_one_evaluation_under_the_rule(self):
        on_the_bottom, up = block((2, 2, 2)), block((2, 2, 2), at=(3, 3, 2))
        self.assertEqual(fs.kept_name('k', fs.PLACED, on_the_bottom), fs.kept_name('k', 'rule2013', on_the_bottom))
        self.assertNotEqual(fs.kept_name('k', fs.PLACED, up), fs.kept_name('k', 'rule2013', up))
        self.assertEqual(len({fs.kept_name('k', f, up) for f in fs.FLOORS + (fs.PLACED,)}), 5)

    def test_the_measures_of_a_recorded_motion(self):
        times = np.linspace(0.0, 0.25, 101)
        cms = np.zeros((101, 3))
        cms[:, 0] = np.where(times <= 0.125, 0.02 * times / 0.125, 0.02 + 0.01 * (times - 0.125) / 0.125)
        frames = np.zeros((101, 4, 10))
        frames[..., 0:3] = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]) * fs.VOXEL + cms[:, None, :]
        frames[..., 2] += 0.5 * fs.VOXEL
        frames[..., 3] = 1.0
        frames[..., 7:10] = fs.VOXEL
        frames[40, 0, 2] = -0.2 * fs.VOXEL                     # one voxel 0.7 of a voxel below the surface for a moment
        m = fs.motion_measures(times, cms, frames)
        self.assertAlmostEqual(m['late_over_early'], 0.5, places=3)      # 2 body lengths, then 1
        self.assertAlmostEqual(m['sunk'], 0.7, places=6)
        self.assertAlmostEqual(m['distance_at_cycle'][10], 3.0, places=3)
        self.assertLess(m['turned_at_most'], 25.0)


if __name__ == '__main__':
    unittest.main()
