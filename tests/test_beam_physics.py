"""Unit tests for the Voxelyze-style beam body (src/physics/mujoco_beam_physics.py).

Run from the repo root:   python -m unittest discover -s tests -t . -v
"""
import os
import pickle
import unittest

import mujoco
import numpy as np

from src.physics.mujoco_beam_physics import (MuJoCoBeamPhysics, e_scaled, bond_modulus, POISSON,
                                             ZETA_GLOBAL, COLLISION_DEPTH, ENVELOPE_RADIUS,
                                             EHAT, DT_FRAC_VX, RHO, gravity_scaled)

L = 0.01
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def grid_with(cells, mat=3, shape=(20, 20, 20)):
    g = np.zeros(shape, np.int8)
    for c in cells:
        g[c] = mat
    return g


def engine(grid, amp=0.0, gravity=True, clamped=(), height=0.0, friction=None, freq=10.0,
           poisson=True, dt_rule='voxelyze', materials='evosoro', gravity_acc=None,
           floor_contact='mujoco'):
    e = MuJoCoBeamPhysics(actuation_amplitude=amp, fitness_mode='forward', friction=friction,
                          actuation_frequency=freq, poisson=poisson, dt_rule=dt_rule,
                          materials=materials, gravity=gravity_acc, floor_contact=floor_contact)
    e.load_robot(grid, initial_height=height, clamped=clamped)
    if not gravity:
        e.model.opt.gravity[:] = 0
    return e


class TestBeamStatics(unittest.TestCase):
    """Cantilever of N soft voxels, voxel 0 clamped, lifted off the floor, gravity off, small tip
    load; after settling (test-only drag) the tip response must match Euler-Bernoulli beam theory
    with l = (N-1)*L, A = L^2, I = L^4/12, J-equivalent = Voxelyze's a2 = E*L^3/(12(1+nu))."""
    N = 5

    def run_cantilever(self, load, poisson=False):
        g = grid_with([(i, 1, 1) for i in range(self.N)])
        e = engine(g, gravity=False, clamped=[0], height=0.05, poisson=poisson)
        e.test_damping = 30.0
        tip = self.N - 1
        e.external = np.zeros((self.N, 6))
        e.external[tip] = load
        mujoco.mj_forward(e.model, e.data)
        p0 = e.data.xpos[1 + tip].copy()
        for _ in range(int(4.0 / e.default_timestep)):
            e.step()
        return e, e.data.xpos[1 + tip] - p0, e.data.xquat[1 + tip].copy()

    def test_axial(self):
        E = e_scaled(3); A = L * L; l = (self.N - 1) * L; F = 0.01 * E * A
        _, dp, _ = self.run_cantilever([F, 0, 0, 0, 0, 0])
        self.assertAlmostEqual(dp[0] / (F * l / (E * A)), 1.0, delta=0.01)

    def test_bending(self):
        E = e_scaled(3); I = L ** 4 / 12; l = (self.N - 1) * L
        F = 0.3 * E * I / l ** 3 * L                     # tip deflection ~0.1 L: linear regime
        _, dp, _ = self.run_cantilever([0, F, 0, 0, 0, 0])
        self.assertAlmostEqual(dp[1] / (F * l ** 3 / (3 * E * I)), 1.0, delta=0.01)

    def test_bending_is_unaffected_by_the_volumetric_law(self):
        """Bending is carried by K_b / K_sh, which the Poisson coupling does not touch; the only
        route in is the bonds' small axial strains, so the tip deflection must barely move."""
        E = e_scaled(3); I = L ** 4 / 12; l = (self.N - 1) * L
        F = 0.3 * E * I / l ** 3 * L
        _, off, _ = self.run_cantilever([0, F, 0, 0, 0, 0], poisson=False)
        _, on, _ = self.run_cantilever([0, F, 0, 0, 0, 0], poisson=True)
        self.assertAlmostEqual(on[1] / off[1], 1.0, delta=0.02)

    def test_twist(self):
        E = e_scaled(3); kt = E * L ** 3 / (12 * (1 + POISSON)); Tq = 0.01 * kt
        _, _, q = self.run_cantilever([0, 0, 0, Tq, 0, 0])
        ang = 2 * np.arctan2(np.linalg.norm(q[1:]), q[0]) * np.sign(q[1])
        self.assertAlmostEqual(ang / (Tq * (self.N - 1) / kt), 1.0, delta=0.01)


