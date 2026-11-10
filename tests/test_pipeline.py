"""Pipeline tests: the default (springs) model is unchanged, and --body beam is wired through the
evaluator, worker processes, resume safeguard, command line, render and scorecard.

Run from the repo root:   python -m unittest discover -s tests -t . -v
"""
import os
import pickle
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, 'results', 'cheney_repro_s1', 'archive.pkl')
SS = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}


def smallest_archive_body():
    with open(ARCHIVE, 'rb') as fh:
        arc = pickle.load(fh)['archive']
    return min(arc.values(), key=lambda e: int((e['genome'] != 0).sum()))['genome']


def run_cli(args, cwd):
    return subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py')] + args,
                          cwd=cwd, capture_output=True, text=True, timeout=120)


@unittest.skipUnless(os.path.exists(ARCHIVE), 'reference archive not present')
class TestDefaultModelUnchanged(unittest.TestCase):
    def test_springs_regression_value(self):
        """The original tendon model must reproduce the value recorded before any of the
        friction / early-termination / beam work (0.728415 BL, 25 cycles)."""
        from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
        e = MuJoCoTendonPhysics(actuation_amplitude=0.16, fitness_mode='forward')
        e.load_robot(smallest_archive_body())
        self.assertEqual(f"{e.get_fitness(simulation_time=2.5, settle_time=0.5):.6f}", "0.728415")

    def test_evaluator_default_is_springs(self):
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        ev = MuJoCoTendonEvaluator(n_workers=1)
        self.assertIs(type(ev.engine), MuJoCoTendonPhysics)
        ev = MuJoCoTendonEvaluator(n_workers=1, body='beam')
        self.assertIs(type(ev.engine), MuJoCoBeamPhysics)


@unittest.skipUnless(os.path.exists(ARCHIVE), 'reference archive not present')
class TestBeamPlumbing(unittest.TestCase):
    def test_direct_equals_sequential_equals_pool(self):
        """Settings (body, stick-slip floor, early termination) must reach worker processes."""
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        g = smallest_archive_body()
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
        e.load_robot(g)
        direct = float(e.get_fitness(simulation_time=0.4, settle_time=0.2,
                                     early_term_threshold=0.02, early_term_fraction=0.5))
        for nw in (1, 2):
            ev = MuJoCoTendonEvaluator(simulation_time=0.4, settle_time=0.2, actuation_amplitude=0.2,
                                       n_workers=nw, attach_controller=False, fitness_mode='forward',
                                       friction=SS, early_term_threshold=0.02, early_term_fraction=0.5,
                                       body='beam')
            got = [float(x) for x in ev.evaluate_batch([g, g])]
            ev.close()
            self.assertEqual(got, [direct, direct], f"n_workers={nw}")


class TestResumeSafeguard(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, ROOT)
        import run_tendon_evolution as R
        self.R = R

    def phys(self, **kw):
        base = {'friction': SS, 'early_term_threshold': 0.02, 'early_term_fraction': 0.5,
                'body': 'beam', 'sim_time': 1.0, 'settle_time': 0.5}
        base.update(kw)
        return base

    def resumes(self, ck, phys):
        try:
            self.R._check_resume_physics(ck, phys)
            return True
        except SystemExit:
            return False

    def test_body_is_checked(self):
        self.assertTrue(self.resumes({'physics': self.phys()}, self.phys()))
        self.assertFalse(self.resumes({'physics': self.phys()}, self.phys(body='springs')))
        self.assertFalse(self.resumes({'physics': self.phys(body='springs')}, self.phys()))

    def test_old_checkpoints_are_springs(self):
        """Checkpoints written before --body existed used the tendon model."""
        old = {'physics': {k: v for k, v in self.phys(body='springs').items() if k != 'body'}}
        self.assertTrue(self.resumes(old, self.phys(body='springs')))
        self.assertFalse(self.resumes(old, self.phys()))
        self.assertFalse(self.resumes({}, self.phys()))


