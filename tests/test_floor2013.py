"""The 2013 simulator's floor and start as options of the engine, added 25 November 2026:
--floor-contact rule2013, --start workspace, and the preset cheney2013-floor that sets both.

The rule had been tried first as an emulation outside the engine
(paper/diagnostics_2026-11-25/floor_softness.py), checked against the 2013 simulator itself and
run on the 140 champions of the campaign. The tests here hold the built-in rule to that
emulation, score for score, so that what was measured with the emulation holds for the engine.
"""
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
sys.path.insert(0, os.path.join(ROOT, 'paper', 'diagnostics_2026-11-25'))
import floor_softness as fs                                   # noqa: E402
import transfer_scores as ts                                  # noqa: E402
from src.evolution import cheney2013 as c13                   # noqa: E402
from src.evolution import mujoco_tendon_evaluator as evaluation   # noqa: E402
from src.evolution.genome_config import VOXEL_GRID_SHAPE, VOXEL_INTERIOR_MIN   # noqa: E402
from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics     # noqa: E402

SPRING = 5000.0                      # N/m: E x size / 2 for the soft and the muscle material
WEIGHT = 1e-3 * 274.68               # N: one voxel in the engine's units (1 g at the rescaled 2.8 g)
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def block(shape, material=3, at=(3, 3, 0)):
    g = np.zeros((10, 10, 10), np.int8)
    g[at[0]:at[0] + shape[0], at[1]:at[1] + shape[1], at[2]:at[2] + shape[2]] = material
    return g


def walker(variant=0, up=0):
    """A small body with both muscle phases, a soft and a stiff voxel, `up` layers above the bottom."""
    g = np.zeros((10, 10, 10), np.int8)
    g[4:6, 4:7, up:up + 2] = 1
    g[4:6, 4:5, up:up + 2] = 2
    g[4, 6, up + 1] = 3
    g[5, 6, up + 1] = 4
    if variant:
        g[4 + variant % 2, 7, up] = 1 + variant % 2
    return g


def engine(floor_contact='rule2013', friction=SS):
    return MuJoCoBeamPhysics(actuation_amplitude=0.14, actuation_frequency=40.0, fitness_mode='forward',
                             friction=friction, materials='cheney2013', floor_contact=floor_contact, poisson=False,
                             direction='any', divide_by='workspace', workspace_voxels=10, global_damping=0.001)


def score(e, grid, height=0.0):
    e.load_robot(np.asarray(grid), voxel_size=0.01, initial_height=height)
    return float(e.get_fitness(0.25, 0.0, early_term_threshold=-1e9))


class TestTheRuleInTheEngine(unittest.TestCase):
    def test_a_block_rests_where_the_spring_says(self):
        """27 voxels on 9: three voxel weights on each spring, 0.0165 of a voxel. The 2013
        simulator itself rests this block at 0.4835 (paper/diagnostics_2026-11-25/floor_checks.json)."""
        e = engine()
        e.load_robot(block((3, 3, 3)), voxel_size=0.01)
        for _ in range(int(0.15 / e.default_timestep)):
            e.step()
        lowest = float(e.data.xpos[1:, 2].min() / 0.01)
        self.assertAlmostEqual(0.5 - 3 * WEIGHT / SPRING / 0.01, 0.4835, places=4)
        self.assertAlmostEqual(lowest, 0.4835, delta=0.0005)
        self.assertFalse(e.diverged())

    def test_the_other_floors_are_as_they_were(self):
        e = engine('voxelyze')
        e.load_robot(block((3, 3, 3)), voxel_size=0.01)
        self.assertIsNone(e._floor_dof)
        self.assertFalse(e.model.opt.disableflags & int(__import__('mujoco').mjtDisableBit.mjDSBL_CONTACT))
        for _ in range(int(0.15 / e.default_timestep)):
            e.step()
        self.assertGreater(float(e.data.xpos[1:, 2].min() / 0.01), 0.4995)       # the hard floor does not give

    def test_mujocos_contact_is_off_under_the_rule(self):
        import mujoco
        e = engine()
        e.load_robot(block((2, 2, 2)), voxel_size=0.01)
        self.assertTrue(e.model.opt.disableflags & int(mujoco.mjtDisableBit.mjDSBL_CONTACT))
        for _ in range(200):
            e.step()
        self.assertEqual(int(e.data.ncon), 0)
        self.assertIsNone(e._ss_sliding)                       # MuJoCo's stick-slip friction is not in play

    def test_a_loaded_body_replaces_the_rule_of_the_one_before(self):
        e = engine()
        e.load_robot(block((1, 1, 2)), voxel_size=0.01)
        self.assertEqual(len(e._floor_dof), 2)
        e.load_robot(block((2, 2, 2)), voxel_size=0.01)
        self.assertEqual(len(e._floor_dof), 8)
        self.assertEqual(len(e._floor_E), 8)

    def test_floors_and_bodies_it_does_not_take(self):
        with self.assertRaises(ValueError):
            engine('ice')
        e = engine()
        with self.assertRaises(ValueError):
            e.load_robot(block((1, 1, 2)), voxel_size=0.01, clamped=(0,))


