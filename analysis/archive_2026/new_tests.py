class TestPoissonLaw(unittest.TestCase):
    """Voxelyze's volumetric material law, checked against its own source:
    CVX_Material::stress   -> sigma = Ehat*((1-nu)*eps + nu*(eps_t1 + eps_t2)), Ehat = E/((1-2nu)(1+nu))
    CVX_Link::updateForces -> axial force = sigma * currentTransverseArea
    CVX_Voxel::strain(true) -> an axis with bonds on both sides takes the average of its bonds'
    shares of their axial strain; any other axis takes the bulge (1 + sum of the constrained
    strains)^(-nu) - 1."""

    def test_ehat_matches_voxelyze(self):
        self.assertAlmostEqual(EHAT, 1 / ((1 - 2 * POISSON) * (1 + POISSON)), places=12)
        self.assertAlmostEqual(EHAT * (1 - POISSON), 1.6049382716049383, places=12)

    def test_free_bar_does_not_bulge(self):
        """Two voxels: no axis has bonds on both sides, so nothing is constrained, the bulge is
        (1+0)^-nu - 1 = 0 and the response is Ehat*(1-nu) = 1.605 E. Voxelyze behaves the same."""
        e = engine(grid_with([(1, 1, 1), (2, 1, 1)]))
        eps = np.array([0.01])
        self.assertTrue(np.allclose(e.poisson_strain(eps), 0.0))
        F = e.axial_bond_force(eps * L, np.array([L]))[0]
        self.assertAlmostEqual(F / (e_scaled(3) * L * L * 0.01), EHAT * (1 - POISSON), places=9)

    def test_long_chain_responds_with_plain_e(self):
        """A column free to contract sideways: the bulge cancels Ehat back to E, which is the
        point of the law (and why the cantilever checks above still hold)."""
        e = engine(grid_with([(i, 1, 1) for i in range(9)]))
        eps0, nb = 0.01, len(e.bi)
        ps = e.poisson_strain(np.full(nb, eps0))
        bulge = (1 + eps0) ** (-POISSON) - 1
        self.assertTrue(np.allclose(ps[4], [eps0, bulge, bulge]))
        self.assertTrue(np.allclose(ps[0], 0.0))          # the end voxel has no constrained axis
        F = e.axial_bond_force(np.full(nb, eps0 * L), np.full(nb, L))
        sigma = e_scaled(3) * EHAT * ((1 - POISSON) * eps0 + POISSON * 2 * bulge)
        self.assertAlmostEqual(F[4], sigma * L * L * (1 + bulge) ** 2, delta=1e-15)
        self.assertAlmostEqual(F[4] / (e_scaled(3) * L * L * eps0), 1.0, delta=0.01)

    def test_voxel_squeezed_on_all_sides_is_1_6x_stiffer(self):
        """The gap the pilot ran without: inside a solid body nothing can bulge, so the same
        strain costs Ehat*(1-nu) = 1.605 E instead of E."""
        e = engine(grid_with([(x, y, z) for x in range(5) for y in range(5) for z in range(5)]))
        eps = np.where(e.ba == 0, 0.01, 0.0)
        c = e.cells.index((2, 2, 2))
        self.assertTrue(e._tension[c].all())
        self.assertTrue(np.allclose(e.poisson_strain(eps)[c], [0.01, 0.0, 0.0]))
        b = next(k for k in range(len(e.bi)) if e.ba[k] == 0 and e.cells[e.bi[k]] == (2, 2, 2))
        F = e.axial_bond_force(eps * L, np.full(len(e.bi), L))[b]
        self.assertAlmostEqual(F / (e_scaled(3) * L * L * 0.01), EHAT * (1 - POISSON), places=9)

    def test_compression_bulges_the_free_axes(self):
        e = engine(grid_with([(i, 1, 1) for i in range(9)]))
        ps = e.poisson_strain(np.full(len(e.bi), -0.02))
        self.assertLess(ps[4][0], 0.0)
        self.assertGreater(ps[4][1], 0.0)
        self.assertAlmostEqual(ps[4][1], (1 - 0.02) ** (-POISSON) - 1, places=12)

    def test_strain_splits_by_stiffness_ratio(self):
        """CVX_Link::axialStrain, strainRatio = E_pos/E_neg."""
        e = engine(grid_with([(1, 1, 1)], 3) + grid_with([(2, 1, 1)], 4))
        r = e_scaled(4) / e_scaled(3)
        self.assertAlmostEqual(e._f_pos[0], 2 * r / (1 + r), places=12)
        self.assertAlmostEqual(e._f_neg[0], 2 / (1 + r), places=12)
        self.assertAlmostEqual(e._f_pos[0] + e._f_neg[0], 2.0, places=12)

    def test_a_voxel_held_to_the_world_counts_as_constrained(self):
        e = engine(grid_with([(i, 1, 1) for i in range(6)]), clamped=[0], height=0.05)
        self.assertTrue(e._tension[0][0])                  # clamped end: one bond, still constrained
        self.assertFalse(e._tension[5][0])                 # free end: one bond, free to bulge
        self.assertTrue(e._tension[3][0])                  # interior: bonds on both sides

    def test_off_restores_the_old_linear_law(self):
        e = engine(grid_with([(i, 1, 1) for i in range(6)]), poisson=False)
        ext = np.linspace(-1e-4, 1e-4, len(e.bi))
        self.assertTrue(np.allclose(e.axial_bond_force(ext, np.full(len(e.bi), L)), e.K_ax * ext))


