"""Memory for the runs of arms D and E, 27 November 2026 (PROTOCOL.md, section 9.6).

Three changes, made before any run of those arms had started:
  (a) every run and every scoring process starts with one linear-algebra thread;
  (b) an evaluation that ends in an error which is not the robot's own stops the run instead of
      being scored 0;
  (c) the engine states how much working memory MuJoCo sets aside for a body.

None of them may change a number that an evaluation computes. The tests here hold that for a
small body; the champions of the campaign and whole runs of the search are held to it in
paper/diagnostics_2026-11-27/.
"""
import json
import os
import pickle
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import mujoco
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'paper', 'analysis'))
sys.path.insert(0, os.path.join(ROOT, 'paper', 'reference_2013'))
import search_arm                                                 # noqa: E402
import transfer_scores as ts                                      # noqa: E402
import src.physics.mujoco_beam_physics as beam                    # noqa: E402
from src.evolution import mujoco_tendon_evaluator as evaluation   # noqa: E402

SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
A_FAILED_ALLOCATION = ('Unable to allocate 4.91 MiB for an array with shape (463, 463, 3) and data type '
                       'float64')                                 # as numpy said it on 25 November 2026


def block(shape, material=1):
    g = np.zeros((10, 10, 10), np.int8)
    g[:shape[0], :shape[1], :shape[2]] = material
    return g


def mixed(shape):
    """Every material in one body."""
    g = np.zeros((10, 10, 10), np.int8)
    for i in range(shape[0]):
        for j in range(shape[1]):
            for k in range(shape[2]):
                g[i, j, k] = (1, 2, 3, 4)[(i + 2 * j + 3 * k) % 4]
    return g


def walker(variant=0):
    """A small body with both muscle phases, a soft and a stiff voxel."""
    g = np.zeros((10, 10, 10), np.int8)
    g[4:6, 4:7, 0:2] = 1
    g[4:6, 4:5, 0:2] = 2
    g[4, 6, 1] = 3
    g[5, 6, 1] = 4
    if variant:
        g[4 + variant % 2, 7, 0] = 1 + variant % 2
    return g


def engine(floor_contact='voxelyze'):
    return beam.MuJoCoBeamPhysics(actuation_amplitude=0.14, actuation_frequency=40.0, fitness_mode='forward',
                                  friction=SS, materials='cheney2013', floor_contact=floor_contact, poisson=False,
                                  direction='any', divide_by='workspace', workspace_voxels=10, global_damping=0.001)


def arguments(floor_contact='voxelyze', **more):
    return dict(simulation_time=0.25, settle_time=0.0, actuation_frequency=40.0, actuation_amplitude=0.14,
                attach_controller=False, fitness_mode='forward', friction=SS, early_term_threshold=-1e9,
                body='beam', poisson=False, materials='cheney2013', floor_contact=floor_contact, direction='any',
                divide_by='workspace', workspace_voxels=10, global_damping=0.001, **more)


def score(e, grid):
    e.load_robot(np.asarray(grid), voxel_size=0.01)
    return float(e.get_fitness(0.25, 0.0, early_term_threshold=-1e9))


def press_every_voxel_on_the_floor(e):
    """Every voxel's sphere into the floor, each layer a little deeper than the one below it so
    that no two voxels sit in the same place, and every voxel moving. MuJoCo then has all the
    contacts a body can have, with friction at work in each."""
    model, data, size = e.model, e.data, e.voxel_size
    for k, cell in enumerate(e.cells):
        data.qpos[model.jnt_qposadr[k] + 2] = size / 2 - (0.05 + 0.03 * cell[2]) * size
    data.qvel[:] = np.random.default_rng(0).normal(0.0, 0.5, model.nv)
    mujoco.mj_forward(model, data)