class TestTheFrictionRule(unittest.TestCase):
    """One evaluation of the forces on a column of two voxels pushed 1 mm into the floor: 5 N of
    normal force on the lower voxel."""
    def make(self, friction=SS):
        import mujoco
        self.mujoco = mujoco
        self.e = engine(friction=friction)
        self.e.load_robot(block((1, 1, 2)), voxel_size=0.01)
        self.dof = np.asarray(self.e.model.jnt_dofadr[:2])
        self.low = int(np.argmin(self.e.data.xpos[1:, 2]))
        self.e.data.qpos[self.e.model.jnt_qposadr[:2] + 2] -= 0.001

    def floor_effect(self, velocity):
        data = self.e.data
        for k in range(2):
            data.qvel[self.dof[k]:self.dof[k] + 3] = velocity
        self.mujoco.mj_forward(self.e.model, data)
        strain = self.e.voxel_strain(0.0)
        dof, self.e._floor_dof = self.e._floor_dof, None       # the engine's forces without its floor
        own, _ = self.e.forces(strain)
        self.e._floor_dof = dof
        with_floor, _ = self.e.forces(strain)
        return with_floor - own, with_floor, data.qvel[self.dof[self.low]:self.dof[self.low] + 3].copy()

    def test_the_spring_and_the_brake_on_a_fast_voxel(self):
        self.make()
        added, _, velocity = self.floor_effect([1.0, 0.0, 0.0])
        self.assertAlmostEqual(added[self.low, 2], SPRING * 0.001, places=6)
        self.assertAlmostEqual(added[self.low, 0], -0.5 * SPRING * 0.001, places=6)
        self.assertAlmostEqual(added[self.low, 1], 0.0, places=9)
        self.assertEqual(velocity[0], 1.0)
        self.assertTrue(np.allclose(added[1 - self.low], 0.0))                 # the upper voxel is off the floor

    def test_the_brake_acts_against_the_motion(self):
        self.make()
        added, _, _ = self.floor_effect([-0.6, 0.8, 0.0])
        self.assertAlmostEqual(added[self.low, 0], +0.6 * 2.5, places=6)
        self.assertAlmostEqual(added[self.low, 1], -0.8 * 2.5, places=6)

    def test_a_slow_voxel_is_stopped_dead_and_held(self):
        self.make()
        _, total, velocity = self.floor_effect([1e-4, -1e-4, 0.0])
        self.assertEqual((velocity[0], velocity[1]), (0.0, 0.0))
        self.assertTrue(np.all(total[self.low, :2] == 0.0))               # exactly zero, as the 2013 code tests for
        _, total, velocity = self.floor_effect([0.0, 0.0, 0.0])
        self.assertTrue(np.all(total[self.low, :2] == 0.0))
        self.assertEqual((velocity[0], velocity[1]), (0.0, 0.0))

    def test_the_stop_depends_on_the_time_step_as_in_2013(self):
        """A voxel is stopped when the brake would stop it within one step: 0.5 N dt >= m speed.
        With 2.5 N of brake on 1 g that is a speed of 2500 dt."""
        self.make()
        limit = 2500.0 * self.e.default_timestep
        _, _, velocity = self.floor_effect([1.05 * limit, 0.0, 0.0])
        self.assertGreater(velocity[0], 0.0)                                   # just fast enough to keep sliding
        _, _, velocity = self.floor_effect([0.95 * limit, 0.0, 0.0])
        self.assertEqual(velocity[0], 0.0)

    def test_damping_on_the_vertical_speed(self):
        self.make()
        still, _, _ = self.floor_effect([0.0, 0.0, 0.0])
        sinking, _, _ = self.floor_effect([0.0, 0.0, -0.1])
        damping = 0.8 * 2 * 1e-3 * np.sqrt(1e4 / 1e-3)                         # ColDampingZ 2 m sqrt(E size / m)
        self.assertAlmostEqual(sinking[self.low, 2] - still[self.low, 2], damping * 0.1, places=6)

    def test_friction_follows_the_floor_friction_that_was_given(self):
        for friction, brake in ((None, 0.5), (dict(SS, mu_s=0.8, mu_k=0.25), 0.25), ({'mode': 'single', 'mu': 0.3}, 0.3)):
            self.make(friction)
            added, _, _ = self.floor_effect([1.0, 0.0, 0.0])
            self.assertAlmostEqual(added[self.low, 0], -brake * SPRING * 0.001, places=6)