class TestMuscles(unittest.TestCase):
    def test_volumetric_stroke(self):
        """A free all-muscle block expands and contracts by exactly +/- amp in every direction."""
        cells = [(x, y, z) for x in range(1, 4) for y in range(1, 4) for z in range(1, 4)]
        e = engine(grid_with(cells, mat=1), amp=0.2, gravity=False, height=0.05, freq=2.0)
        spans = []
        for s in range(int(1.0 / e.default_timestep)):
            e.step()
            if s > int(0.5 / e.default_timestep):
                p = e.data.xpos[1:]
                spans.append([p[:, a].max() - p[:, a].min() for a in range(3)])
        spans = np.array(spans) / (2 * L) - 1
        for a in range(3):
            self.assertAlmostEqual(spans[:, a].max(), 0.2, delta=0.004)
            self.assertAlmostEqual(spans[:, a].min(), -0.2, delta=0.004)

    def test_opposite_phases_cancel_in_shared_bond(self):
        """Voxelyze: a bond's rest length uses the MEAN of its voxels' strains, so a bond between
        the two muscle phases never changes length (the old tendon model gave it full stroke)."""
        e = engine(grid_with([(1, 1, 1)], 1) + grid_with([(2, 1, 1)], 2), amp=0.2, gravity=False)
        for t in np.linspace(0, 0.1, 11):
            s = e.voxel_strain(t)
            self.assertAlmostEqual(0.5 * (s[0] + s[1]), 0.0, places=12)

    def test_floor_contact_size_follows_strain(self):
        e = engine(grid_with([(1, 1, 1)], 1), amp=0.2)
        for _ in range(7):
            t0 = e.current_time
            e.step()
            expect = L / 2 * (1 + 0.2 * np.sin(2 * np.pi * 10 * t0))
            self.assertAlmostEqual(e.model.geom_size[e._floor_geom[0], 0], expect, places=12)


class TestForceProperties(unittest.TestCase):
    def block(self):
        cells = [(x, y, z) for x in range(2) for y in range(2) for z in range(2)]
        return engine(grid_with(cells), gravity=False, height=0.05)

    def test_rigid_motion_gives_no_internal_force(self):
        e = self.block()
        rng = np.random.default_rng(0)
        # rigid rotation of the whole block by a random quaternion about its centre
        axis = rng.normal(size=3); axis /= np.linalg.norm(axis); ang = 0.7
        qr = np.array([np.cos(ang / 2), *(np.sin(ang / 2) * axis)])
        Rr = np.zeros(9); mujoco.mju_quat2Mat(Rr, qr); Rr = Rr.reshape(3, 3)
        qpos = e.data.qpos.reshape(-1, 7)
        c = qpos[:, :3].mean(0)
        qpos[:, :3] = (qpos[:, :3] - c) @ Rr.T + c
        for k in range(len(qpos)):
            out = np.zeros(4); mujoco.mju_mulQuat(out, qr, qpos[k, 3:]); qpos[k, 3:] = out
        # rigid velocity field: v = V + W x (x - c), angular velocity W (local frame for free joints)
        V, W = np.array([0.03, -0.02, 0.01]), np.array([0.4, -0.3, 0.2])
        qvel = e.data.qvel.reshape(-1, 6)
        for k in range(len(qvel)):
            qvel[k, :3] = V + np.cross(W, qpos[k, :3] - c)
            Rk = np.zeros(9); mujoco.mju_quat2Mat(Rk, qpos[k, 3:]); qvel[k, 3:] = Rk.reshape(3, 3).T @ W
        mujoco.mj_forward(e.model, e.data)
        F, T = e.forces(np.zeros(len(e.cells)))
        # only global damping may act: -g*v (and -g_rot*w); bond + collision forces must vanish
        F_int = F + e.g_lin[:, None] * e.data.cvel[1:, 3:]
        T_int = T + e.g_rot[:, None] * e.data.cvel[1:, :3]
        scale = e.K_ax.max() * L * 1e-3                 # force of a 0.1% strain
        self.assertLess(np.abs(F_int).max(), 1e-6 * scale / 1e-3)
        self.assertLess(np.abs(T_int).max(), 1e-6 * scale * L / 1e-3)

    def test_stiffness_forces_balance(self):
        """Bond stiffness forces are internal: they sum to zero force and zero torque."""
        e = self.block()
        rng = np.random.default_rng(1)
        e.data.qpos.reshape(-1, 7)[:, :3] += rng.normal(scale=2e-4, size=(len(e.cells), 3))
        mujoco.mj_forward(e.model, e.data)
        F, T = e.forces(np.zeros(len(e.cells)))        # zero velocity -> no damping terms
        p = e.data.xpos[1:]
        self.assertLess(np.abs(F.sum(0)).max(), 1e-12)
        total_torque = T.sum(0) + np.cross(p, F).sum(0)
        self.assertLess(np.abs(total_torque).max(), 1e-9)

    def test_global_damping_decay(self):
        """A lone voxel coasting in zero gravity slows at rate zeta_g*2*sqrt(E*L/m) (Voxelyze)."""
        e = engine(grid_with([(1, 1, 1)]), gravity=False, height=0.05)
        e.data.qvel[0] = 0.1
        mujoco.mj_forward(e.model, e.data)
        T = 0.2
        for _ in range(int(T / e.default_timestep)):
            e.step()
        rate = ZETA_GLOBAL * 2 * np.sqrt(e_scaled(3) * L / e._m)
        self.assertAlmostEqual(e.data.qvel[0] / (0.1 * np.exp(-rate * T)), 1.0, delta=0.01)