class TestStatedMemory(unittest.TestCase):
    def test_the_engine_states_what_it_says(self):
        e = engine()
        e.load_robot(block((3, 3, 3)), voxel_size=0.01)
        self.assertEqual(beam.arena_bytes(27), 8 * 2 ** 20 + 27 * 16 * 2 ** 10)
        self.assertEqual(e.model.narena, beam.arena_bytes(27))
        self.assertLess(beam.arena_bytes(1000), 25 * 2 ** 20)            # a full workspace: under 25 MB

    def test_a_body_cannot_use_a_fifth_of_it(self):
        """The most a body can use is every voxel in contact with the floor at once: its only
        MuJoCo constraints are the floor pairs, one contact per voxel, four rows each. Built here
        for a slab, for half the workspace and for the full workspace of 1000 voxels."""
        for floor, shape in (('voxelyze', (10, 10, 1)), ('voxelyze', (10, 10, 5)), ('voxelyze', (10, 10, 10)),
                             ('mujoco', (10, 10, 10)), ('rule2013', (10, 10, 10))):
            with self.subTest(floor=floor, shape=shape):
                e = engine(floor)
                e.load_robot(mixed(shape), voxel_size=0.01)
                n = len(e.cells)
                press_every_voxel_on_the_floor(e)
                contacts = 0 if floor == 'rule2013' else n            # the 2013 rule has no MuJoCo contact
                self.assertEqual((int(e.data.ncon), int(e.data.nefc)), (contacts, 4 * contacts))
                e.step()                                               # raises if anything was dropped
                self.assertFalse(e.diverged())
                used = int(e.data.maxuse_arena)                        # the most used so far, by MuJoCo's count
                self.assertGreater(used, 300 * n)
                self.assertLessEqual(5 * used, beam.arena_bytes(n), f'{used} bytes used by {n} voxels')
                self.assertLess(used, 3100 * n)                        # 2.9 kB per voxel, as measured

    def test_the_score_does_not_depend_on_it(self):
        """The same body with MuJoCo's own estimate in place of the statement: the same score to
        the last digit, on each floor."""
        for floor in beam.FLOOR_CONTACTS:
            with self.subTest(floor=floor):
                stated = engine(floor)
                with_statement = score(stated, walker())
                with mock.patch.object(beam, 'arena_bytes', return_value=-1):      # -1: MuJoCo estimates
                    own = engine(floor)
                    with_estimate = score(own, walker())
                self.assertGreater(own.model.narena, stated.model.narena)
                self.assertGreater(with_statement, 0.01)
                self.assertEqual(with_statement, with_estimate)

    def test_memory_that_runs_out_is_never_scored(self):
        """With too little memory MuJoCo drops the floor contact, counts a warning and goes on:
        the voxel sinks through the floor. The engine stops instead."""
        with mock.patch.object(beam, 'arena_bytes', return_value=1024):
            e = engine()
            with self.assertRaises(MemoryError) as stop:
                e.load_robot(block((1, 1, 1)), voxel_size=0.01)
                for _ in range(200):
                    e.step()
        self.assertIn('ran out of the working memory stated', str(stop.exception))

    def test_the_search_then_stops_too(self):
        """However MuJoCo reports it: a warning (1 kB for one voxel), its own error while it
        builds the model (1 kB for 200 voxels: a ValueError that speaks of memory) or while it
        simulates (300 kB for 200 voxels)."""
        params = dict(evaluation.MuJoCoTendonEvaluator(**arguments())._params)
        for size, body in ((1024, block((1, 1, 1))), (1024, block((10, 10, 2))), (300 * 1024, block((10, 10, 2)))):
            with self.subTest(size=size, voxels=int((body != 0).sum())):
                with mock.patch.object(beam, 'arena_bytes', return_value=size):
                    with self.assertRaises(evaluation.EvaluationStopped) as stop:
                        evaluation._eval_worker((body, None, None, params))
                self.assertIn('not a result of the robot', str(stop.exception))
                self.assertIn('memory', str(stop.exception).lower())