class TestCommandLine(unittest.TestCase):
    def test_impossible_flags_rejected_before_any_work(self):
        """Still impossible for a beam body: it has no MuJoCo actuators and no tendons, so there
        is nothing for flex or a CPG to drive and no actuator force to charge for."""
        with tempfile.TemporaryDirectory() as tmp:
            for extra in (['--flex'], ['--use-cpg'], ['--fitness', 'efficiency']):
                r = run_cli(['--map-elites', '--gen', '1', '--pop', '2', '--workers', '1',
                             '--name', 'cli_reject', '--body', 'beam'] + extra, tmp)
                self.assertIn('ERROR: --body beam cannot be combined with', r.stdout + r.stderr, extra)
            self.assertFalse(os.path.exists(os.path.join(tmp, 'results')), 'a rejected run created output')

    def test_gait_flags_are_now_accepted(self):
        """--per-voxel-phase / --evolve-gait / --freeze-body became available for beam bodies on
        2026-10-02; they are what stage 2 of the two-stage protocol needs."""
        with tempfile.TemporaryDirectory() as tmp:
            cases = [(['--evolve-gait'], 'gait_wave'),
                     (['--per-voxel-phase'], 'gait_pvp'),
                     (['--per-voxel-phase', '--freeze-body'], 'gait_frozen')]
            for extra, name in cases:
                r = run_cli(['--map-elites', '--gen', '1', '--pop', '2', '--workers', '1',
                             '--sim-time', '0.25', '--settle', '0', '--freq', '40',
                             '--grid-size', '5', '--no-trim',
                             '--name', name, '--body', 'beam'] + extra, tmp)
                self.assertNotIn('cannot be combined with', r.stdout + r.stderr, extra)
                self.assertIn('MAP-ELITES COMPLETE', r.stdout, extra)

    def test_help_lists_body(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py'), '--help'],
                           capture_output=True, text=True, timeout=60)
        self.assertIn('--body {springs,beam}', r.stdout)


class TestVolumetricPlumbing(unittest.TestCase):
    """--poisson / --dt-rule must reach the engine, the workers and the checkpoint."""

    def test_engine_defaults_are_the_new_physics(self):
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        e = MuJoCoBeamPhysics()
        self.assertTrue(e.poisson)
        self.assertEqual(e.dt_rule, 'voxelyze')

    def test_evaluator_passes_them_through(self):
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        ev = MuJoCoTendonEvaluator(n_workers=1, body='beam')
        self.assertTrue(ev.engine.poisson)
        self.assertEqual(ev.engine.dt_rule, 'voxelyze')
        ev = MuJoCoTendonEvaluator(n_workers=1, body='beam', poisson=False, dt_rule='ours')
        self.assertFalse(ev.engine.poisson)
        self.assertEqual(ev.engine.dt_rule, 'ours')

    @unittest.skipUnless(os.path.exists(ARCHIVE), 'reference archive not present')
    def test_workers_get_the_same_physics(self):
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        g = smallest_archive_body()
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=SS)
        e.load_robot(g)
        direct = float(e.get_fitness(simulation_time=0.4, settle_time=0.2,
                                     early_term_threshold=0.02, early_term_fraction=0.5))
        ev = MuJoCoTendonEvaluator(simulation_time=0.4, settle_time=0.2, actuation_amplitude=0.2,
                                   n_workers=2, attach_controller=False, fitness_mode='forward',
                                   friction=SS, early_term_threshold=0.02, early_term_fraction=0.5,
                                   body='beam')
        got = [float(x) for x in ev.evaluate_batch([g, g])]
        ev.close()
        self.assertEqual(got, [direct, direct])

        ev = MuJoCoTendonEvaluator(simulation_time=0.4, settle_time=0.2, actuation_amplitude=0.2,
                                   n_workers=2, attach_controller=False, fitness_mode='forward',
                                   friction=SS, early_term_threshold=0.02, early_term_fraction=0.5,
                                   body='beam', poisson=False, dt_rule='ours')
        old = [float(x) for x in ev.evaluate_batch([g])]
        ev.close()
        self.assertNotAlmostEqual(old[0], direct, places=4)


