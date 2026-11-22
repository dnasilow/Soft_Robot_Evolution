"""Prototype A: Voxelyze's beam bonds applied as explicit forces (MuJoCo handles masses/contacts).

Each voxel = rigid body (free joint), mass m = rho*L^3, rotational inertia m*L^2/6 (Voxelyze).
Each face-adjacent pair = Euler-Bernoulli frame element, co-rotational. For small deformations the
element energy decomposes EXACTLY into
    1/2*K_ax*u_par^2 + 1/2*K_sh*|u_perp|^2 + 1/2*K_b*|phi_bend|^2 + 1/2*K_t*phi_twist^2
with u = mismatch between the two voxels' bond MIDPOINTS (each carried by its own voxel's pose) and
phi = relative rotation. Stiffnesses (Voxelyze VX_MaterialLink, square section side L):
    K_ax = E*L (a1)   K_sh = 12EI/L^3 = E*L (b1)   K_b = EI/L = E*L^3/12 (b3/2)   K_t = E*L^3/(12(1+nu)) (a2)
Damping: 2*zeta*sqrt(m*K) per mode, zeta = 1 (Voxelyze BondDampingZ = 1).
Volumetric actuation: bond rest length L*(1 + (s_i + s_j)/2)  (Hiller & Lipson eq. 40).
Material scaling: 1 g voxels with E x 1e-3 == Cheney's 1 kg voxels with E (same k/m and m*g/k).
"""
import numpy as np
import mujoco

L, RHO, NU, ZETA = 0.01, 1000.0, 0.35, 1.0
E_CHENEY = {1: 5e6, 2: 5e6, 3: 5e6, 4: 5e8}
E_SCALE = RHO / 1e6
AXES = np.eye(3)


def _qmul(a, b):
    w1, x1, y1, z1 = a.T; w2, x2, y2, z2 = b.T
    return np.stack([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2], 1)


def _rotvec(q):
    q = np.where(q[:, :1] < 0, -q, q)                       # shortest rotation
    v = q[:, 1:]; s = np.linalg.norm(v, axis=1, keepdims=True)
    ang = 2 * np.arctan2(s, q[:, :1])
    return np.where(s > 1e-12, v * ang / np.maximum(s, 1e-12), 2 * v)


