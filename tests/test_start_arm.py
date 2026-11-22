"""The launcher of the re-execution arms (paper/reference_2013/start_arm.py): the parts that can
be checked without starting anything. What it does with real runs is checked by trial runs."""
import importlib.util
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATH = os.path.join(ROOT, 'paper', 'reference_2013', 'start_arm.py')
spec = importlib.util.spec_from_file_location('start_arm', PATH)
start_arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start_arm)


def read(name):
    with open(os.path.join(ROOT, 'paper', 'reference_2013', name), encoding='utf-8') as f:
        return f.read()


class TestSeeds(unittest.TestCase):
    def test_the_protocol_range_is_35_seeds(self):
        seeds = start_arm.parse_seeds(start_arm.PROTOCOL_SEEDS)
        self.assertEqual(seeds, list(range(1, 36)))

    def test_lists_and_ranges(self):
        self.assertEqual(start_arm.parse_seeds('1-3, 7,10-11'), [1, 2, 3, 7, 10, 11])

    def test_refuses_nonsense(self):
        for bad in ('', 'a', '3-1', '1-2,2', '1;2', '-3'):
            with self.assertRaises(ValueError, msg=bad):
                start_arm.parse_seeds(bad)


class TestScripts(unittest.TestCase):
    def test_settings_come_first_and_no_carriage_returns(self):
        text = start_arm.shell_script('run_2013_search.sh', SEEDS='1 2', TAG='armR', PENALTY=0, GENS=None)
        self.assertTrue(text.startswith("export SEEDS='1 2'\nexport TAG='armR'\nexport PENALTY='0'\n#!"))
        self.assertNotIn('GENS=', text.split('#!')[0])
        self.assertNotIn('\r', text)

    def test_refuses_values_that_could_break_the_shell(self):
        for bad in ("1'; rm -rf x", '$HOME', 'a;b', '`x`'):
            with self.assertRaises(ValueError, msg=bad):
                start_arm.shell_script('run_2013_search.sh', TAG=bad)

    def test_the_run_script_keeps_its_safety_rules(self):
        text = read('run_2013_search.sh')
        self.assertIn('flock -n 9', text)                       # one launch per arm at a time
        self.assertIn('already finished, skipping', text)       # finished runs are never redone
        self.assertIn('is running (pid', text)                  # runs in progress are never touched
        self.assertIn('RESTART_INCOMPLETE', text)               # unfinished ones only on request
        self.assertNotIn('rm -rf', text)

    def test_the_builds_do_not_wipe_the_run_folders(self):
        sim = read('build_2013_simulator.sh')
        self.assertNotIn('rm -rf "$REF"\n', sim)
        self.assertIn('rm -rf softbots/Voxel_Sim_NoGui', sim)
        for name in ('build_2013_simulator.sh', 'build_2013_search.sh'):
            self.assertIn('pgrep -x Hypercube_NEAT', read(name), name)


class TestStatus(unittest.TestCase):
    OUTPUT = ("armR_P0_s1: 1000 generations, finished\n"
              "armR_P0_s2: 412 generations, running\n"
              "armR_P0_s3: 77 generations, interrupted\n"
              "armR_P0_s4: 12 generations, FAILED (exit 139)\n"
              "armR_P0_s5: 990 generations, finished\n"
              "armR_P0_s40: 3 generations, running\n"
              "armRc_P2_s2: 5 generations, running\n"
              "5 runs collected into /mnt/c/SoftRobotEvolution/results/rerun2013\n")

    def setUp(self):
        self.st = start_arm.parse_status(self.OUTPUT, 'armR_P0_s', [1, 2, 3, 4, 5, 6])

    def test_reads_every_state_and_only_the_seeds_asked_for(self):
        self.assertEqual(self.st, {1: (1000, 'finished'), 2: (412, 'running'), 3: (77, 'interrupted'),
                                   4: (12, 'FAILED (exit 139)'), 5: (990, 'finished'), 6: (0, 'not started')})

    def test_complete_means_finished_with_all_generations(self):
        self.assertEqual(start_arm.complete_seeds(self.st, 1000), [1])

    def test_progress_line_names_what_needs_attention(self):
        line = start_arm.progress_line(self.st, 1000, started={2: 0}, now=41200)
        self.assertIn('6 runs: 1 running, 2 finished, 1 interrupted, 1 FAILED, 1 not started.', line)
        self.assertIn('slowest 412, median 412, fastest 412', line)
        self.assertIn('about 16.3 h more', line)                # 588 generations at 100 s each
        self.assertIn('WRONG NUMBER OF GENERATIONS: seeds [5]', line)
        self.assertIn('interrupted: seeds [3]', line)
        self.assertIn('FAILED: seeds [4]', line)
        for word in ('score', 'fitness'):                       # progress only, never results
            self.assertNotIn(word, line.lower())

    def test_progress_line_with_nothing_running(self):
        st = {1: (1000, 'finished'), 2: (1000, 'finished')}
        self.assertEqual(start_arm.progress_line(st, 1000), '2 runs: 2 finished.')


class TestRules(unittest.TestCase):
    def test_protocol_frozen_is_read_from_its_status_line(self):
        self.assertFalse(start_arm.protocol_is_frozen('# Title\n\n**Status: draft for approval, not yet frozen.** x\n'))
        self.assertTrue(start_arm.protocol_is_frozen('# Title\n\n**Frozen on 21 November 2026.** x\n'))
        self.assertFalse(start_arm.protocol_is_frozen('# Title\n\nno status line\n'))

    def test_generations_are_read_from_the_settings_file(self):
        self.assertEqual(start_arm.settings_generations('PopulationSize 30.0\nMaxGenerations 1000.0\n'), 1000)
        self.assertIsNone(start_arm.settings_generations('PopulationSize 30.0\n'))

    def test_a_trial_needs_its_own_tag(self):
        for argv in (['--arm', 'R', '--seeds', '1-2'], ['--arm', 'R', '--gens', '2'],
                     ['--arm', 'R', '--tag', 'armR', '--gens', '2'], ['--arm', 'R', '--tag', 'armRc'],
                     ['--arm', 'R', '--tag', 'a b'], ['--arm', 'X']):
            with self.assertRaises(SystemExit, msg=argv), open(os.devnull, 'w') as null:
                import contextlib
                with contextlib.redirect_stderr(null):
                    start_arm.main(argv)

    def test_the_arms_are_those_of_the_protocol(self):
        self.assertEqual(start_arm.ARMS['R'], {'tag': 'armR', 'penalty': 0, 'condition': 'noCost'})
        self.assertEqual(start_arm.ARMS['Rc'], {'tag': 'armRc', 'penalty': 2, 'condition': 'costNumActuated'})

    def test_window_file_runs_this_launcher_here(self):
        text = start_arm.window_command_text('R', ['--arm', 'R', '--here'], python=r'C:\Py 100%\python.exe',
                                             script=r'C:\x\start_arm.py')
        lines = text.splitlines()
        self.assertEqual(lines[0], '@echo off')
        self.assertIn('keep this window open', lines[1])
        self.assertEqual(lines[3], r'"C:\Py 100%%\python.exe" C:\x\start_arm.py --arm R --here')
        self.assertEqual(lines[-1], 'pause > nul')


if __name__ == '__main__':
    unittest.main()