class TestVolumetricResumeSafeguard(TestResumeSafeguard):
    def test_new_flags_are_checked(self):
        self.assertTrue(self.resumes({'physics': self.phys(poisson=True, dt_rule='voxelyze')},
                                     self.phys(poisson=True, dt_rule='voxelyze')))
        self.assertFalse(self.resumes({'physics': self.phys(poisson=True, dt_rule='voxelyze')},
                                      self.phys(poisson=False, dt_rule='voxelyze')))
        self.assertFalse(self.resumes({'physics': self.phys(poisson=True, dt_rule='voxelyze')},
                                      self.phys(poisson=True, dt_rule='ours')))

    def test_the_pilot_checkpoint_predates_the_flags(self):
        """cheney_beam_s1 ran without them, so resuming it on the new defaults must be refused
        and resuming it with --poisson off --dt-rule ours must be allowed."""
        pilot = {'physics': self.phys()}          # no poisson / dt_rule keys
        self.assertFalse(self.resumes(pilot, self.phys(poisson=True, dt_rule='voxelyze')))
        self.assertTrue(self.resumes(pilot, self.phys(poisson=False, dt_rule='ours')))

    def test_springs_runs_are_unaffected(self):
        """Springs checkpoints carry no poisson/dt_rule, and a springs command must not send
        them - otherwise every older springs run would refuse to resume."""
        springs = {k: v for k, v in self.phys(body='springs').items()}
        self.assertTrue(self.resumes({'physics': springs}, springs))


class TestVolumetricCommandLine(unittest.TestCase):
    def test_help_lists_the_flags(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py'), '--help'],
                           capture_output=True, text=True, timeout=60)
        self.assertIn('--poisson {on,off}', r.stdout)
        self.assertIn('--dt-rule {voxelyze,ours}', r.stdout)

    def test_rejected_with_springs(self):
        with tempfile.TemporaryDirectory() as tmp:
            for extra in (['--poisson', 'off'], ['--dt-rule', 'ours']):
                r = run_cli(['--map-elites', '--gen', '1', '--pop', '2', '--workers', '1',
                             '--name', 'cli_reject_vol'] + extra, tmp)
                self.assertIn('only applies to --body beam', r.stdout + r.stderr, extra)
            self.assertFalse(os.path.exists(os.path.join(tmp, 'results')))


def legs_walker():
    """A 5-voxel beam body with a foot at each end; it walks ~3 voxels in 10 cycles at 40 Hz."""
    g = np.zeros((20, 20, 20), np.int8)
    for x in range(5):
        for y in range(3):
            for z in range(3):
                if z > 0 or x in (0, 4):
                    g[x, y, z] = 1 if x < 2 else 2
    return g