class TestCollisions(unittest.TestCase):
    def u_shape(self):
        # two 1x1x8 arms along z, two voxels apart in x, joined by a 3-voxel bridge at the bottom
        cells = [(1, 1, 1), (2, 1, 1), (3, 1, 1)] + [(1, 1, z) for z in range(2, 9)] + [(3, 1, z) for z in range(2, 9)]
        return engine(grid_with(cells), gravity=False, height=0.05), cells

    def test_exclusions_follow_bond_distance(self):
        e, cells = self.u_shape()
        idx = {c: k for k, c in enumerate(e.cells)}
        a, b = idx[(1, 1, 2)], idx[(3, 1, 2)]            # 4 bonds apart via the bridge -> excluded
        self.assertIn((min(a, b), max(a, b)), e.excluded)
        a, b = idx[(1, 1, 5)], idx[(3, 1, 5)]            # 10 bonds apart -> may collide
        self.assertNotIn((min(a, b), max(a, b)), e.excluded)
        self.assertEqual(COLLISION_DEPTH, 5)

    def test_interior_voxels_are_not_surface(self):
        cells = [(x, y, z) for x in range(3) for y in range(3) for z in range(3)]
        e = engine(grid_with(cells), gravity=False)
        k = {c: i for i, c in enumerate(e.cells)}[(1, 1, 1)]
        self.assertFalse(e.surface[k])
        self.assertEqual(int(e.surface.sum()), 26)

    def test_collision_force_value(self):
        """Squeeze the two arm tips closer than 0.625*(L+L): repulsion = series(2EL,2EL)*overlap."""
        e, cells = self.u_shape()
        idx = {c: k for k, c in enumerate(e.cells)}
        a, b = idx[(1, 1, 8)], idx[(3, 1, 8)]
        qpos = e.data.qpos.reshape(-1, 7)
        gap = 1.1 * L                                      # nominal contact distance is 1.25 L
        mid = 0.5 * (qpos[a, :3] + qpos[b, :3])
        qpos[a, :3] = mid - [gap / 2, 0, 0]; qpos[b, :3] = mid + [gap / 2, 0, 0]
        mujoco.mj_forward(e.model, e.data)
        e._watch = None                                    # force a watch-list rebuild
        f = e._collision_forces(e.data.xpos[1:], np.zeros((len(e.cells), 3)), np.zeros(len(e.cells)))
        k = 2 * e_scaled(3) * L
        self.assertAlmostEqual(f[b, 0], k * (ENVELOPE_RADIUS * 2 * L - gap), delta=1e-9)
        self.assertAlmostEqual(f[a, 0], -f[b, 0], delta=1e-12)


