"""PARKED (2026-09-17) -- model B of the physics rework, kept for reference; not used by the pipeline.

Status: built and validated side by side with model A (src/physics/mujoco_beam_physics.py, adopted).
Parked because a spring lattice one voxel thick is too stiff for thin limbs, which are the point:
cantilever of 10 bone voxels vs Euler-Bernoulli theory -> axial 0.985, BENDING 0.544 (1.8x too stiff),
TWIST 0.278 (3.6x too stiff). Alternative spring layouts were worse (edges + body diagonals: bending
0.42, twist 31x too soft; all three kinds: bending 0.45, twist 0.55). Muscles exact (+/-0.198 at 20%).
~2x faster than A (0.73-1.08 ms/step at 0.157 ms on 485-810 voxel champions), no self-collision yet.
Run standalone:  python prototypes/truss_body_B.py   (cantilever tests)
"""
"""Prototype B: corner-node mass-spring voxels (Evolution-Gym style cross-bracing, in 3D).

Each voxel is a cube of 8 corner NODES (shared with neighbouring voxels). Node = body with 3 slide
joints (no rotation); mass = m/8 from every voxel that owns it. Each voxel contributes its own springs
between its corners: 12 edges (k_e = 0.1*E*L) + 12 face diagonals (k_f = 0.2*E*L). For a periodic
lattice this gives C11 = 1.2E, C12 = C44 = 0.4E, i.e. isotropic with Young's modulus E and Poisson 0.25
(central springs obey the Cauchy relation, so 0.25 is the best a spring lattice can do; Cheney 0.35).
Shared springs (same node pair) are merged: stiffness summed, rest length = stiffness-weighted mean of
each owning voxel's actuated rest length -> volumetric actuation L0*(1 + s_voxel), Voxelyze-consistent.
Damping 2*zeta*sqrt(m_node*K), zeta = 1. Forces explicit via xfrc_applied (mj_step1/mj_step2).
"""
import numpy as np
import mujoco

L, RHO, ZETA = 0.01, 1000.0, 1.0
E_CHENEY = {1: 5e6, 2: 5e6, 3: 5e6, 4: 5e8}
E_SCALE = RHO / 1e6
K_EDGE, K_FACE, K_BODY = 0.1, 0.2, 0.0   # isotropy (nu=0.25): 4k_e = 2k_f + (8/3)k_b, 2k_f + (4/3)k_b = 0.4
CORNERS = np.array([(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)])


class TrussBody:
    def __init__(self, grid, dt=0.0005, gravity=True, amp=0.0, freq=10.0, clamp_x0=False, node_r=None):
        cells = np.argwhere(grid != 0)
        mats = np.array([int(grid[tuple(c)]) for c in cells])
        lo = cells.min(0)
        nid = {}
        vox_nodes = np.zeros((len(cells), 8), int)
        for v, c in enumerate(cells):
            for k, off in enumerate(CORNERS):
                key = tuple(c - lo + off)
                vox_nodes[v, k] = nid.setdefault(key, len(nid))
        nodes = np.zeros((len(nid), 3)); [nodes.__setitem__(i, np.array(k) * L) for k, i in nid.items()]
        m = RHO * L ** 3
        nmass = np.zeros(len(nid)); np.add.at(nmass, vox_nodes.ravel(), m / 8)
        # per-voxel springs between its corners: edges (differ in 1 coord) + face diagonals (differ in 2)
        pairs = [(a, b) for a in range(8) for b in range(a + 1, 8)]
        kinds = [int(np.abs(CORNERS[a] - CORNERS[b]).sum()) for a, b in pairs]
        spring_id, S_i, S_j, S_l0 = {}, [], [], []
        W_rows, W_cols, W_vals = [], [], []                     # spring x voxel stiffness weights
        for v in range(len(cells)):
            E = E_CHENEY[mats[v]] * E_SCALE
            for (a, b), kind in zip(pairs, kinds):
                kval = {1: K_EDGE, 2: K_FACE, 3: K_BODY}[kind]
                if kval == 0:
                    continue
                na, nb = vox_nodes[v, a], vox_nodes[v, b]
                key = (min(na, nb), max(na, nb))
                if key not in spring_id:
                    spring_id[key] = len(S_i); S_i.append(key[0]); S_j.append(key[1])
                    S_l0.append(np.linalg.norm(nodes[key[1]] - nodes[key[0]]))
                W_rows.append(spring_id[key]); W_cols.append(v)
                W_vals.append(kval * E * L)
        self.si, self.sj, self.l0 = np.array(S_i), np.array(S_j), np.array(S_l0)
        ns = len(S_i)
        self.K = np.bincount(W_rows, W_vals, ns)
        # fraction of each spring's stiffness owned by each voxel (for actuated rest length)
        self.W = (np.array(W_rows), np.array(W_cols), np.array(W_vals) / self.K[W_rows])
        mr = np.minimum(nmass[self.si], nmass[self.sj])
        self.C = 2 * ZETA * np.sqrt(mr * self.K)
        self.vamp = np.where(np.isin(mats, (1, 2)), amp, 0.0)
        self.vph = np.where(mats == 2, np.pi, 0.0)
        self.omega, self.nmass, self.nn, self.ns = 2 * np.pi * freq, nmass, len(nid), ns
        r = node_r if node_r is not None else 0.1 * L
        x = [f'<mujoco><option timestep="{dt}" gravity="0 0 {-9.81 if gravity else 0}"/>',
             '<worldbody><geom name="ground" type="plane" size="2 2 0.1" friction="0.7 0.005 0.0001"/>']
        self.fixed = np.zeros(len(nid), bool)
        for k in range(len(nid)):
            p = nodes[k] + np.array([0, 0, r])
            fixed = clamp_x0 and nodes[k][0] == 0
            self.fixed[k] = fixed
            joints = '' if fixed else ''.join(f'<joint type="slide" axis="{a}"/>' for a in ('1 0 0', '0 1 0', '0 0 1'))
            x.append(f'<body name="n{k}" pos="{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}">{joints}'
                     f'<geom type="sphere" size="{r}" mass="{nmass[k]:.6g}" contype="1" conaffinity="0" '
                     f'friction="0.6 0.005 0.0001"/></body>')
        x.append('</worldbody></mujoco>')
        self.model = mujoco.MjModel.from_xml_string('\n'.join(x))
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        self.t, self.ext, self.test_damp = 0.0, np.zeros((len(nid), 3)), 0.0
        self.nodes0 = nodes

    def stable_dt(self, frac=0.8):
        k = np.bincount(self.si, self.K, self.nn) + np.bincount(self.sj, self.K, self.nn)
        c = np.bincount(self.si, self.C, self.nn) + np.bincount(self.sj, self.C, self.nn)
        free = ~self.fixed
        return frac / max(np.sqrt((k / self.nmass)[free].max()), (c / self.nmass)[free].max())

    def forces(self):
        d = self.data
        p = d.xpos[1:]; v = d.cvel[1:, 3:]
        s = self.vamp * np.sin(self.omega * self.t + self.vph)
        r, c, w = self.W
        rest = self.l0 * (1 + np.bincount(r, w * s[c], self.ns))
        dvec = p[self.sj] - p[self.si]; ln = np.linalg.norm(dvec, axis=1)
        n = dvec / ln[:, None]
        rel_v = ((v[self.sj] - v[self.si]) * n).sum(1)
        f = (self.K * (ln - rest) + self.C * rel_v)[:, None] * n       # tension pulls i toward j
        F = np.stack([np.bincount(self.si, f[:, a], self.nn) - np.bincount(self.sj, f[:, a], self.nn)
                      for a in range(3)], 1)
        return F

    def step(self):
        mujoco.mj_step1(self.model, self.data)
        F = self.forces() + self.ext
        if self.test_damp:
            F -= self.test_damp * self.nmass[:, None] * self.data.cvel[1:, 3:]
        self.data.xfrc_applied[1:, :3] = F
        mujoco.mj_step2(self.model, self.data)
        self.t += self.model.opt.timestep