class TestTheSameAsTheEmulation(unittest.TestCase):
    def test_score_for_score(self):
        """The rule built into the engine against the emulation that was checked against the 2013
        simulator and run on the champions: the same score to the last digit, on the floor and
        from a height."""
        for grid, height in ((walker(), 0.0), (walker(1), 0.0), (walker(2, up=2), 0.02)):
            built_in = score(engine('rule2013'), grid, height)
            emulated = engine('voxelyze')
            emulated.load_robot(np.asarray(grid), voxel_size=0.01, initial_height=height)
            fs.install_2013_floor(emulated)
            self.assertEqual(built_in, float(emulated.get_fitness(0.25, 0.0, early_term_threshold=-1e9)))
            self.assertGreater(built_in, 0.0)

    def test_it_is_not_the_hard_floor(self):
        self.assertNotEqual(score(engine('rule2013'), walker()), score(engine('voxelyze'), walker()))


class TestWhereABodyStarts(unittest.TestCase):
    def test_start_height(self):
        self.assertEqual(c13.start_height(walker()), 0.0)
        self.assertAlmostEqual(c13.start_height(walker(up=3), 10, 0.01), 0.03)
        self.assertAlmostEqual(c13.start_height(walker(up=3)), 0.003)            # in the 2013 simulator's 1 mm voxels
        self.assertEqual(c13.start_height(np.zeros((10, 10, 10), np.int8)), 0.0)
        big = np.zeros(VOXEL_GRID_SHAPE, np.int8)                                # a genome: the workspace sits inside it
        i = VOXEL_INTERIOR_MIN
        big[i + 2:i + 4, i + 2:i + 4, i + 2:i + 4] = 1
        self.assertAlmostEqual(c13.start_height(big, 10, 0.01), 0.02)

    def arguments(self, **more):
        return dict(simulation_time=0.25, settle_time=0.0, actuation_frequency=40.0, actuation_amplitude=0.14,
                    attach_controller=False, fitness_mode='forward', friction=SS, early_term_threshold=-1e9,
                    body='beam', poisson=False, materials='cheney2013', floor_contact='rule2013', direction='any',
                    divide_by='workspace', workspace_voxels=10, global_damping=0.001, **more)

    def test_the_evaluator_starts_a_body_where_it_is(self):
        up = walker(up=2)
        from_its_height = score(engine(), up, 0.02)
        on_the_floor = score(engine(), up, 0.0)
        self.assertNotEqual(from_its_height, on_the_floor)
        placed = evaluation.MuJoCoTendonEvaluator(start='workspace', **self.arguments())
        floored = evaluation.MuJoCoTendonEvaluator(**self.arguments())
        try:
            self.assertEqual(placed.evaluate_single(up), from_its_height)
            self.assertEqual(floored.evaluate_single(up), on_the_floor)
            self.assertEqual(placed.evaluate_single(walker()), floored.evaluate_single(walker()))   # on the bottom: the same
            # the worker processes of a pool take the same path
            self.assertEqual(evaluation._eval_worker((up, None, None, dict(placed._params))), from_its_height)
            self.assertEqual(evaluation._eval_worker((up, None, None, dict(floored._params))), on_the_floor)
        finally:
            placed.close()
            floored.close()

    def test_starts_it_does_not_take(self):
        with self.assertRaises(ValueError):
            evaluation.MuJoCoTendonEvaluator(start='orbit', **self.arguments())
        arguments = self.arguments()
        arguments['workspace_voxels'] = None
        arguments['divide_by'] = 'body'
        with self.assertRaises(ValueError):
            evaluation.MuJoCoTendonEvaluator(start='workspace', **arguments)