class TestTimeStepAndStability(unittest.TestCase):
    def test_bone_needs_10x_smaller_step(self):
        """Every rate in the step estimate scales with sqrt(E), so bone (100x E) needs exactly
        10x smaller steps. Compared below the 0.5 ms cap (frac 0.01), which thin soft bodies hit."""
        chain = [(i, 1, 1) for i in range(6)]
        soft = engine(grid_with(chain, 3)).stable_dt(0.01)
        bone = engine(grid_with(chain, 4)).stable_dt(0.01)
        self.assertAlmostEqual(soft / bone, 10.0, places=6)

    def test_step_is_capped_at_half_a_millisecond(self):
        self.assertLessEqual(engine(grid_with([(i, 1, 1) for i in range(6)], 3)).default_timestep, 0.0005)

    def test_champion_body_runs_finite(self):
        """The beam pilot's champion - a body evolved under this engine - must run clean on the
        defaults. (cheney_floor_s1's champion, evolved under the spring model, does NOT: see
        TestDivergenceGuard.)"""
        path = os.path.join(ROOT, 'results', 'cheney_beam_s1', 'best_robot.pkl')
        if not os.path.exists(path):
            self.skipTest('champion file not present')
        with open(path, 'rb') as fh:
            g = pickle.load(fh)['genome']
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(g)
        for _ in range(int(0.3 / e.default_timestep)):
            e.step()
        self.assertFalse(e.diverged())
        self.assertTrue(np.all(np.isfinite(e.data.qpos)) and np.all(np.isfinite(e.data.qvel)))
        self.assertLess(np.abs(e.data.qvel).max(), 100.0)


class TestInterface(unittest.TestCase):
    def test_get_fitness_and_descriptors(self):
        cells = [(x, y, 1) for x in range(4) for y in range(2)]
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(grid_with(cells, 1) + grid_with([(0, 0, 2)], 3))
        f, desc = e.get_fitness(simulation_time=0.3, settle_time=0.1, return_descriptors=True)
        self.assertTrue(np.isfinite(f) and len(desc) == 2 and all(np.isfinite(desc)))

    def test_body_without_muscle_scores_zero(self):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(grid_with([(x, 1, 1) for x in range(4)], 3))
        self.assertEqual(e.get_fitness(simulation_time=0.2, settle_time=0.1), 0.0)

    def test_rejects_unsupported_modes(self):
        with self.assertRaises(ValueError):
            MuJoCoBeamPhysics(fitness_mode='efficiency')
        with self.assertRaises(ValueError):
            MuJoCoBeamPhysics(phase_mode='bogus')

    def test_series_modulus(self):
        self.assertAlmostEqual(bond_modulus(3, 3), e_scaled(3))
        self.assertAlmostEqual(bond_modulus(3, 4), 2 * e_scaled(3) * e_scaled(4) / (e_scaled(3) + e_scaled(4)))

    def test_stickslip_floor_switches(self):
        fr = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
        e = engine(grid_with([(1, 1, 1), (2, 1, 1)], 1), amp=0.0, friction=fr)
        self.assertTrue(np.allclose(e.model.pair_friction[:, 0], 1.0))
        e.data.qvel.reshape(-1, 6)[:, 0] = 0.5              # both voxels sliding fast
        e.step()
        self.assertTrue(np.allclose(e.model.pair_friction[:, 0], 0.5))


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

    def test_voxelyze_rule_is_the_larger_step_on_solid_bodies(self):
        """On the bodies we actually evolve, 'ours' is limited by the bond DAMPING rate summed
        over a voxel's six bonds, which Voxelyze's rule ignores; the Voxelyze step is then 1.6x
        larger. On a thin chain (two bonds, and the 0.5 ms cap) the ordering reverses, so the
        rule is not uniformly looser - which is why it is validated per body, not assumed."""
        block = [(x, y, z) for x in range(4) for y in range(4) for z in range(4)]
        for mat in (3, 4):
            vx = engine(grid_with(block, mat), dt_rule='voxelyze').stable_dt()
            ours = engine(grid_with(block, mat), dt_rule='ours').stable_dt()
            self.assertAlmostEqual(vx / ours, 1.60, delta=0.01, msg=f"mat {mat}")
        self.assertLess(self.chain(4, dt_rule='voxelyze').stable_dt(),
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


class TestDivergenceGuard(unittest.TestCase):
    """The volumetric law is nonlinear in compression and a body that crushes itself runs
    away (structurally - it is unchanged at 1/16 of the time step). Such a run must score
    nothing rather than whatever MuJoCo produces after it clamps the acceleration."""

    def test_a_healthy_body_is_not_flagged(self):
        e = engine(grid_with([(x, y, 1) for x in range(4) for y in range(3)], 1), amp=0.2)
        for _ in range(int(0.2 / e.default_timestep)):
            e.step()
        self.assertFalse(e.diverged())

    def test_a_blown_up_run_scores_zero(self):
        path = os.path.join(ROOT, 'results', 'cheney_floor_s1', 'best_robot.pkl')
        if not os.path.exists(path):
            self.skipTest('reference body not present')
        with open(path, 'rb') as fh:
            g = pickle.load(fh)['genome']
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(g)
        f, desc = e.get_fitness(simulation_time=0.5, settle_time=0.1, return_descriptors=True)
        self.assertTrue(e.diverged())
        self.assertEqual(f, 0.0)
        self.assertEqual(desc, (0.0, 0.0))

    def test_the_counter_is_clear_for_each_new_body(self):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, fitness_mode='forward')
        e.load_robot(grid_with([(x, y, 1) for x in range(4) for y in range(3)], 1))
        e.data.qvel[:] = np.nan
        e.step()
        self.assertTrue(e.diverged())
        e.load_robot(grid_with([(x, y, 1) for x in range(4) for y in range(3)], 1))
        self.assertFalse(e.diverged())


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
        e = engine(grid_with([(1, 1, 1), (2, 1, 1)]), materials='cheney2013', gravity_acc=3.71)
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


