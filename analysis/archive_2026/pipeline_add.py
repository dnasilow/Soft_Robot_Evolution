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