class BeamBody:
    def __init__(self, grid, dt=0.0005, clamp_first=False, gravity=True, amp=0.0, freq=10.0):
        self.grid = grid
        cells = [tuple(c) for c in np.argwhere(grid != 0)]
        self.cells = cells
        idx = {c: k for k, c in enumerate(cells)}
        n = len(cells); m = RHO * L ** 3; I = m * L * L / 6
        self.m, self.I, self.n, self.amp, self.omega = m, I, n, amp, 2 * np.pi * freq
        lo = np.min(cells, axis=0)
        bi, bj, ba, E = [], [], [], []
        for c, k in idx.items():
            for a in range(3):
                nb = tuple(np.array(c) + AXES[a].astype(int))
                if nb in idx:
                    e1, e2 = E_CHENEY[int(grid[c])] * E_SCALE, E_CHENEY[int(grid[nb])] * E_SCALE
                    bi.append(k); bj.append(idx[nb]); ba.append(a); E.append(2 * e1 * e2 / (e1 + e2))
        self.bi, self.bj, self.ba = np.array(bi), np.array(bj), np.array(ba)
        E = np.array(E)
        self.Kax = E * L; self.Ksh = E * L; self.Kb = E * L ** 3 / 12; self.Kt = E * L ** 3 / (12 * (1 + NU))
        self.Cax = 2 * ZETA * np.sqrt(m * self.Kax); self.Csh = 2 * ZETA * np.sqrt(m * self.Ksh)
        self.Cb = 2 * ZETA * np.sqrt(I * self.Kb); self.Ct = 2 * ZETA * np.sqrt(I * self.Kt)
        self.ea = AXES[self.ba]                                   # bond axis in voxel-local frame
        mats = np.array([int(grid[c]) for c in cells])
        self.vamp = np.where(np.isin(mats, (1, 2)), amp, 0.0)
        self.vph = np.where(mats == 2, np.pi, 0.0)
        # surface voxels collide (except bonded pairs); interior voxels never do
        occ = grid != 0
        def interior(c):
            return all(0 <= c[a] + s < grid.shape[a] and occ[tuple(np.array(c) + s * AXES[a].astype(int))]
                       for a in range(3) for s in (-1, 1))
        x = [f'<mujoco><option timestep="{dt}" gravity="0 0 {-9.81 if gravity else 0}"/>',
             '<worldbody><geom name="ground" type="plane" size="2 2 0.1" friction="0.7 0.005 0.0001"/>']
        for k, c in enumerate(cells):
            p = (np.array(c) - lo) * L + np.array([0, 0, L / 2])
            col = 'contype="0" conaffinity="0"' if interior(c) else 'contype="1" conaffinity="1"'
            joint = '' if (clamp_first and k == 0) else '<freejoint/>'
            x.append(f'<body name="v{k}" pos="{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}">{joint}'
                     f'<inertial pos="0 0 0" mass="{m:.6g}" diaginertia="{I:.6g} {I:.6g} {I:.6g}"/>'
                     f'<geom type="sphere" size="{L/2}" {col} mass="0" friction="0.6 0.005 0.0001"/></body>')
        x.append('</worldbody><contact>')
        for i, j in zip(self.bi, self.bj):
            x.append(f'<exclude body1="v{i}" body2="v{j}"/>')
        x.append('</contact></mujoco>')
        self.model = mujoco.MjModel.from_xml_string('\n'.join(x))
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        self.t = 0.0
        self.ext = np.zeros((n + 1, 6))                           # extra test loads (world frame)
        self.test_damp = 0.0                                      # static tests only: global drag rate (1/s)

    def stable_dt(self, frac=0.5):
        """Largest safe explicit timestep: per voxel, sum bond stiffness/damping acting on its
        translation (K) and rotation (Kb + Ksh*(L/2)^2 via the anchor lever arm); require
        omega*dt and damping-rate*dt below frac (explicit-integration margin)."""
        kt = np.zeros(self.n); kr = np.zeros(self.n); ct = np.zeros(self.n); cr = np.zeros(self.n)
        for arr, val in ((kt, self.Kax + self.Ksh), (kr, self.Kb + self.Ksh * (L / 2) ** 2),
                         (ct, self.Cax + self.Csh), (cr, self.Cb + self.Csh * (L / 2) ** 2)):
            np.add.at(arr, self.bi, val); np.add.at(arr, self.bj, val)
        rate = max(np.sqrt(kt.max() / self.m), np.sqrt(kr.max() / self.I), ct.max() / self.m, cr.max() / self.I)
        return frac / rate

    def forces(self):
        d = self.data
        p = d.xpos[1:]; R = d.xmat[1:].reshape(-1, 3, 3); q = d.xquat[1:]
        w = d.cvel[1:, :3]; v = d.cvel[1:, 3:]                   # world-frame angular / linear
        s = self.vamp * np.sin(self.omega * self.t + self.vph)
        rest = L * (1 + 0.5 * (s[self.bi] + s[self.bj]))
        i, j = self.bi, self.bj
        hi = np.einsum('bij,bj->bi', R[i], self.ea) * (rest / 2)[:, None]    # anchor offsets (world)
        hj = -np.einsum('bij,bj->bi', R[j], self.ea) * (rest / 2)[:, None]
        u = (p[j] + hj) - (p[i] + hi)                                          # midpoint mismatch
        nvec = (hi - hj); nvec /= np.linalg.norm(nvec, axis=1, keepdims=True)  # current bond axis
        du = (v[j] + np.cross(w[j], hj)) - (v[i] + np.cross(w[i], hi))
        upar = (u * nvec).sum(1, keepdims=True) * nvec; uper = u - upar
        dpar = (du * nvec).sum(1, keepdims=True) * nvec; dper = du - dpar
        Fj = -(self.Kax[:, None] * upar + self.Ksh[:, None] * uper
               + self.Cax[:, None] * dpar + self.Csh[:, None] * dper)
        # relative rotation of j w.r.t. i, in i's frame -> bend / twist components
        qi_conj = q[i] * np.array([1, -1, -1, -1])
        phi = _rotvec(_qmul(qi_conj, q[j]))
        tw = (phi * self.ea).sum(1, keepdims=True)
        tau_loc = -(self.Kb[:, None] * (phi - tw * self.ea) + self.Kt[:, None] * tw * self.ea)
        tau = np.einsum('bij,bj->bi', R[i], tau_loc)
        dw = w[j] - w[i]; dtw = (dw * nvec).sum(1, keepdims=True) * nvec
        tau -= self.Cb[:, None] * (dw - dtw) + self.Ct[:, None] * dtw
        n = self.n
        def scatter(vals_j, vals_i):
            return np.stack([np.bincount(j, vals_j[:, c], n) + np.bincount(i, vals_i[:, c], n) for c in range(3)], 1)
        F = scatter(Fj, -Fj)
        T = scatter(tau + np.cross(hj, Fj), -tau + np.cross(hi, -Fj))
        return F, T

    def step(self):
        # mj_step1 brings xpos/xquat/cvel up to date with the CURRENT qpos/qvel; after a plain
        # mj_step they still describe the previous state, and forces computed from one-step-old
        # positions act like negative damping on stiff modes (bending blew up that way).
        mujoco.mj_step1(self.model, self.data)
        F, T = self.forces()
        if self.test_damp:
            F -= self.test_damp * self.m * self.data.cvel[1:, 3:]
            T -= self.test_damp * self.I * self.data.cvel[1:, :3]
        self.data.xfrc_applied[1:, :3] = F + self.ext[1:, :3]
        self.data.xfrc_applied[1:, 3:] = T + self.ext[1:, 3:]
        mujoco.mj_step2(self.model, self.data)
        self.t += self.model.opt.timestep