class TestFloorContact(unittest.TestCase):
    """--floor-contact voxelyze makes the floor HARD, because Voxelyze's penalty floor
    (k = 2*E*nomSize) is effectively hard at these loads - under 1% of a voxel of penetration.

    MuJoCo's softness is a TIME CONSTANT, not a stiffness, and its 20 ms default is comparable to a
    40 Hz actuation cycle (25 ms), so the contact never reaches equilibrium and bodies sink into the
    floor while walking. A negative solref pair does NOT set (stiffness, damping) in N/m - those act
    in acceleration space - which is why the first version of this was 14x too soft."""

    BLOCK = [(x, y, z) for x in range(3) for y in range(3) for z in range(8)]

    def sink(self, **kw):
        e = engine(grid_with(self.BLOCK, 3), **kw)
        for _ in range(int(1.0 / e.default_timestep)):
            e.step()
        z = np.array(e.data.xpos[1:e.model.nbody, 2])
        return e, (e.voxel_size / 2 - float(z.min())) / e.voxel_size    # penetration in voxels

    def test_default_is_unchanged(self):
        e = engine(grid_with([(1, 1, 1), (2, 1, 1)]))
        self.assertEqual(e.floor_contact, 'mujoco')
        pid = mujoco.mj_name2id(e.model, mujoco.mjtObj.mjOBJ_PAIR, 'floorpair_0')
        self.assertGreater(e.model.pair_solref[pid, 0], 0.0)          # timeconst form, untouched

    def test_time_constant_is_short_and_still_stable(self):
        """Short enough to be a small slice of an actuation cycle, never under MuJoCo's stability
        floor of two time steps."""
        for grid, mats in ((grid_with([(1, 1, 1), (2, 1, 1)]), 'evosoro'),
                           (grid_with(self.BLOCK, 3), 'cheney2013')):
            e = engine(grid, materials=mats, floor_contact='voxelyze')
            pid = mujoco.mj_name2id(e.model, mujoco.mjtObj.mjOBJ_PAIR, 'floorpair_0')
            tc = float(e.model.pair_solref[pid, 0])
            self.assertGreaterEqual(tc, 2.0 * e.default_timestep, msg=mats)
            # 0.5 ms unless the body's own time step forces a larger one (stability wins)
            self.assertAlmostEqual(tc, max(5e-4, 2.5 * e.default_timestep), places=9, msg=mats)
            self.assertEqual(float(e.model.pair_solref[pid, 1]), 1.0)   # critically damped
        # a body stiff enough to run at 40 Hz gets a step small enough for the short constant
        e = engine(grid_with(self.BLOCK, 3), materials='cheney2013', floor_contact='voxelyze')
        pid = mujoco.mj_name2id(e.model, mujoco.mjtObj.mjOBJ_PAIR, 'floorpair_0')
        self.assertLessEqual(float(e.model.pair_solref[pid, 0]), 0.02 / 40)

    def test_it_is_stiffer_than_voxelyzes_own_spring(self):
        """Voxelyze's floor would sink F/k under a load; ours must sink no more than that."""
        e, pen = self.sink(floor_contact='voxelyze')
        predicted = 8 * e._m * e.g_acc / e._kpen.min() / e.voxel_size
        self.assertLessEqual(pen, predicted)

    def test_it_stops_bodies_sinking_through_the_floor(self):
        """MuJoCo's default lets a body sink far into the floor once gravity is raised."""
        _, soft = self.sink(materials='cheney2013')
        _, stiff = self.sink(materials='cheney2013', floor_contact='voxelyze')
        self.assertGreater(soft, 1.0)              # more than a whole voxel under
        self.assertLess(stiff, 0.1)                # under a tenth of a voxel
        self.assertLess(stiff, soft / 10)

    def test_a_walking_body_stays_on_top_of_the_floor(self):
        """The failure this was built for: a 40 Hz gait sank 1.6 voxels into MuJoCo's default
        contact, and the distance it 'won' that way reversed sign once the floor was fixed."""
        g = grid_with([(x, y, z) for x in range(4) for y in range(3) for z in range(3)], 1)
        worst = {}
        for floor in ('mujoco', 'voxelyze'):
            e = engine(g, amp=0.2, freq=40.0, materials='cheney2013', floor_contact=floor,
                       friction={'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5,
                                 'v_on': 0.02, 'v_off': 0.01})
            r, nb, deep = e.voxel_size / 2, e.model.nbody, 0.0
            for _ in range(int(0.25 / e.default_timestep)):
                e.step()
                deep = max(deep, (r - float(e.data.xpos[1:nb, 2].min())) / e.voxel_size)
            worst[floor] = deep
            self.assertFalse(e.diverged(), msg=floor)
        self.assertLess(worst['voxelyze'], 0.25)
        self.assertLess(worst['voxelyze'], worst['mujoco'])

    def test_rejects_an_unknown_floor(self):
        with self.assertRaises(ValueError):
            MuJoCoBeamPhysics(floor_contact='penalty')


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


