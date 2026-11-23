"""A run that is stopped and continued from its checkpoint must compute exactly what it would have
computed without the stop.

Until 23 November 2026 it did not. The loop's random generator and the genomes' generator are one
object while a run is alive; the checkpoint stored the genomes (with their generator) and the
loop's generator state separately, so a continued run went on with two independent copies and
drew different numbers. The checkpoint now stores the generator itself next to the genomes.

The evolution loop is run here with a stand-in for the simulator (a fixed function of the body),
so the test is about the search alone and takes seconds.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest

import numpy as np

import run_tendon_evolution as R


class StandInSimulator:
    """Takes the place of MuJoCoTendonEvaluator: a score that depends only on the body."""
    stop_at_batch = None            # raise in that evaluate_batch call of the next run (1 = first population)

    def __init__(self, **settings):
        self.batches = 0

    @staticmethod
    def score(genome):
        g = np.asarray(genome)
        return ((int((g != 0).sum()) * 7919) % 1000) / 1000.0 + float((g == 1).sum()) / 100000.0

    def evaluate_single(self, genome, controller=None):
        return self.score(genome)

    def evaluate_batch(self, genomes, controllers=None, with_descriptors=False, gait_params=None):
        self.batches += 1
        if StandInSimulator.stop_at_batch == self.batches:
            raise RuntimeError('stopped on purpose')
        return np.array([self.score(g) for g in genomes], dtype=float)

    def close(self):
        pass


class TestContinuedRunRepeatsTheUninterruptedOne(unittest.TestCase):
    GENERATIONS = 7

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.real = R.MuJoCoTendonEvaluator
        R.MuJoCoTendonEvaluator = StandInSimulator
        self.addCleanup(setattr, R, 'MuJoCoTendonEvaluator', self.real)
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)                     # the loop also writes a convenience file where it stands
        self.addCleanup(os.chdir, self.cwd)

    def run_search(self, name, stop_at_batch=None, age_pareto=False):
        StandInSimulator.stop_at_batch = stop_at_batch
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                R.run_evolution(population_size=12, generations=self.GENERATIONS, n_workers=1, seed=5,
                                use_age_pareto=age_pareto, results_dir=self.tmp.name, name=name)
        finally:
            StandInSimulator.stop_at_batch = None

    def recorded(self, name):
        out = []
        for g in range(1, self.GENERATIONS + 1):
            with open(os.path.join(self.tmp.name, name, f'gen_{g:03d}.json')) as f:
                out.append(json.load(f)['fitnesses'])
        return out

    def check(self, age_pareto):
        self.run_search('plain', age_pareto=age_pareto)
        plain = self.recorded('plain')
        self.assertGreater(len({tuple(f) for f in plain}), 3, 'the stand-in search should move')

        # Stopped while generation 2 is being evaluated, so it is continued from generation 1, where
        # the first population still shares the loop's generator: the case that went wrong with
        # tournament selection. Stopped again three generations later, and continued to the end.
        with self.assertRaises(RuntimeError):
            self.run_search('cut', stop_at_batch=2, age_pareto=age_pareto)
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, 'cut', 'checkpoint.pkl')))
        with self.assertRaises(RuntimeError):
            self.run_search('cut', stop_at_batch=3, age_pareto=age_pareto)     # third batch after the resume
        self.run_search('cut', age_pareto=age_pareto)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'cut', 'checkpoint.pkl')))
        self.assertEqual(self.recorded('cut'), plain)

        # Stopped late only (generation 5): this was already exact with tournament selection.
        with self.assertRaises(RuntimeError):
            self.run_search('late', stop_at_batch=5, age_pareto=age_pareto)
        self.run_search('late', age_pareto=age_pareto)
        self.assertEqual(self.recorded('late'), plain)

        # and the same seed twice, uninterrupted, is the same run
        self.run_search('again', age_pareto=age_pareto)
        self.assertEqual(self.recorded('again'), plain)

    def test_tournament_selection_as_in_the_campaign(self):
        self.check(age_pareto=False)

    def test_age_fitness_pareto_selection(self):
        self.check(age_pareto=True)


if __name__ == '__main__':
    unittest.main()
