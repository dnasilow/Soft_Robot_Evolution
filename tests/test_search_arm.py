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


class TestArmD(unittest.TestCase):
    """Arm D: this project's search in its MuJoCo engine (PROTOCOL.md, sections 2, 9.5 and 9.6)."""

    def test_arm_d_is_the_one_of_the_protocol(self):
        arm = search_arm.ARMS['D']
        self.assertEqual(arm['runner'], ['--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '30'])
        self.assertEqual((arm['generations'], arm['condition'], arm['tag'], arm['seeds']), (300, 'noCost', 'armD', '1-10'))
        self.assertEqual(start_arm.parse_seeds(arm['seeds']), list(range(1, 11)))
        self.assertEqual(arm['code'], 'campaign-v4')              # v3 (the 2013 floor and start) plus section 9.6
        self.assertFalse(search_arm.in_the_2013_simulator(arm))
        a = search_arm.ARMS['A']                                  # and arm A is what it was
        self.assertEqual((a['code'], a['seeds'], a['workers']), ('campaign-v2', start_arm.PROTOCOL_SEEDS, 1))
        self.assertTrue(search_arm.in_the_2013_simulator(a))

    def test_the_command_of_a_run(self):
        cmd = search_arm.runner_command(search_arm.ARMS['D'], 'python.exe', 'armD', 4, 300, 3)
        self.assertEqual(cmd[2:], ['--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '30', '--gen', '300',
                                   '--workers', '3', '--seed', '4', '--name', 'armD_s4'])

    def test_each_arm_has_its_own_seeds(self):
        from unittest import mock
        with mock.patch.object(search_arm, 'main', side_effect=lambda core, a, ap, seeds: seeds):
            self.assertEqual(start_arm.main(['--arm', 'D', '--status']), list(range(1, 11)))
            self.assertEqual(start_arm.main(['--arm', 'A', '--status']), list(range(1, 36)))
            self.assertEqual(start_arm.main(['--arm', 'D', '--tag', 'trialD', '--seeds', '101-102', '--gens', '3']),
                             [101, 102])

    def test_runs_start_only_with_room_in_memory(self):
        from unittest import mock
        per, keep = search_arm.GB_PER_PROCESS, search_arm.KEEP_FREE_GB
        self.assertEqual((search_arm.processes_of_a_run(1), search_arm.processes_of_a_run(3)), (1, 4))
        fits, free, wanted = search_arm.room_for(10, 3, free=keep + 40 * per)
        self.assertTrue(fits)
        self.assertEqual(wanted, keep + 40 * per)
        self.assertFalse(search_arm.room_for(10, 3, free=keep + 40 * per - 0.1)[0])
        self.assertTrue(search_arm.room_for(1, 3, free=keep + 4 * per)[0])
        with mock.patch.object(search_arm, 'free_commit_gb', return_value=None):      # a system that cannot be asked
            self.assertTrue(search_arm.room_for(10, 3)[0])
        if os.name == 'nt':
            self.assertGreater(search_arm.free_commit_gb(), 0)

    def test_what_stopped_a_run(self):
        tail = ('Traceback (most recent call last): / raise _stopped(exc) from exc / '
                'src.evolution.mujoco_tendon_evaluator.EvaluationStopped: An evaluation ended in an error that is not a '
                'result of the robot, so it was not scored: MemoryError: Unable to allocate 4.91 MiB for an array')
        why = search_arm.stopped_by(tail)
        self.assertIn("not the robot's", why)
        self.assertIn('(MemoryError: Unable to allocate 4.91 MiB for an array)', why)
        self.assertEqual(search_arm.stopped_by('Gen  12/300  best=1.2000W / Gen  13/300  best=1.3000W'), '')

    def test_the_log_never_shows_a_score(self):
        """When a run ends early the launcher quotes the end of its output. That output has scores
        in it, and an arm's results are read only once the arm is complete."""
        shown = search_arm.without_scores(
            'Evaluating initial population... / Gen   1/300  best=1.3112W  mean=0.3937W  worst=0.0000W  [478.5s]  '
            'species=1  cppn=N10/E24 / Resumed at generation 57/300  |  best so far 2.4199m / Sanity check passed — '
            'fitness=0.3605W  voxels=457 / EVOLUTION COMPLETE — best fitness: 2.7170W / MemoryError: Unable to allocate '
            '4.91 MiB for an array with shape (463, 463, 3)')
        for score in ('1.3112', '0.3937', '0.0000', '2.4199', '0.3605', '2.7170'):
            self.assertNotIn(score, shown)
        for kept in ('Gen   1/300', '[478.5s]', 'cppn=N10/E24', 'generation 57/300', 'voxels=457',
                     'Unable to allocate 4.91 MiB for an array with shape (463, 463, 3)'):
            self.assertIn(kept, shown)
        self.assertEqual(shown.count('(not shown)'), 6)

    def test_a_run_without_progress_is_noticed(self):
        progress = {}
        self.assertEqual(search_arm.without_progress(progress, {1: 5, 2: 7}, now=0.0, limit=100), {})
        self.assertEqual(search_arm.without_progress(progress, {1: 5, 2: 8}, now=90.0, limit=100), {})
        self.assertEqual(search_arm.without_progress(progress, {1: 5, 2: 8}, now=150.0, limit=100), {1: 150.0})
        self.assertEqual(search_arm.without_progress(progress, {1: 6, 2: 8}, now=200.0, limit=100), {2: 110.0})
        self.assertEqual(search_arm.without_progress(progress, {2: 8}, now=210.0, limit=100), {2: 120.0})
        self.assertNotIn(1, progress)                             # a run that has ended is forgotten


class TestArmsE(unittest.TestCase):
    """Arms E1 to E3: arm D with one setting undone each (PROTOCOL.md, section 9.8). Added on 27
    November 2026, while arm D was running and before any of the three was started."""

    RUNNERS = {
        'E1': ['--preset', 'cheney2013-floor', '--damping-global', '0.01', '--no-age-pareto', '--pop', '30'],
        'E2': ['--preset', 'cheney2013-floor', '--amp', '0.2', '--poisson', 'on', '--no-age-pareto', '--pop', '30'],
        'E3': ['--preset', 'cheney2013', '--no-age-pareto', '--pop', '30'],
    }

    def test_they_are_those_of_the_protocol(self):
        d = search_arm.ARMS['D']
        for name, runner in self.RUNNERS.items():
            arm = search_arm.ARMS[name]
            self.assertEqual(arm['runner'], runner)
            self.assertEqual((arm['generations'], arm['condition'], arm['tag'], arm['seeds'], arm['code']),
                             (300, 'noCost', 'arm' + name, '1-3', 'campaign-v4'))
            self.assertFalse(search_arm.in_the_2013_simulator(arm))
            self.assertEqual(runner[-3:], d['runner'][-3:])               # the search itself is arm D's
        # and arm D, which is running, is what it was
        self.assertEqual(d, {'tag': 'armD', 'generations': 300, 'condition': 'noCost', 'seeds': '1-10',
                             'code': 'campaign-v4', 'workers': 3,
                             'runner': ['--preset', 'cheney2013-floor', '--no-age-pareto', '--pop', '30']})

    def test_the_command_of_a_run(self):
        cmd = search_arm.runner_command(search_arm.ARMS['E2'], 'python.exe', 'armE2', 3, 300, 3)
        self.assertEqual(cmd[2:], ['--preset', 'cheney2013-floor', '--amp', '0.2', '--poisson', 'on', '--no-age-pareto',
                                   '--pop', '30', '--gen', '300', '--workers', '3', '--seed', '3', '--name', 'armE2_s3'])
        cmd = search_arm.runner_command(search_arm.ARMS['E3'], 'python.exe', 'armE3', 1, 300, 3)
        self.assertEqual(cmd[2:], ['--preset', 'cheney2013', '--no-age-pareto', '--pop', '30', '--gen', '300',
                                   '--workers', '3', '--seed', '1', '--name', 'armE3_s1'])

    def test_what_each_command_says_about_the_engine(self):
        options = {name: search_arm.engine_options(arm) for name, arm in search_arm.ARMS.items()}
        self.assertEqual(options, {'A': (None, {}), 'D': ('cheney2013-floor', {}),
                                   'E1': ('cheney2013-floor', {'damping_global': '0.01'}),
                                   'E2': ('cheney2013-floor', {'amp': '0.2', 'poisson': 'on'}),
                                   'E3': ('cheney2013', {})})
        with self.assertRaises(ValueError):                                # a command without a preset
            search_arm.engine_options({'runner': ['--no-age-pareto', '--pop', '30']})
        with self.assertRaises(ValueError):                                # an option whose value is not there
            search_arm.engine_options({'runner': ['--preset', 'cheney2013', '--no-trim', '--no-age-pareto', '--pop', '30']})

    def test_an_option_next_to_a_preset_undoes_an_entry_of_that_preset(self):
        sys.path.insert(0, ROOT)
        import run_tendon_evolution as runner
        differs_from_d = {}
        d = dict(runner._PRESETS['cheney2013-floor'])
        for name in self.RUNNERS:
            preset, given = search_arm.engine_options(search_arm.ARMS[name])
            entries = dict(runner._PRESETS[preset])
            for option, value in given.items():
                self.assertIn(option, entries, f'arm {name}: {option} is not a setting of {preset}')
                self.assertNotEqual(type(entries[option])(value), entries[option])
                entries[option] = type(entries[option])(value)
            differs_from_d[name] = sorted(k for k in set(d) | set(entries) if d.get(k) != entries.get(k))
        # each arm differs from arm D in the one setting the protocol names, and in no other
        self.assertEqual(differs_from_d, {'E1': ['damping_global'], 'E2': ['amp', 'poisson'],
                                          'E3': ['floor_contact', 'start']})

    def test_their_seeds_and_their_trials(self):
        from unittest import mock
        with mock.patch.object(search_arm, 'main', side_effect=lambda core, a, ap, seeds: seeds):
            for name in self.RUNNERS:
                self.assertEqual(start_arm.main(['--arm', name, '--status']), [1, 2, 3])
            self.assertEqual(start_arm.main(['--arm', 'E1', '--tag', 'trialE1', '--seeds', '101-103', '--gens', '2']),
                             [101, 102, 103])
            self.assertEqual(start_arm.main(['--arm', 'D', '--status']), list(range(1, 11)))
        for argv in (['--arm', 'E1', '--tag', 'armE1', '--gens', '2'], ['--arm', 'E2', '--tag', 'armD'],
                     ['--arm', 'E3', '--seeds', '101'], ['--arm', 'E1', '--restart-incomplete']):
            with self.assertRaises(SystemExit, msg=argv), contextlib.redirect_stderr(io.StringIO()):
                start_arm.main(argv)

    def test_robots_at_a_time_and_memory(self):
        """Arm E2's robots take about twice as long to simulate (the volumetric law shortens the
        time step), so its runs simulate five at a time and the others three. Machine time only:
        the scores do not depend on it."""
        self.assertEqual({name: search_arm.ARMS[name]['workers'] for name in self.RUNNERS}, {'E1': 3, 'E2': 5, 'E3': 3})
        cmd = search_arm.runner_command(search_arm.ARMS['E2'], 'python.exe', 'armE2', 2, 300, search_arm.ARMS['E2']['workers'])
        self.assertEqual(cmd[cmd.index('--workers') + 1], '5')
        per, keep = search_arm.GB_PER_PROCESS, search_arm.KEEP_FREE_GB
        # each arm's launcher asks for its own three runs: four processes each, six in arm E2
        self.assertEqual(search_arm.room_for(3, 3, free=64.0)[2], keep + 12 * per)
        self.assertEqual(search_arm.room_for(3, 5, free=64.0)[2], keep + 18 * per)
        self.assertTrue(search_arm.room_for(3, 5, free=keep + 18 * per)[0])


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


class TestWaitingForArmD(unittest.TestCase):
    """--after D: an arm E waits for arm D, which is run with this project's search and whose
    runs end with its launcher, and starts only if arm D is complete (PROTOCOL.md, section 9.8)."""

    def setUp(self):
        import types
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.results, self.out = os.path.join(self.tmp.name, 'results'), os.path.join(self.tmp.name, 'campaign')
        os.makedirs(self.out)
        self.said = []
        self.core = types.SimpleNamespace(say=self.said.append, parse_seeds=start_arm.parse_seeds,
                                          lock_held=start_arm.lock_held, complete_seeds=start_arm.complete_seeds,
                                          progress_line=start_arm.progress_line)

    def arm_d(self, unfinished=None):
        """Arm D's ten run folders; `unfinished`: a seed that stands at generation 120."""
        for s in range(1, 11):
            if s == unfinished:
                make_run(self.results, f'armD_s{s}', 120, final=False, checkpoint=True)
            else:
                make_run(self.results, f'armD_s{s}', 300)

    def wait(self, stop=lambda: False, poll=0.05):
        return search_arm.wait_for_search_arm(self.core, 'D', stop, poll, out=self.out, results=self.results)

    @unittest.skipUnless(os.name == 'nt', 'the lock is a Windows file lock')
    def test_it_waits_for_the_launcher_and_then_reads_the_run_folders(self):
        import shutil
        import threading
        self.arm_d(unfinished=7)
        lock = start_arm.take_lock(os.path.join(self.out, 'armD_host.lock'))          # arm D's launcher is alive

        def the_arm_finishes():
            shutil.rmtree(os.path.join(self.results, 'armD_s7'))
            make_run(self.results, 'armD_s7', 300)
            lock.close()
        threading.Timer(0.6, the_arm_finishes).start()
        self.assertEqual(self.wait(), 'complete')
        self.assertIn('Arm D is running. Waiting for it to finish', self.said[0])
        self.assertIn('Arm D is complete: 10 of 10 runs with 300 generations', self.said[-1])

    def test_an_arm_d_that_ended_unfinished_starts_nothing(self):
        self.arm_d(unfinished=7)                                                      # and no launcher looks after it
        self.assertEqual(self.wait(), 'incomplete')
        self.assertEqual(len(self.said), 1)
        self.assertIn('Arm D has ended without being complete', self.said[0])
        self.assertIn('interrupted: seeds [7]', self.said[0])

    def test_an_arm_d_that_is_complete_already_is_seen_at_once(self):
        self.arm_d()
        self.assertEqual(self.wait(), 'complete')

    @unittest.skipUnless(os.name == 'nt', 'the lock is a Windows file lock')
    def test_a_stop_while_waiting(self):
        self.arm_d(unfinished=2)
        lock = start_arm.take_lock(os.path.join(self.out, 'armD_host.lock'))
        try:
            asked = iter([False, False, True])
            self.assertEqual(self.wait(stop=lambda: next(asked), poll=0.01), 'stopped')
        finally:
            lock.close()
        self.assertEqual(len(self.said), 1)                                           # it never said how arm D ended

    def test_the_launcher_hands_a_search_arm_to_this_wait(self):
        from unittest import mock
        stop = lambda: False                                                          # noqa: E731
        with mock.patch.object(search_arm, 'wait_for_search_arm', return_value='complete') as wait:
            self.assertEqual(search_arm.wait_for_other_arm(self.core, 'D', stop, poll=1.5), 'complete')
        wait.assert_called_once_with(self.core, 'D', stop, 1.5)

    def test_through_the_command_line(self):
        from unittest import mock
        seen = []
        with mock.patch.object(search_arm, 'main', side_effect=lambda core, a, ap, seeds: seen.append((a.arm, a.after))):
            start_arm.main(['--arm', 'E1', '--after', 'D'])
            start_arm.main(['--arm', 'E3', '--after', 'D', '--interval', '5'])
        self.assertEqual(seen, [('E1', 'D'), ('E3', 'D')])
        import argparse
        a = argparse.Namespace(seeds=None, gens=None, tag=None, interval=10.0, jobs=None, workers=None, after='D',
                               restart_incomplete=False)
        self.assertEqual(start_arm.passthrough(a, True), ['--interval', '10.0', '--after', 'D'])   # the launcher gets it
        self.assertEqual(start_arm.passthrough(a, False), [])                                      # the view does not
        for argv in (['--arm', 'E1', '--after', 'E1'], ['--arm', 'D', '--after', 'D'], ['--arm', 'R', '--after', 'D']):
            with self.assertRaises(SystemExit, msg=argv), contextlib.redirect_stderr(io.StringIO()):
                start_arm.main(argv)


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
        self.fails(['--arm', 'R', '--after', 'Rc', '--status'])   # a re-run arm waits for no other arm
        self.fails(['--arm', 'A', '--after', 'A'])                # and no arm waits for itself

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