class TestWhichErrorsAreAScore(unittest.TestCase):
    def test_the_rule(self):
        own = evaluation.is_the_bodys_own
        for exc in (ValueError('No voxels in grid!'), ZeroDivisionError('float division by zero'),
                    FloatingPointError('overflow encountered'), OverflowError('math range error')):
            self.assertTrue(own(exc), repr(exc))
        for exc in (MemoryError(A_FAILED_ALLOCATION),
                    mujoco.FatalError('mj_stackAlloc: out of memory, stack overflow at mj_instantiateContact'),
                    ValueError('Error: engine error: mj_stackAlloc: out of memory, stack overflow at set0, line 291'),
                    ValueError('Error: engine error: Could not allocate memory'),
                    OSError(22, 'The paging file is too small for this operation to complete'),
                    ImportError('DLL load failed while importing _multiarray_umath: The paging file is too small '
                                'for this operation to complete.'),
                    RuntimeError("can't start new thread"), IndexError('tuple index out of range'),
                    TypeError('unsupported operand'), KeyError('floor'), AttributeError('model')):
            self.assertFalse(own(exc), repr(exc))

    def setUp(self):
        self.evaluator = evaluation.MuJoCoTendonEvaluator(**arguments())
        self.addCleanup(self.evaluator.close)
        self.params = dict(self.evaluator._params)

    def test_a_body_the_engine_refuses_scores_nothing_as_before(self):
        empty = np.zeros((10, 10, 10), np.int8)
        self.assertEqual(self.evaluator.evaluate_single(empty), 0.0)
        self.assertEqual(evaluation._eval_worker((empty, None, None, self.params)), 0.0)
        self.assertEqual(evaluation._eval_worker((empty, None, None, dict(self.params, return_descriptors=True))),
                         (0.0, (0.0, 0.0)))
        fits = self.evaluator.evaluate_batch([empty, walker()])              # and the batch goes on
        self.assertEqual(fits[0], 0.0)
        self.assertGreater(fits[1], 0.01)

    def test_a_failure_of_the_machine_stops_the_batch(self):
        """One process (--workers 1): the evaluator's own engine fails."""
        with mock.patch.object(self.evaluator.engine, 'get_fitness', side_effect=MemoryError(A_FAILED_ALLOCATION)):
            with self.assertRaises(evaluation.EvaluationStopped) as stop:
                self.evaluator.evaluate_batch([walker(), walker(1)])
        text = str(stop.exception)
        self.assertIn('robot 0', text)
        self.assertIn('not a result of the robot', text)
        self.assertIn('MemoryError: ' + A_FAILED_ALLOCATION, text)

    def test_and_so_does_one_in_a_worker(self):
        """What a worker process of a pool runs."""
        for fault in (MemoryError(A_FAILED_ALLOCATION), mujoco.FatalError('mj_stackAlloc: out of memory'),
                      OSError(22, 'The paging file is too small for this operation to complete')):
            with mock.patch.object(evaluation, '_make_engine', side_effect=fault):
                with self.assertRaises(evaluation.EvaluationStopped) as stop:
                    evaluation._eval_worker((walker(), None, None, self.params))
            self.assertIn(type(fault).__name__, str(stop.exception))

    def test_it_reaches_the_run_from_a_real_worker_process(self):
        """A pool of two processes. A body of the wrong shape stands in for the fault: the engine
        fails on it with an error that is not a body's own (an IndexError)."""
        with self.assertRaises(IndexError):
            engine().load_robot(np.ones((3, 3), np.int8), voxel_size=0.01)
        pool = evaluation.MuJoCoTendonEvaluator(n_workers=2, **arguments())
        try:
            both = pool.evaluate_batch([walker(), walker(1)])
            self.assertEqual(float(both[0]), self.evaluator.evaluate_single(walker()))       # a worker scores as one process does
            with self.assertRaises(evaluation.EvaluationStopped) as stop:
                pool.evaluate_batch([walker(), np.ones((3, 3), np.int8)])
            self.assertIn('IndexError', str(stop.exception))
        finally:
            pool.close()

    def test_the_scoring_script_follows_the_same_rule(self):
        params = ts.worker_parameters(ts.evaluator_arguments())
        empty = ts.score_one(('e', np.zeros((10, 10, 10), np.int8), params, 1.0))
        self.assertEqual((empty['score'], empty['error']), (0.0, 'ValueError: No voxels in grid!'))
        for fault, said in ((MemoryError(A_FAILED_ALLOCATION), 'out of memory'),
                            (mujoco.FatalError('mj_stackAlloc: out of memory'), 'out of memory'),
                            (IndexError('tuple index out of range'), 'not a result of the robot')):
            with mock.patch.object(evaluation, '_make_engine', side_effect=fault):
                with self.assertRaises(RuntimeError) as stop:
                    ts.score_one(('k', walker(), params, 1.0))
            self.assertIn(said, str(stop.exception))


