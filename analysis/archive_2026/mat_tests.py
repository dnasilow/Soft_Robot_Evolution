class TestMaterialPresets(unittest.TestCase):
    """`--materials cheney2013` must reproduce Cheney's OWN dimensionless physics on our lattice.

    A voxel lattice's behaviour is fixed by E/(rho*L^2) (natural frequency) and rho*g*L/E (sag per
    voxel). His .vxa: rho 1e6, L 1e-3, E 1e7 (hard 5e7), g 27.468 -> w = 3162 rad/s, sag/L =
    0.0027468. The old 'evosoro' preset corrected for density but not for our 10x bigger lattice,
    which is why our bodies were 200x too soft.
    """
    RHO_C, L_C, E_C, G_C = 1e6, 1e-3, 1e7, 27.468

    def cheney_targets(self):
        return (np.sqrt(self.E_C / (self.RHO_C * self.L_C ** 2)),          # rad/s
                self.RHO_C * self.G_C * self.L_C / self.E_C)               # sag per voxel

    def test_evosoro_preset_is_unchanged(self):
        """Runs before 2026-09-24 must keep their exact numbers."""
        self.assertEqual(e_scaled(3), 5e3)
        self.assertEqual(e_scaled(4), 5e5)
        self.assertEqual(e_scaled(3, 'evosoro', 0.01), 5e3)
        self.assertEqual(gravity_scaled('evosoro', 0.01), 9.81)

    def test_cheney_preset_matches_his_natural_frequency(self):
        w_target, _ = self.cheney_targets()
        E = e_scaled(3, 'cheney2013', L)
        w = np.sqrt(E / (RHO * L ** 2))
        self.assertAlmostEqual(w / w_target, 1.0, places=9)

    def test_cheney_preset_matches_his_sag_per_voxel(self):
        _, sag_target = self.cheney_targets()
        E = e_scaled(3, 'cheney2013', L)
        g = gravity_scaled('cheney2013', L)
        self.assertAlmostEqual((RHO * g * L / E) / sag_target, 1.0, places=9)

    def test_his_hard_material_is_five_times_soft_not_a_hundred(self):
        self.assertAlmostEqual(e_scaled(4, 'cheney2013', L) / e_scaled(3, 'cheney2013', L), 5.0)
        self.assertAlmostEqual(e_scaled(4) / e_scaled(3), 100.0)

    def test_engine_uses_the_preset(self):
        cells = [(x, y, z) for x in range(3) for y in range(3) for z in range(3)]
        soft = engine(grid_with(cells, 3), materials='cheney2013')
        self.assertAlmostEqual(soft.g_acc, gravity_scaled('cheney2013', L), places=9)
        self.assertAlmostEqual(float(soft.model.opt.gravity[2]), -soft.g_acc, places=4)
        self.assertAlmostEqual(soft.bE.max(), e_scaled(3, 'cheney2013', L), places=6)
        old = engine(grid_with(cells, 3))
        self.assertAlmostEqual(float(old.model.opt.gravity[2]), -9.81, places=6)
        self.assertAlmostEqual(old.bE.max(), e_scaled(3), places=6)

    def test_explicit_gravity_overrides_the_preset(self):
        e = engine(grid_with([(1, 1, 1), (2, 1, 1)]), materials='cheney2013', gravity=3.71)
        self.assertAlmostEqual(float(e.model.opt.gravity[2]), -3.71, places=6)

    def test_stiffer_bodies_need_a_smaller_step(self):
        cells = [(x, y, z) for x in range(3) for y in range(3) for z in range(3)]
        a = engine(grid_with(cells, 3)).stable_dt(0.01)
        b = engine(grid_with(cells, 3), materials='cheney2013').stable_dt(0.01)
        ratio = np.sqrt(e_scaled(3, 'cheney2013', L) / e_scaled(3))
        self.assertAlmostEqual(a / b, ratio, places=6)      # 200x stiffer -> 14.1x smaller step

    def test_rejects_an_unknown_preset(self):
        with self.assertRaises(ValueError):
            MuJoCoBeamPhysics(materials='cheney2015')