class TestThePreset(unittest.TestCase):
    def test_the_old_preset_is_what_it_was(self):
        """Everything scored with --preset cheney2013 up to 25 November 2026 (the transfer outcome
        of the protocol among it) must stay repeatable: the preset is not touched."""
        import run_tendon_evolution as runner
        self.assertEqual(runner._PRESETS['cheney2013'], [
            ('body', 'beam'), ('materials', 'cheney2013'), ('floor_contact', 'voxelyze'),
            ('friction_static', 1.0), ('friction_kinetic', 0.5),
            ('freq', 40.0), ('amp', 0.14), ('poisson', 'off'), ('damping_global', 0.001),
            ('sim_time', 0.25), ('settle', 0.0),
            ('direction', 'any'), ('divide_by', 'workspace'), ('fitness', 'forward'),
            ('grid_size', 10), ('no_trim', True)])

    def test_the_new_preset_differs_in_the_floor_and_the_start_only(self):
        import run_tendon_evolution as runner
        old, new = dict(runner._PRESETS['cheney2013']), dict(runner._PRESETS['cheney2013-floor'])
        self.assertEqual({k for k in new if new[k] != old.get(k)}, {'floor_contact', 'start'})
        self.assertEqual((new['floor_contact'], new['start']), ('rule2013', 'workspace'))
        self.assertEqual(set(old) - set(new), set())

    def test_the_scoring_script_reads_either_preset(self):
        old = ts.evaluator_arguments()
        new = ts.evaluator_arguments(preset='cheney2013-floor')
        self.assertEqual((old['floor_contact'], old['start']), ('voxelyze', 'floor'))
        self.assertEqual((new['floor_contact'], new['start']), ('rule2013', 'workspace'))
        self.assertEqual({k for k in new if new[k] != old[k]}, {'floor_contact', 'start'})

    def test_what_was_scored_before_is_still_found(self):
        """The start became a setting on 25 November 2026. An evaluation kept before that day was
        made with the body set on the floor, and must still be found under the same name."""
        before = {'floor_contact': 'voxelyze', 'voxel_size': 0.01}
        now = dict(before, start='floor')
        self.assertEqual(ts.evaluation_key(walker(), before, 1.0, 'tag'), ts.evaluation_key(walker(), now, 1.0, 'tag'))
        self.assertNotEqual(ts.evaluation_key(walker(), before, 1.0, 'tag'),
                            ts.evaluation_key(walker(), dict(before, start='workspace'), 1.0, 'tag'))

    def run_cli(self, arguments, folder):
        return subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py')] + arguments, cwd=folder,
                              capture_output=True, text=True, timeout=1800)

    def test_a_run_under_the_new_preset(self):
        """The search's own command line under --preset cheney2013-floor: the manifest says what
        ran, and every robot of the final population gets the same score from the scoring script
        when it is given that preset."""
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli(['--preset', 'cheney2013-floor', '--no-age-pareto', '--gen', '1', '--pop', '4', '--workers',
                              '1', '--grid-size', '5', '--seed', '3', '--name', 'floor_run'], tmp)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
            self.assertIn("the 2013 simulator's own floor rule", r.stdout)
            self.assertIn('starts where it is in the workspace', r.stdout)
            with open(os.path.join(tmp, 'results', 'floor_run', 'manifest.json')) as f:
                settings = json.load(f)['invocations'][0]
            self.assertEqual(settings['preset_applied']['floor_contact'], 'rule2013')
            self.assertEqual(settings['preset_applied']['start'], 'workspace')
            self.assertEqual((settings['settings']['floor_contact'], settings['settings']['start']), ('rule2013', 'workspace'))
            with open(os.path.join(tmp, 'results', 'floor_run', 'final_population.pkl'), 'rb') as f:
                population = pickle.load(f)
        params = ts.worker_parameters(ts.evaluator_arguments(early_stop=True, workspace=5, preset='cheney2013-floor'))
        fitnesses = [float(v) for v in population['fitnesses']]
        self.assertGreater(max(fitnesses), 0)
        for i, (genome, fitness) in enumerate(zip(population['genomes'], fitnesses)):
            self.assertEqual(ts.score_one((str(i), np.asarray(genome), params, 1.0))['score'], fitness)

    def test_the_2013_simulator_has_its_own_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli(['--simulator', 'voxelyze2013', '--start', 'workspace', '--gen', '1', '--pop', '2',
                              '--name', 'x'], tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--start', r.stdout + r.stderr)

    def test_the_rule_is_for_beam_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli(['--floor-contact', 'rule2013', '--gen', '1', '--pop', '2', '--name', 'x'], tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('only applies to --body beam', r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
