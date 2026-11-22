class TestControlGain(unittest.TestCase):
    """The evolvable gain on a control CPPN (--phase-gain-init). Stage 2 on beam bodies needs a new
    control network to start as a SMALL perturbation of the body's gait: a full-range random field
    destroyed the seeded stage-1 bodies (1.62 -> 0.09 BL) before stage 2 could begin."""

    def genome(self):
        from src.evolution.cppn_genome import CPPNGenome, InnovationCounter
        return CPPNGenome(InnovationCounter(), np.random.default_rng(1))

    def test_gain_survives_copy_and_mutation(self):
        """CPPNGenome._clone rebuilds the genome from an explicit attribute list, so an attribute
        it does not name is silently dropped. The gain would then revert to 1.0 - wrecking the
        bodies anyway, with nothing to show it had happened."""
        from src.evolution.cppn_genome import _phase_innov
        rng = np.random.default_rng(0)
        g = self.genome()
        g.init_phase_cppn(rng, gain=0.05)
        self.assertEqual(g.phase_cppn.phase_gain, 0.05)
        self.assertEqual(g.copy().phase_cppn.phase_gain, 0.05)
        self.assertEqual(g.phase_cppn.mutate(_phase_innov(), rate=0.3).phase_gain, 0.05)
        from src.evolution.cppn_genome import InnovationCounter
        child = g.mutate(InnovationCounter(), rate=0.3)          # body mutation path
        self.assertIsNotNone(child.phase_cppn.phase_gain)

    def test_no_gain_keeps_the_original_behaviour(self):
        rng = np.random.default_rng(0)
        g = self.genome()
        g.init_phase_cppn(rng)
        self.assertIsNone(g.phase_cppn.phase_gain)
        before = None
        g.phase_cppn.mutate_phase_gain(rng)                       # must be a no-op
        self.assertIsNone(g.phase_cppn.phase_gain)

    def test_gain_mutation_is_multiplicative_and_bounded(self):
        rng = np.random.default_rng(0)
        g = self.genome()
        g.init_phase_cppn(rng, gain=0.05)
        seen = []
        for _ in range(500):
            g.phase_cppn.mutate_phase_gain(rng)
            seen.append(g.phase_cppn.phase_gain)
        self.assertGreaterEqual(min(seen), 1e-3)
        self.assertLessEqual(max(seen), 1.0)
        self.assertGreater(max(seen), 0.5)                        # it CAN grow to full range

    def test_beam_field_scales_with_the_gain(self):
        from src.evolution.cppn_genome import CPPNGenome, _phase_innov
        body = TestBeamGaits().body()
        net = CPPNGenome(_phase_innov(), np.random.default_rng(3))
        ref = engine(body, amp=0.2)                               # material gait

        def phases(gain):
            net.phase_gain = gain
            e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward',
                                  phase_mode='offset')
            e.load_robot(body, gait_params=net)
            return e.v_phase - ref.v_phase                        # the offset field alone

        full, half, zero = phases(None), phases(0.5), phases(0.0)
        self.assertTrue(np.allclose(zero, 0.0))                   # gain 0 = the material gait
        self.assertTrue(np.allclose(half, 0.5 * full))            # linear in the gain
        self.assertGreater(float(np.abs(full).max()), 0.0)

    def test_tendon_engine_is_unchanged_without_a_gain(self):
        """The tendon engine reads the same gain; with none set it must behave exactly as before."""
        from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
        from src.evolution.cppn_genome import CPPNGenome, _phase_innov
        g = grid_with([(x, y, 1) for x in range(3) for y in range(2)], 1)
        net = CPPNGenome(_phase_innov(), np.random.default_rng(5))
        a = MuJoCoTendonPhysics(actuation_amplitude=0.1)
        a.load_robot(g, gait_params=net)
        net.phase_gain = 1.0
        b = MuJoCoTendonPhysics(actuation_amplitude=0.1)
        b.load_robot(g, gait_params=net)
        self.assertTrue(np.allclose(a._base_phases, b._base_phases))