class TestPoissonInABody(unittest.TestCase):
    """The law as it reaches forces(): sign, magnitude and the usual invariants."""

    def stretched_chain(self, n=9, eps0=0.01):
        e = engine(grid_with([(i, 1, 1) for i in range(n)]), gravity=False, height=0.05)
        q = e.data.qpos.reshape(n, 7)
        q[:, 0] = q[0, 0] + np.arange(n) * L * (1 + eps0)
        mujoco.mj_forward(e.model, e.data)
        return e, e.forces(np.zeros(n))

    def test_end_voxel_feels_stress_times_area(self):
        n, eps0 = 9, 0.01
        e, (F, T) = self.stretched_chain(n, eps0)
        want = e.axial_bond_force(np.full(len(e.bi), eps0 * L), np.full(len(e.bi), L))[0]
        self.assertAlmostEqual(F[0, 0], want, delta=1e-9 * abs(want))   # pulled toward its neighbour
        self.assertGreater(F[0, 0], 0.0)
        self.assertTrue(np.allclose(F[:, 1:], 0.0, atol=1e-12))

    def test_uniformly_stretched_interior_is_balanced(self):
        e, (F, T) = self.stretched_chain()
        self.assertTrue(np.allclose(F[2:7], 0.0, atol=1e-12))
        self.assertAlmostEqual(F[:, 0].sum(), 0.0, delta=1e-12)

    def test_rigid_motion_gives_no_internal_force(self):
        cells = [(x, y, z) for x in range(3) for y in range(3) for z in range(2)]
        e = engine(grid_with(cells), gravity=False, height=0.2)
        rng = np.random.default_rng(0)
        q = e.data.qpos.reshape(len(e.cells), 7)
        ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
        ang = 0.4
        R = (np.cos(ang) * np.eye(3) + np.sin(ang) * np.cross(np.eye(3), ax)
             + (1 - np.cos(ang)) * np.outer(ax, ax))
        c = q[:, :3].mean(0)
        q[:, :3] = (q[:, :3] - c) @ R.T + c + np.array([0.01, -0.02, 0.03])
        q[:, 3:] = np.concatenate([[np.cos(ang / 2)], np.sin(ang / 2) * ax])
        mujoco.mj_forward(e.model, e.data)
        F, T = e.forces(np.zeros(len(e.cells)))
        scale = e_scaled(3) * L * L
        self.assertLess(np.abs(F).max() / scale, 1e-9)
        self.assertLess(np.abs(T).max() / (scale * L), 1e-9)

    def test_the_flag_changes_a_real_robot(self):
        """Guard against the flag silently doing nothing."""
        path = os.path.join(ROOT, 'results', 'cheney_beam_s1', 'best_robot.pkl')
        if not os.path.exists(path):
            self.skipTest('pilot champion not present')
        with open(path, 'rb') as fh:
            g = pickle.load(fh)['genome']
        out = []
        for pois in (False, True):
            e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', poisson=pois,
                                  dt_rule='ours')
            e.load_robot(g)
            out.append(float(e.get_fitness(simulation_time=0.3, settle_time=0.1)))
        self.assertNotAlmostEqual(out[0], out[1], places=4)