def cantilever(N=10, mat=3, test='bend', dt=0.0005, T=4.0):
    g = np.zeros((20, 3, 3), np.int8); g[0:N, 1, 1] = mat
    b = BeamBody(g, dt=dt, clamp_first=True, gravity=False)
    b.test_damp = 30.0
    E = E_CHENEY[mat] * E_SCALE; A = L * L; Ib = L ** 4 / 12; l = (N - 1) * L
    tip = b.model.nbody - 1; p0 = np.array(b.data.xpos[tip])
    if test == 'axial':
        F = 0.01 * E * A; b.ext[tip, 0] = F; th = F * l / (E * A)
    elif test == 'bend':
        F = 1.5 * E * Ib / l ** 3 * L * 0.2; b.ext[tip, 1] = F; th = F * l ** 3 / (3 * E * Ib)   # sideways: the floor can't interfere
    else:                                                       # torsion: tip torque about x
        Tq = 0.02 * E * L ** 3 / (12 * (1 + NU)) / (N - 1); b.ext[tip, 3] = Tq
        th = Tq * (N - 1) / (E * L ** 3 / (12 * (1 + NU)))      # series of N-1 torsion springs
    for _ in range(int(T / dt)):
        b.step()
    if test == 'axial':
        return b.data.xpos[tip][0] - p0[0], th
    if test == 'bend':
        return b.data.xpos[tip][1] - p0[1], th
    return _rotvec(b.data.xquat[tip:tip + 1])[0, 0], th


if __name__ == '__main__':
    import time
    print("A (Voxelyze beam forces) cantilever, clamped at voxel 0, gravity off, static after 1.5 s")
    for mat, lab in ((3, 'soft'), (4, 'bone')):
        for N in (5, 10):
            for test in ('axial', 'bend', 'twist'):
                dt = 0.0005 if mat == 3 else 0.0001
                t0 = time.time(); sim, th = cantilever(N, mat, test, dt=dt)
                print(f"  {lab:<4} N={N:<2} {test:<5}  sim {sim:.5e}  theory {th:.5e}  ratio {sim/th:6.3f}"
                      f"   ({time.time()-t0:.1f}s, dt={dt})")