# A run of the search's own command line in which the engine fails once, as a machine without
# memory makes it fail. Started as `python -c`, so that the fault is put in without any hook in
# the code that computes a run.
DRIVER = r'''
import runpy
import sys
fail_at, script = int(sys.argv[1]), sys.argv[2]
sys.argv = [script] + sys.argv[3:]
import src.physics.mujoco_beam_physics as beam
real, calls = beam.MuJoCoBeamPhysics.get_fitness, [0]
def get_fitness(self, *a, **k):
    calls[0] += 1
    if calls[0] == fail_at:
        raise MemoryError('Unable to allocate 4.91 MiB for an array with shape (463, 463, 3) and data type float64')
    return real(self, *a, **k)
beam.MuJoCoBeamPhysics.get_fitness = get_fitness
runpy.run_path(script, run_name='__main__')
'''


class TestAStoppedRunContinuesAsItWouldHaveGone(unittest.TestCase):
    """A run under the preset of arm D, small enough to take seconds: population 4, 3 generations,
    a workspace of 5 voxels. Its evaluations are number 1 (the check before the run), 2 to 5 (the
    first population), 6 to 9 and 10 to 13."""
    COMMAND = ['--preset', 'cheney2013-floor', '--no-age-pareto', '--gen', '3', '--pop', '4', '--workers', '1',
               '--grid-size', '5', '--seed', '3']

    def run_cli(self, folder, name, fail_at=None):
        script = os.path.join(ROOT, 'run_tendon_evolution.py')
        command = ([sys.executable, script] if fail_at is None
                   else [sys.executable, '-c', DRIVER, str(fail_at), script])
        environment = search_arm.run_environment(dict(os.environ, PYTHONPATH=ROOT))
        return subprocess.run(command + self.COMMAND + ['--name', name], cwd=folder, env=environment,
                              capture_output=True, text=True, timeout=1800)

    @staticmethod
    def recorded(folder, name):
        out = []
        for g in (1, 2, 3):
            path = os.path.join(folder, 'results', name, f'gen_{g:03d}.json')
            if os.path.exists(path):
                with open(path) as f:
                    out.append(json.load(f)['fitnesses'])
        return out

    @staticmethod
    def population(folder, name):
        with open(os.path.join(folder, 'results', name, 'final_population.pkl'), 'rb') as f:
            p = pickle.load(f)
        return [np.asarray(g).tolist() for g in p['genomes']], [float(v) for v in p['fitnesses']]

    def test_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = self.run_cli(tmp, 'plain')
            self.assertEqual(plain.returncode, 0, plain.stdout[-2000:] + plain.stderr[-2000:])
            uninterrupted = self.recorded(tmp, 'plain')
            self.assertEqual(len(uninterrupted), 3)
            self.assertGreater(len({tuple(f) for f in uninterrupted}), 1, 'the search should move')

            # the engine fails in the second evaluation of the second population
            cut = self.run_cli(tmp, 'cut', fail_at=7)
            self.assertNotEqual(cut.returncode, 0)
            self.assertIn('EvaluationStopped', cut.stderr)
            self.assertIn('not a result of the robot', cut.stderr)
            self.assertIn('MemoryError: Unable to allocate 4.91 MiB', cut.stderr)
            self.assertNotIn('EVOLUTION COMPLETE', cut.stdout)
            self.assertEqual(self.recorded(tmp, 'cut'), uninterrupted[:1])       # nothing of the unfinished generation
            self.assertTrue(os.path.exists(os.path.join(tmp, 'results', 'cut', 'checkpoint.pkl')))

            # the same command again continues it, and it ends as the uninterrupted run did
            again = self.run_cli(tmp, 'cut')
            self.assertEqual(again.returncode, 0, again.stdout[-2000:] + again.stderr[-2000:])
            self.assertIn('Resumed at generation', again.stdout)
            self.assertEqual(self.recorded(tmp, 'cut'), uninterrupted)
            self.assertEqual(self.population(tmp, 'cut'), self.population(tmp, 'plain'))

            # the fault in the very first population, before anything is recorded: the run starts again
            early = self.run_cli(tmp, 'early', fail_at=3)
            self.assertNotEqual(early.returncode, 0)
            self.assertEqual(self.recorded(tmp, 'early'), [])
            again = self.run_cli(tmp, 'early')
            self.assertEqual(again.returncode, 0, again.stdout[-2000:] + again.stderr[-2000:])
            self.assertEqual(self.recorded(tmp, 'early'), uninterrupted)

            # every start of a run is in its manifest, with the threads it was started with
            with open(os.path.join(tmp, 'results', 'cut', 'manifest.json')) as f:
                starts = json.load(f)['invocations']
            self.assertEqual(len(starts), 2)
            self.assertEqual([s['threads'] for s in starts], [search_arm.ONE_THREAD] * 2)