class TestTimeStepRules(unittest.TestCase):
    def chain(self, mat=3, **kw):
        return engine(grid_with([(i, 1, 1) for i in range(6)], mat), **kw)

    def test_voxelyze_rule_is_one_radian_of_the_fastest_axial_mode(self):
        e = self.chain()
        want = DT_FRAC_VX / (2 * np.pi * np.sqrt(e.axial_stiffness().max() / e._m))
        self.assertAlmostEqual(e.default_timestep, min(want, 0.0005), places=12)
        self.assertAlmostEqual(e.axial_stiffness().max(), e_scaled(3) * EHAT * L, places=12)
        self.assertAlmostEqual(e._m, RHO * L ** 3, places=15)

    def test_the_volumetric_law_shrinks_the_step_by_sqrt_ehat(self):
        on = self.chain(poisson=True).stable_dt(0.01)
        off = self.chain(poisson=False).stable_dt(0.01)
        self.assertAlmostEqual(off / on, np.sqrt(EHAT), places=9)

    def test_both_rules_scale_with_sqrt_e(self):
        for rule in ('voxelyze', 'ours'):
            soft = self.chain(3, dt_rule=rule).stable_dt(0.01)
            bone = self.chain(4, dt_rule=rule).stable_dt(0.01)
            self.assertAlmostEqual(soft / bone, 10.0, places=6, msg=rule)

    def test_voxelyze_rule_is_the_larger_step(self):
        self.assertGreater(self.chain(4, dt_rule='voxelyze').stable_dt(),
                           self.chain(4, dt_rule='ours').stable_dt())

    def test_rejects_an_unknown_rule(self):
        with self.assertRaises(ValueError):
            MuJoCoBeamPhysics(dt_rule='fastest')

    def test_a_bone_body_stays_stable_on_the_voxelyze_rule(self):
        g = (grid_with([(x, y, 1) for x in range(4) for y in range(3)], 4)
             + grid_with([(x, y, 2) for x in range(4) for y in range(3)], 1))
        e = engine(g, amp=0.2)
        for _ in range(int(0.2 / e.default_timestep)):
            e.step()
        self.assertTrue(np.all(np.isfinite(e.data.qvel)))
        self.assertLess(np.abs(e.data.qvel).max(), 100.0)


class TestPilotRegression(unittest.TestCase):
    """The 2026-09-17 pilot (cheney_beam_s1) ran with the volumetric law off and the old step
    rule. Those settings must still reproduce its recorded champion score exactly."""

    def test_pilot_champion_score(self):
        path = os.path.join(ROOT, 'results', 'cheney_beam_s1', 'best_robot.pkl')
        if not os.path.exists(path):
            self.skipTest('pilot champion not present')
        with open(path, 'rb') as fh:
            g = pickle.load(fh)['genome']
        fr = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward', friction=fr,
                              poisson=False, dt_rule='ours')
        e.load_robot(g)
        f = e.get_fitness(simulation_time=1.0, settle_time=0.5,
                          early_term_threshold=0.02, early_term_fraction=0.5)
        self.assertEqual(f"{float(f):.4f}", "1.6401")