class TestScoreSwitches(unittest.TestCase):
    """--direction / --divide-by (Cheney 2013's score) must reach the engine, the worker
    processes, the checkpoint and the logs, and leave every default run unchanged."""
    CHENEY = dict(direction='any', divide_by='workspace', workspace_voxels=10)
    BEAM = dict(simulation_time=0.25, settle_time=0.0, actuation_amplitude=0.2,
                actuation_frequency=40.0, attach_controller=False, fitness_mode='forward',
                friction=SS, early_term_threshold=0.02, early_term_fraction=0.5, body='beam',
                materials='cheney2013', floor_contact='voxelyze')

    def test_workers_get_the_same_score(self):
        from src.physics.mujoco_beam_physics import MuJoCoBeamPhysics
        from src.evolution.mujoco_tendon_evaluator import MuJoCoTendonEvaluator
        g = legs_walker()
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                              fitness_mode='forward', friction=SS, materials='cheney2013',
                              floor_contact='voxelyze', **self.CHENEY)
        e.load_robot(g)
        direct = float(e.get_fitness(0.25, 0.0, early_term_threshold=0.02, early_term_fraction=0.5))
        ev = MuJoCoTendonEvaluator(n_workers=2, **self.BEAM, **self.CHENEY)
        got = [float(x) for x in ev.evaluate_batch([g, g])]
        ev.close()
        self.assertEqual(got, [direct, direct])
        ev = MuJoCoTendonEvaluator(n_workers=2, **self.BEAM)          # default score differs
        default = [float(x) for x in ev.evaluate_batch([g])]
        ev.close()
        self.assertNotAlmostEqual(default[0], direct, places=3)

    def test_resume_checks_the_score(self):
        sys.path.insert(0, ROOT)
        import run_tendon_evolution as R
        base = {'friction': SS, 'body': 'beam', 'sim_time': 0.25, 'settle_time': 0.0}

        def ok(ck, phys):
            try:
                R._check_resume_physics(ck, phys)
                return True
            except SystemExit:
                return False
        new = {**base, 'direction': 'any', 'divide_by': 'workspace', 'workspace_voxels': 10}
        old = {**base, 'direction': 'forward', 'divide_by': 'body'}
        self.assertTrue(ok({'physics': new}, new))
        self.assertFalse(ok({'physics': new}, old))
        self.assertFalse(ok({'physics': new}, {**new, 'workspace_voxels': 8}))
        self.assertTrue(ok({'physics': base}, old))       # checkpoints before the flags: defaults
        self.assertFalse(ok({'physics': base}, new))

    def test_help_lists_the_flags(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'run_tendon_evolution.py'), '--help'],
                           capture_output=True, text=True, timeout=60)
        self.assertIn('--direction {forward,any}', r.stdout)
        self.assertIn('--divide-by {body,workspace}', r.stdout)

    def test_runs_and_reports_in_workspace_widths(self):
        common = ['--gen', '1', '--pop', '4', '--workers', '1', '--sim-time', '0.25',
                  '--settle', '0', '--freq', '40', '--grid-size', '5', '--no-trim', '--body', 'beam',
                  '--materials', 'cheney2013', '--floor-contact', 'voxelyze',
                  '--direction', 'any', '--divide-by', 'workspace']
        with tempfile.TemporaryDirectory() as tmp:
            r = run_cli(['--no-age-pareto', '--name', 'score_neat'] + common, tmp)
            self.assertIn('EVOLUTION COMPLETE', r.stdout, r.stderr[-800:])
            self.assertIn('Score      : 3D COM displacement in ANY direction, per FIXED workspace '
                          'width of 5 voxels [W]', r.stdout)
            self.assertRegex(r.stdout, r'Gen   1/1  best=\d+\.\d{4}W  mean=')
            r = run_cli(['--map-elites', '--name', 'score_me'] + common, tmp)
            self.assertIn('MAP-ELITES COMPLETE', r.stdout, r.stderr[-800:])
            self.assertRegex(r.stdout, r'max=\d+\.\d{4}W  top10=')

    def test_default_runs_still_report_body_lengths(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_cli(['--no-age-pareto', '--gen', '1', '--pop', '4', '--workers', '1',
                         '--sim-time', '0.25', '--settle', '0', '--freq', '40', '--grid-size', '5',
                         '--no-trim', '--body', 'beam', '--name', 'score_default'], tmp)
            self.assertIn('Score      : forward (+X) COM displacement, per own body length [BL]',
                          r.stdout, r.stderr[-800:])
            self.assertRegex(r.stdout, r'Gen   1/1  best=\d+\.\d{4}BL  mean=')

    def test_rejected_with_flex(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_cli(['--map-elites', '--gen', '1', '--pop', '2', '--workers', '1', '--flex',
                         '--name', 'score_flex', '--direction', 'any'], tmp)
            self.assertIn('not --flex', r.stdout + r.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, 'results')))


@unittest.skipUnless(os.path.exists(os.path.join(ROOT, 'results', 'cheney_floor_s1', 'archive.pkl')),
                     'E1 results not present')
class TestTools(unittest.TestCase):
    def test_render_beam(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'x.gif')
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'render_champion.py'),
                                os.path.join(ROOT, 'results', 'cheney_floor_s1', 'best_robot.pkl'),
                                '--body', 'beam', '--amp', '0.2', '--sim-time', '0.1', '--settle', '0.05',
                                '--friction-static', '1.0', '--friction-kinetic', '0.5', '--out', out],
                               cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-500:])
            self.assertTrue(os.path.getsize(out) > 1000)

    def test_scorecard_dynamic_beam(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'morphology_scorecard.py'),
                            os.path.join(ROOT, 'results', 'cheney_floor_s1'), '--dynamic', '--body', 'beam',
                            '--amp', '0.2', '--sim-time', '0.1', '--settle', '0.05'],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertIn('dynamic (champion', r.stdout)


if __name__ == '__main__':
    unittest.main()
