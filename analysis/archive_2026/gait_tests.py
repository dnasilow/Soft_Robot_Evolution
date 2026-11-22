class TestBeamGaits(unittest.TestCase):
    """The beam body accepts a per-robot gait, which is what stage 2 of the two-stage protocol
    (Mertan & Cheney 2024) optimises on a frozen morphology. Added 2026-10-02; before that the
    engine only had the material 2-phase gait and --per-voxel-phase was rejected for beam."""

    CELLS = [(x, y, z) for x in range(4) for y in range(3) for z in range(2)]

    def body(self):
        return grid_with(self.CELLS, 1) + grid_with([(x, y, 2) for x in range(4)
                                                     for y in range(3)], 2)

    class Field:
        """Stand-in control CPPN: a spatial phase field, scaled by `gain`."""

        def __init__(self, gain=1.0, k=2.0):
            self.gain, self.k = gain, k

        def evaluate_batch(self, coords):
            return (self.gain * np.tanh(self.k * coords[:, 0]))[:, None]

    def test_material_gait_is_still_the_default(self):
        e = engine(self.body(), amp=0.2)
        self.assertEqual(sorted({round(float(p), 6) for p in e.v_phase}),
                         [0.0, round(float(np.pi), 6)])

    def test_phase_cppn_gives_a_spatial_phase_field(self):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(self.body(), gait_params=self.Field())
        self.assertGreater(len({round(float(p), 4) for p in e.v_phase}), 2)
        self.assertLessEqual(float(np.abs(e.v_phase).max()), np.pi * 1.0001 + np.pi)

    def test_offset_mode_starts_from_the_material_gait(self):
        """The default. A zero-output control net must leave the gait exactly as evolved, so
        stage 2 searches outward from a working baseline instead of from noise."""
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward',
                              phase_mode='offset')
        e.load_robot(self.body(), gait_params=self.Field(gain=0.0))
        ref = engine(self.body(), amp=0.2)
        self.assertTrue(np.allclose(e.v_phase, ref.v_phase))

    def test_replace_mode_discards_the_material_gait(self):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward',
                              phase_mode='replace')
        e.load_robot(self.body(), gait_params=self.Field(gain=0.0))
        self.assertTrue(np.allclose(e.v_phase, 0.0))

    def test_traveling_wave_is_a_plane_wave(self):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward',
                              phase_mode='replace')
        e.load_robot(self.body(), gait_params=(1.0, 0.0, 0.0, 0.25))
        cells = np.asarray(e.cells, float)
        xs = cells[:, 0]
        xn = (xs - xs.min()) / (xs.max() - xs.min())
        self.assertTrue(np.allclose(e.v_phase, 2 * np.pi * xn + 0.25))

    def test_the_gait_changes_the_motion(self):
        """Guard against the class of bug that has bitten this project twice: a controller that
        is stored but never reaches the simulation."""
        g = self.body()
        out = []
        for gp in (None, self.Field(gain=0.9, k=4.0)):
            e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward',
                                  actuation_frequency=40.0, materials='cheney2013',
                                  floor_contact='voxelyze')
            e.load_robot(g, gait_params=gp)
            out.append(float(e.get_fitness(0.25, 0.0, early_term_threshold=-1e9)))
        self.assertNotAlmostEqual(out[0], out[1], places=4)

    def test_phase_field_does_not_depend_on_where_the_body_is_dropped(self):
        a = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        a.load_robot(self.body(), gait_params=self.Field())
        b = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        b.load_robot(self.body(), initial_height=0.3, gait_params=self.Field())
        self.assertTrue(np.allclose(a.v_phase, b.v_phase))

    def test_passive_voxels_stay_inert(self):
        g = grid_with(self.CELLS, 3)                      # all soft, no muscle
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(g, gait_params=self.Field())
        self.assertTrue(np.allclose(e.v_amp, 0.0))
        self.assertTrue(np.allclose(e.voxel_strain(0.123), 0.0))

    def test_rejects_an_unknown_phase_mode(self):
        with self.assertRaises(ValueError):
            MuJoCoBeamPhysics(phase_mode='add')


