"""The launcher of the arms run with this project's own search (paper/reference_2013/search_arm.py,
used through start_arm.py): the parts that can be checked without starting a run."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HERE = os.path.join(ROOT, 'paper', 'reference_2013')
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location('start_arm', os.path.join(HERE, 'start_arm.py'))
start_arm = importlib.util.module_from_spec(spec)
sys.modules['start_arm'] = start_arm        # start_arm hands itself to search_arm by this name
spec.loader.exec_module(start_arm)
import search_arm           # noqa: E402


def make_run(results, name, generations, final=True, checkpoint=False):
    d = os.path.join(results, name)
    os.makedirs(d)
    with open(os.path.join(d, 'manifest.json'), 'w') as f:
        f.write('{}')
    for g in range(1, generations + 1):
        with open(os.path.join(d, f'gen_{g:03d}.json'), 'w') as f:
            json.dump({'generation': g, 'best_fitness': 1.0}, f)
    for name_, wanted in (('final_population.pkl', final), ('best_robot.pkl', final), ('checkpoint.pkl', checkpoint)):
        if wanted:
            with open(os.path.join(d, name_), 'wb') as f:
                f.write(b'x')
    return d


class TestArmA(unittest.TestCase):
    def test_arm_a_is_the_one_of_the_protocol(self):
        arm = search_arm.ARMS['A']
        self.assertEqual(arm['runner'], ['--simulator', 'voxelyze2013', '--no-age-pareto', '--pop', '30'])
        self.assertEqual((arm['generations'], arm['condition'], arm['tag']), (1000, 'noCost', 'armA'))
        self.assertEqual(start_arm.parse_seeds(start_arm.PROTOCOL_SEEDS), list(range(1, 36)))

    def test_the_command_of_a_run(self):
        cmd = search_arm.runner_command(search_arm.ARMS['A'], 'python.exe', 'armA', 7, 1000, 1)
        self.assertEqual(cmd[0], 'python.exe')
        self.assertTrue(cmd[1].endswith('run_tendon_evolution.py'))
        self.assertEqual(cmd[2:], ['--simulator', 'voxelyze2013', '--no-age-pareto', '--pop', '30', '--gen', '1000',
                                   '--workers', '1', '--seed', '7', '--name', 'armA_s7'])
        for forbidden in ('--no-resume', '--force', '--preset', '--penalty'):     # a continued run is the same command
            self.assertNotIn(forbidden, cmd)

    def test_the_code_that_computes_a_run_is_checked_against_the_tag(self):
        self.assertEqual(search_arm.CODE_TAG, 'campaign-v2')      # v1 plus the exact continuation (PROTOCOL 9.3)
        self.assertEqual(search_arm.RUN_DEFINING, ['run_tendon_evolution.py', 'src'])

    def test_the_check_against_the_tag(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            def git(*a):
                subprocess.run(['git', '-C', d, '-c', 'user.name=t', '-c', 'user.email=t@example.invalid'] + list(a),
                               check=True, capture_output=True)
            os.makedirs(os.path.join(d, 'src'))
            for name, text in (('run_tendon_evolution.py', 'a = 1\n'), (os.path.join('src', 'x.py'), 'b = 2\n'),
                               ('README.md', 'notes\n')):
                with open(os.path.join(d, name), 'w') as f:
                    f.write(text)
            git('init', '-q')
            git('add', '-A')
            git('commit', '-q', '-m', 'one')
            self.assertIn('does not exist', search_arm.code_differs_from_tag(tag='campaign-v9', root=d))
            git('tag', 'campaign-v9')
            self.assertIsNone(search_arm.code_differs_from_tag(tag='campaign-v9', root=d))
            with open(os.path.join(d, 'README.md'), 'a') as f:            # documentation may move on
                f.write('more\n')
            git('commit', '-q', '-am', 'docs')
            self.assertIsNone(search_arm.code_differs_from_tag(tag='campaign-v9', root=d))
            with open(os.path.join(d, 'src', 'x.py'), 'a') as f:          # the code of a run may not, even uncommitted
                f.write('b = 3\n')
            self.assertIn('differ from the code tagged campaign-v9', search_arm.code_differs_from_tag(tag='campaign-v9', root=d))


class TestRunState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = self.tmp.name

    def test_states_from_the_files_alone(self):
        make_run(self.r, 'armA_s1', 1000)
        make_run(self.r, 'armA_s2', 412, final=False, checkpoint=True)
        make_run(self.r, 'armA_s3', 0, final=False)                       # begun, no generation recorded yet
        make_run(self.r, 'armA_s4', 999)                                  # final files but a generation short
        make_run(self.r, 'armA_s5', 1000, checkpoint=True)                # final files AND a checkpoint: not trusted
        state = lambda s: search_arm.run_state(os.path.join(self.r, f'armA_s{s}'), 1000)   # noqa: E731
        self.assertEqual(state(1), (1000, 'finished'))
        self.assertEqual(state(2), (412, 'interrupted'))
        self.assertEqual(state(3), (0, 'interrupted'))
        self.assertEqual(state(4), (999, 'interrupted'))
        self.assertEqual(state(5), (1000, 'interrupted'))
        self.assertEqual(state(6), (0, 'not started'))

    def test_a_gap_in_the_generations_is_not_counted_past(self):
        d = make_run(self.r, 'armA_s1', 10, final=False)
        os.remove(os.path.join(d, 'gen_004.json'))
        self.assertEqual(search_arm.run_state(d, 1000), (3, 'interrupted'))

    def test_statuses_in_the_words_of_the_progress_line(self):
        make_run(self.r, 'armA_s1', 1000)
        make_run(self.r, 'armA_s2', 412, final=False, checkpoint=True)
        make_run(self.r, 'armA_s3', 77, final=False, checkpoint=True)
        make_run(self.r, 'armA_s4', 5, final=False, checkpoint=True)
        st = search_arm.statuses('armA', [1, 2, 3, 4, 5], 1000, running={2, 1}, failed={'4': 'ended 6 times'},
                                 results=self.r)
        self.assertEqual(st, {1: (1000, 'finished'), 2: (412, 'running'), 3: (77, 'interrupted'),
                              4: (5, 'FAILED (ended 6 times)'), 5: (0, 'not started')})
        line = start_arm.progress_line(st, 1000)
        self.assertIn('5 runs: 1 running, 1 finished, 1 interrupted, 1 FAILED, 1 not started.', line)
        self.assertEqual(start_arm.complete_seeds(st, 1000), [1])


class TestWaitingForAnotherArm(unittest.TestCase):
    """--after: arm A waits for a re-run arm to finish and starts only if that arm is complete."""

    def test_waits_while_held_and_reminds(self):
        clock = [0.0]
        held = [True] * 500 + [False]
        said = []
        outcome = search_arm.wait_until_free(lambda: held.pop(0), lambda: False, said.append, 'arm Rc', poll=10,
                                             remind=1800, sleep=lambda s: clock.__setitem__(0, clock[0] + s),
                                             clock=lambda: clock[0])
        self.assertEqual(outcome, 'free')
        self.assertEqual(clock[0], 5000.0)                       # 500 polls of 10 seconds
        self.assertEqual(said, ['(still waiting for arm Rc)'] * 2)   # after 30 and 60 minutes

    def test_a_stop_request_ends_the_wait(self):
        asked = iter([False, False, True])
        outcome = search_arm.wait_until_free(lambda: True, lambda: next(asked), lambda s: None, 'arm Rc', poll=0,
                                             sleep=lambda s: None)
        self.assertEqual(outcome, 'stopped')

    def fake_core(self, tmp, statuses_in_turn, said):
        """start_arm with its reading of the other arm replaced by a script of answers."""
        import types
        settings = os.path.join(tmp, 'settings.dat')
        with open(settings, 'w') as f:
            f.write('MaxGenerations 1000.0\n')
        calls = []

        def read_status(prefix, seeds):
            calls.append(prefix)
            return {s: statuses_in_turn[min(len(calls), len(statuses_in_turn)) - 1] for s in seeds}
        core = types.SimpleNamespace(
            ARMS=start_arm.ARMS, RERUN_OUT=tmp, PROTOCOL_SEEDS='1-3', SETTINGS=settings, say=said.append,
            parse_seeds=start_arm.parse_seeds, settings_generations=start_arm.settings_generations,
            lock_held=start_arm.lock_held, running_seeds=start_arm.running_seeds,
            complete_seeds=start_arm.complete_seeds, progress_line=start_arm.progress_line, read_status=read_status)
        return core, calls

    @unittest.skipUnless(os.name == 'nt', 'the lock is a Windows file lock')
    def test_the_other_arm_is_read_only_after_its_launcher_has_ended(self):
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            said = []
            core, calls = self.fake_core(tmp, [(1000, 'finished')], said)
            lock = start_arm.take_lock(os.path.join(tmp, 'armRc_P2_host.lock'))      # arm Rc's launcher is alive
            seen_while_held = []
            threading.Timer(0.6, lambda: (seen_while_held.append(len(calls)), lock.close())).start()
            outcome = search_arm.wait_for_other_arm(core, 'Rc', lambda: False, poll=0.05)
            self.assertEqual(outcome, 'complete')
            self.assertEqual(seen_while_held, [0])               # nothing was read while it ran
            self.assertEqual(calls, ['armRc_P2_s'])
            self.assertIn('Arm Rc is running. Waiting for it to finish', said[0])
            self.assertIn('Arm Rc is complete: 3 of 3 runs', said[-1])

    def test_an_arm_that_ended_unfinished_does_not_start_the_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            said = []
            core, calls = self.fake_core(tmp, [(412, 'interrupted')], said)
            self.assertEqual(search_arm.wait_for_other_arm(core, 'Rc', lambda: False, poll=0.01), 'incomplete')
            self.assertIn('ended without being complete', said[-1])
            core, calls = self.fake_core(tmp, [(999, 'finished')], said)             # finished, but a generation short
            self.assertEqual(search_arm.wait_for_other_arm(core, 'R', lambda: False, poll=0.01), 'incomplete')
            self.assertEqual(calls, ['armR_P0_s'])

    def test_a_stop_while_waiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            said = []
            core, calls = self.fake_core(tmp, [(1000, 'finished')], said)
            lock = start_arm.take_lock(os.path.join(tmp, 'armRc_P2_host.lock'))
            try:
                asked = iter([False, False, True])
                outcome = search_arm.wait_for_other_arm(core, 'Rc', lambda: next(asked), poll=0.01)
            finally:
                lock.close()
            self.assertEqual(outcome, 'stopped')
            self.assertEqual(calls, [])


class TestThroughStartArm(unittest.TestCase):
    def fails(self, argv):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            start_arm.main(argv)

    def test_arm_a_is_started_with_the_same_program(self):
        self.fails(['--arm', 'A', '--restart-incomplete'])       # its runs are continued, never started over
        self.fails(['--arm', 'A', '--tag', 'armA', '--gens', '3'])   # a trial cannot take the arm's name
        self.fails(['--arm', 'A', '--seeds', '1-2'])             # nor change the arm without a tag
        self.fails(['--arm', 'A', '--workers', '0'])
        self.fails(['--arm', 'R', '--workers', '2', '--status'])  # --workers means nothing for the re-runs
        self.fails(['--arm', 'R', '--after', 'Rc', '--status'])   # only arm A waits for another arm
        self.fails(['--arm', 'A', '--after', 'A'])                # and only for a re-run arm

    @unittest.skipUnless(os.name == 'nt', 'Windows job objects')
    def test_the_job_object_can_be_created(self):
        # In a child process: the job would otherwise take this test process into it.
        import subprocess
        code = ("import sys; sys.path.insert(0, r'%s'); import search_arm; "
                "h = search_arm.own_children(); print('job' if h else 'none')" % HERE)
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout.strip(), 'job', out.stderr)


if __name__ == '__main__':
    unittest.main()
