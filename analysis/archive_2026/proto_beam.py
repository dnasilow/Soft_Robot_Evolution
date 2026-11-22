"""Prototype A: Voxelyze-style bonds as soft MuJoCo welds (6-DOF elastic, beam-like).

Units / material scaling. Cheney's lab: 1 cm voxels, density 1e6 kg/m^3 (1 kg voxels), E = 5e6 Pa
(soft, muscle), 5e8 Pa (bone). Dynamics depend only on k/m (natural frequency) and m*g/k (sag), so
1 g voxels (density 1e3) with E scaled by 1e-3 behave identically. We use the scaled values.

Validation (Hiller & Lipson 2012 did the same): cantilever of N voxels, first voxel clamped, gravity
off, small tip force F.  Beam theory:  axial   dx = F*l/(E*A)
                                        bending dz = F*l^3/(3*E*I)   (l = (N-1)*L, A = L^2, I = L^4/12)
"""
import numpy as np
import mujoco

L = 0.01
RHO = 1000.0
E_CHENEY = {1: 5e6, 2: 5e6, 3: 5e6, 4: 5e8}
E_SCALE = RHO / 1e6


def e_bond(m1, m2):
    e1, e2 = E_CHENEY[m1] * E_SCALE, E_CHENEY[m2] * E_SCALE
    return 2 * e1 * e2 / (e1 + e2)            # springs in series (Voxelyze)


def build(grid, dt=0.0005, tc_scale=1.0, torquescale=1.0, zeta=1.0, clamp_first=False, gravity=True):
    cells = [tuple(c) for c in np.argwhere(grid != 0)]
    idx = {c: k for k, c in enumerate(cells)}
    m = RHO * L ** 3
    I = m * L * L / 6.0                         # Voxelyze voxel rotational inertia
    lo = np.min(cells, axis=0)
    x = ['<mujoco><option timestep="%g" gravity="0 0 %g" integrator="implicitfast"/>' % (dt, -9.81 if gravity else 0),
         '<worldbody><geom name="ground" type="plane" size="1 1 0.1"/>']
    for k, c in enumerate(cells):
        p = (np.array(c) - lo) * L + np.array([0, 0, L / 2])
        joint = '' if (clamp_first and k == 0) else '<freejoint/>'
        x.append(f'<body name="v{k}" pos="{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}">{joint}'
                 f'<inertial pos="0 0 0" mass="{m:.6g}" diaginertia="{I:.6g} {I:.6g} {I:.6g}"/>'
                 f'<geom type="sphere" size="{L/2}" contype="0" conaffinity="0" mass="0"/></body>')
    x.append('</worldbody><equality>')
    bonds = []
    for c, k in idx.items():
        for ax, off in enumerate(((1, 0, 0), (0, 1, 0), (0, 0, 1))):
            nb = (c[0] + off[0], c[1] + off[1], c[2] + off[2])
            if nb not in idx:
                continue
            j = idx[nb]
            E = e_bond(int(grid[c]), int(grid[nb]))
            k_phys = E * L                       # Voxelyze a1 = b1 = E*L (axial = transverse)
            m_eff = m / 2.0                      # relative motion of two equal free masses
            tc = tc_scale / np.sqrt(k_phys / m_eff)
            h = np.array(off, float) * L / 2
            x.append(f'<weld body1="v{k}" body2="v{j}" relpose="{h[0]:.6f} {h[1]:.6f} {h[2]:.6f} 1 0 0 0" '
                     f'anchor="{-h[0]:.6f} {-h[1]:.6f} {-h[2]:.6f}" solref="{tc:.6g} {zeta}" '
                     f'torquescale="{torquescale}"/>')
            bonds.append((k, j, ax, tc))
    x.append('</equality></mujoco>')
    return '\n'.join(x), cells, bonds


def cantilever(N=10, mat=3, F=None, test='bend', **kw):
    g = np.zeros((20, 3, 3), np.int8); g[0:N, 1, 1] = mat
    xml, cells, bonds = build(g, clamp_first=True, gravity=False, **kw)
    mdl = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(mdl)
    E = E_CHENEY[mat] * E_SCALE; A = L * L; Ib = L ** 4 / 12; l = (N - 1) * L
    if F is None:                                # small force: 1% strain axial / ~0.5*L tip deflection
        F = 0.01 * E * A if test == 'axial' else 0.05 * 3 * E * Ib / l ** 3 * L * 10
    tip = mdl.nbody - 1
    p0 = np.array(d.xpos[tip]); mujoco.mj_forward(mdl, d); p0 = np.array(d.xpos[tip])
    for s in range(int(1.5 / mdl.opt.timestep)):
        d.xfrc_applied[tip, :3] = [F, 0, 0] if test == 'axial' else [0, 0, -F]
        mujoco.mj_step(mdl, d)
    disp = d.xpos[tip] - p0
    if test == 'axial':
        return disp[0], F * l / (E * A)
    return -disp[2], F * l ** 3 / (3 * E * Ib)


if __name__ == '__main__':
    import time
    print("A (weld beam) cantilever, soft material, N voxels, clamped at voxel 0, gravity off")
    print(f"{'N':>3} {'test':>6} {'tc_scale':>8} {'torqsc':>7} {'sim':>10} {'theory':>10} {'ratio':>6}")
    for N in (5, 10):
        for test in ('axial', 'bend'):
            for tcs, ts in ((1.0, 1.0),):
                t0 = time.time()
                sim, th = cantilever(N, test=test, tc_scale=tcs, torquescale=ts)
                print(f"{N:>3} {test:>6} {tcs:>8} {ts:>7} {sim*1e3:>8.4f}mm {th*1e3:>8.4f}mm {sim/th:>6.2f}")