class TestOneThread(unittest.TestCase):
    def test_the_launcher_gives_every_run_one_thread(self):
        import run_tendon_evolution as runner
        given = search_arm.run_environment({'PATH': 'x', 'OPENBLAS_NUM_THREADS': '32'})
        self.assertEqual({k: given[k] for k in search_arm.ONE_THREAD}, {k: '1' for k in runner._THREAD_SETTINGS})
        self.assertEqual((given['PATH'], given['PYTHONUNBUFFERED']), ('x', '1'))
        self.assertEqual(sorted(search_arm.ONE_THREAD), sorted(runner._THREAD_SETTINGS))

    def test_the_scoring_script_sets_it_for_itself_and_its_workers(self):
        self.assertEqual({k: os.environ.get(k) for k in search_arm.ONE_THREAD}, search_arm.ONE_THREAD)

    @unittest.skipUnless(sys.platform.startswith('win'), 'asks Windows what a process has been promised')
    def test_what_a_worker_now_asks_the_system_for(self):
        """A process as the launcher starts it, with the libraries and the engine loaded and a
        full workspace of 1000 voxels built: 0.1 GB. Without the two settings it asked for
        3.2 GB (paper/diagnostics_2026-11-25/memory_check.json)."""
        code = ("import sys; sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])\n"
                "import numpy as np, scipy.linalg, scipy.sparse, mujoco\n"
                "import check_memory\n"
                "from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics\n"
                "e = MuJoCoBeamPhysics(materials='cheney2013', floor_contact='voxelyze', poisson=False)\n"
                "e.load_robot(np.ones((10, 10, 10), np.int8), voxel_size=0.01)\n"
                "print(check_memory.asked_for_gb())\n")
        r = subprocess.run([sys.executable, '-c', code, ROOT, os.path.join(ROOT, 'paper', 'diagnostics_2026-11-25')],
                           env=search_arm.run_environment(), capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertLess(float(r.stdout.split()[-1]), 0.25)
        self.assertGreaterEqual(ts.GB_PER_WORKER, 0.5)        # what the scoring script allows for a worker


if __name__ == '__main__':
    unittest.main()