def cantilever(N=10, mat=3, test='bend', T=4.0, damp=30.0):
    g = np.zeros((20, 3, 3), np.int8); g[0:N, 1, 1] = mat
    b = TrussBody(g, gravity=False, clamp_x0=True); dt = b.stable_dt(); b.model.opt.timestep = dt
    b.test_damp = damp
    E = E_CHENEY[mat] * E_SCALE; A = L * L; Ib = L ** 4 / 12; l = N * L        # clamped face -> free face
    tipn = np.where(np.isclose(b.nodes0[:, 0], N * L))[0]
    p0 = b.data.xpos[1:][tipn].copy()
    if test == 'axial':
        F = 0.01 * E * A; b.ext[tipn, 0] = F / len(tipn); th = F * l / (E * A)
    elif test == 'bend':
        F = 1.5 * E * Ib / l ** 3 * L * 0.2; b.ext[tipn, 1] = F / len(tipn); th = F * l ** 3 / (3 * E * Ib)
    else:                                                      # torque about x as a force couple on tip nodes
        G = E / (2 * 1.25); J = 0.1406 * L ** 4; Tq = 0.02 * G * J / l
        ctr = b.nodes0[tipn].mean(0); rr = b.nodes0[tipn] - ctr
        for k, rv in zip(tipn, rr):
            b.ext[k] = Tq * np.cross([1, 0, 0], rv) / (len(tipn) * (rv @ rv))
        th = Tq * l / (G * J)
    for _ in range(int(T / dt)):
        b.step()
    dp = b.data.xpos[1:][tipn] - p0
    if test == 'axial':
        return dp[:, 0].mean(), th, dt
    if test == 'bend':
        return dp[:, 1].mean(), th, dt
    rr = b.nodes0[tipn] - b.nodes0[tipn].mean(0)
    ang = np.mean([np.cross(rv, dv)[0] / (rv @ rv) for rv, dv in zip(rr, dp)])
    return ang, th, dt


if __name__ == '__main__':
    import time
    print("B (corner-node truss) cantilever, clamped face at x=0, gravity off, static (test damping)")
    for mat, lab in ((3, 'soft'), (4, 'bone')):
        for N in (5, 10):
            for test in ('axial', 'bend', 'twist'):
                t0 = time.time(); sim, th, dt = cantilever(N, mat, test)
                print(f"  {lab} N={N:<2} {test:<5} ratio {sim/th:6.3f}   (dt {dt*1e3:.3f} ms, {time.time()-t0:.1f}s)")