if __name__ == '__main__':
    unittest.main()


class TestCheneyScore(unittest.TestCase):
    """--direction any / --divide-by workspace: Cheney 2013's score, |COM_end - COM_start| as a 3D
    vector length (Voxelyze's FinalCOM_Dist) over a FIXED workspace width (BoundingBoxLength x
    VoxelSize), next to our default +X distance over the body's own length.

    The test robot is 5 voxels long with a foot at each end; it walks about 3 voxels in 10 cycles
    at 40 Hz, and its mirror image walks the other way."""

    FR = {'mode': 'stickslip', 'mu_s': 1.0, 'mu_k': 0.5, 'v_on': 0.02, 'v_off': 0.01}
    LEGS = [((x, y, z), 1 if x < 2 else 2) for x in range(5) for y in range(3) for z in range(3)
            if z > 0 or x in (0, 4)]
    W = 10
    CHENEY = dict(direction='any', divide_by='workspace', workspace_voxels=10)
    NO_ET = dict(early_term_threshold=-1e9)

    def body(self, mirror=False):
        g = np.zeros((20, 20, 20), np.int8)
        for (x, y, z), m in self.LEGS:
            g[(4 - x if mirror else x, y, z)] = m
        return g

    def eng(self, mirror=False, **kw):
        e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                              fitness_mode='forward', friction=self.FR, materials='cheney2013',
                              floor_contact='voxelyze', **kw)
        e.load_robot(self.body(mirror))
        return e

    def score(self, mirror=False, et=None, **kw):
        return float(self.eng(mirror, **kw).get_fitness(0.25, 0.0, **(et or self.NO_ET)))

    def test_defaults_are_unchanged(self):
        e = MuJoCoBeamPhysics()
        self.assertEqual((e.direction, e.divide_by, e.workspace_voxels), ('forward', 'body', None))
        self.assertEqual(self.score(), self.score(direction='forward', divide_by='body'))

    def test_the_divisor_is_exactly_the_workspace_width(self):
        """Same +X distance in a different unit: a 5-voxel body's score in workspace widths is
        its body-length score x 5/10, i.e. the 10/L bonus removed."""
        bl = self.score()
        w = self.score(divide_by='workspace', workspace_voxels=self.W)
        self.assertGreater(bl, 0.3)
        self.assertAlmostEqual(w, bl * 5 / self.W, places=12)

    def test_any_direction_is_the_3d_com_displacement(self):
        e = self.eng()
        c0 = np.array(e.get_position())
        for _ in range(int(0.25 / e.default_timestep)):
            e.step()
        d = (np.array(e.get_position()) - c0) / (self.W * e.voxel_size)
        self.assertAlmostEqual(self.score(**self.CHENEY), float(np.linalg.norm(d)), places=12)
        self.assertGreater(float(np.linalg.norm(d)), float(np.linalg.norm(d[:2])))   # vertical counts

    def test_a_backward_walker_now_scores(self):
        """The mirror image walks -X: nothing on the forward score, about what the original
        gets on Cheney's (the engine is left-right symmetric to a few per cent)."""
        self.assertEqual(self.score(mirror=True), 0.0)
        fwd, back = self.score(**self.CHENEY), self.score(mirror=True, **self.CHENEY)
        self.assertGreater(back, 0.25)
        self.assertAlmostEqual(back / fwd, 1.0, delta=0.05)

    def test_early_termination_is_in_the_score_unit(self):
        """--early-term-bl is compared with the score itself, in its own unit. With a threshold
        between the half-way progress in workspace widths (p) and in body lengths (2p, the body is
        half the workspace), the workspace score stops early with exactly p while the body-length
        score runs to the end."""
        e = self.eng()
        x0 = float(e.get_position()[0])
        for _ in range(int(int(0.25 / e.default_timestep) * 0.5)):
            e.step()
        p = (float(e.get_position()[0]) - x0) / (self.W * e.voxel_size)
        self.assertGreater(p, 0.05)
        et = dict(early_term_threshold=1.5 * p, early_term_fraction=0.5)
        self.assertAlmostEqual(self.score(et=et, divide_by='workspace', workspace_voxels=self.W),
                               p, places=12)
        self.assertEqual(self.score(et=et), self.score())

    def test_rejects_bad_values(self):
        for kw in (dict(direction='backward'), dict(divide_by='grid'), dict(divide_by='workspace'),
                   dict(divide_by='workspace', workspace_voxels=0)):
            with self.assertRaises(ValueError, msg=kw):
                MuJoCoBeamPhysics(**kw)

    def test_the_springs_engine_takes_the_same_switches(self):
        from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
        e = MuJoCoTendonPhysics(**self.CHENEY)
        self.assertEqual((e.direction, e.divide_by, e.workspace_voxels), ('any', 'workspace', 10))

    def test_the_record_champion(self):
        """cheney_fix_s1's champion: unchanged on the defaults, and on Cheney's score it is
        10 voxels long and walks +X, so the two nearly agree."""
        path = os.path.join(ROOT, 'results', 'cheney_fix_s1', 'best_robot.pkl')
        if not os.path.exists(path):
            self.skipTest('record champion not present')
        with open(path, 'rb') as fh:
            g = pickle.load(fh)['genome']
        et = dict(early_term_threshold=0.02, early_term_fraction=0.5)
        out = []
        for kw in ({}, self.CHENEY):
            e = MuJoCoBeamPhysics(actuation_amplitude=0.2, actuation_frequency=40.0,
                                  fitness_mode='forward', friction=self.FR, materials='cheney2013',
                                  floor_contact='voxelyze', **kw)
            e.load_robot(g)
            out.append(f"{float(e.get_fitness(0.25, 0.0, **et)):.4f}")
        self.assertEqual(out, ["2.6118", "2.6149"])
