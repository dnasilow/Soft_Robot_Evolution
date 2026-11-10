"""
MuJoCo engine with Voxelyze-style voxel bodies  (--body beam)

Reproduces the bond mechanics of Voxelyze, the simulator behind Cheney et al. 2013 (Hiller &
Lipson, "Dynamic Simulation of Soft Heterogeneous Objects"), inside MuJoCo, which keeps doing what
it is good at: rigid-body integration, floor contact and floor friction.

Voxel  = rigid body (free joint) at its centre: mass m = rho*L^3, rotational inertia m*L^2/6
         (Voxelyze VX_MaterialVoxel). Position AND orientation are simulated.
Bond   = every face-adjacent pair, an Euler-Bernoulli frame element (Voxelyze CVX_Link). Stiffness
         is applied as a co-rotational spring on the mismatch between the two voxels' bond MIDPOINTS
         (axial K_ax = E*L, transverse K_sh = 12EI/L^3 = E*L) plus a spring on their relative
         rotation (bending K_b = EI/L = E*L^3/12, twist K_t = E*L^3/(12(1+nu))). For small
         deformations this energy equals the frame element's exactly (validated against beam theory:
         axial, bending and twist of a cantilever all match to 0.1%).
Damping (Voxelyze, verbatim structure): bond damping in the bond's frame with coefficients
         zeta*sqrt(m)*sqrt(k) (VX_Link sqA1, sqB1, sqB2xFMp, sqB3xIp, sqA2xIp), zeta = 1
         (evosoro BondDampingZ); global "slow" damping zeta_g*2*sqrt(m*E*L) on every voxel's
         velocity (and 2*sqrt(I*E*L^3) on its spin), zeta_g = 0.01 (evosoro SlowDampingZ).
Muscles (volumetric, Hiller & Lipson eq. 40): voxel strain s = amp*sin(w*t + phase), phase 0 for
         material 1 and pi for material 2; a bond's rest length is L*(1 + (s_i + s_j)/2). A voxel's
         floor-contact size also follows its strain (Voxelyze floorPenetration uses baseSize).
Materials (evosoro defaults): E = 5 MPa soft, 5 MPa muscle, 500 MPa bone, density 1e6 kg/m^3,
         Poisson 0.35; bonds between materials use the series average 2*E1*E2/(E1+E2). We keep 1 g
         voxels (density 1e3) and scale E by 1e-3: dynamics depend only on k/m and m*g/k, so this is
         identical to Cheney's 1 kg voxels while keeping MuJoCo's contact model well scaled.
Contacts: floor = a sphere of radius L/2*(1+s) per voxel, via explicit floor pairs (so the
         --friction / stick-slip floors apply); floor response is MuJoCo's soft contact, not
         Voxelyze's penalty spring. Self-collision follows Voxelyze exactly (regenerateCollisions,
         CVX_Collision): SURFACE voxels only; never between two voxels within 5 bonds of each other
         (generateNearby(int(2*(2*0.75 + 1.0)))); contact when centres are closer than
         0.625*(size_i + size_j) (envelopeRadius, sizes include muscle expansion); normal force only,
         stiffness = series average of 2*E*L, damping 0.8*2*sqrt(m*E*L) (ColDampingZ), no friction.
         Computed here as forces over a watch list of candidate pairs (centres within 2.5*L, i.e.
         2*boundingRadius + watchDistance), rebuilt whenever a voxel has moved more than L/2 —
         MuJoCo's own collision pipeline spent ~4.5 ms/step sifting overlapping excluded pairs.
Poisson (volumetric coupling, Voxelyze CVX_Material::stress + CVX_Voxel::strain(true), on by
         default, `poisson=False` restores the uncoupled law used before 2026-09-22):
         a bond's axial force is stress x current transverse area rather than K_ax x extension,
         with stress = Ehat*((1-nu)*eps_axial + nu*(eps_t1 + eps_t2)) and Ehat = E/((1-2nu)(1+nu)).
         Each voxel's per-axis strain is the average of its bonds' shares of their axial strain
         (a bond splits its strain between its two voxels as 2*eps*r/(1+r) and 2*eps/(1+r), with
         r = E_pos/E_neg); an axis with fewer than two bonds is free to bulge instead and takes
         (1 + sum of the constrained strains)^(-nu) - 1. A free bar therefore still responds with
         E, while a voxel squeezed on all three axes responds with Ehat*(1-nu) = 1.6*E, and an
         expanding muscle inside a body pushes back that much harder and bulges its free faces.
Time step: explicit bond forces need dt below the fastest bond mode, so each robot gets its own dt.
         `dt_rule='voxelyze'` (default) is Voxelyze's own recommendedTimeStep: DtFrac 0.7 divided by
         2*pi*sqrt(k_axial_max / m_min), where k_axial is the link's axialStiffness (Ehat*L with
         Poisson on, E*L without). `dt_rule='ours'` is the older, ~1.6x more conservative estimate
         that also sums every bond on a voxel and includes damping rates. Both are capped at 0.5 ms.
         Robots with bone (100x stiffer) need ~10x more steps either way.

Forces are applied through xfrc_applied between mj_step1 and mj_step2: after a plain mj_step,
xpos/xquat/cvel still describe the PREVIOUS state, and bond forces computed from one-step-old
positions act as negative damping on the stiff modes.
"""
from collections import deque
from typing import Dict, Optional

import mujoco
import numpy as np

from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

E_CHENEY        = {1: 5e6, 2: 5e6, 3: 5e6, 4: 5e8}   # Pa, evosoro muscle/fat/bone stiffness
# Cheney 2013's OWN values, read from his .vxa files and hard-coded in
# HCUBE_SoftbotsExperiment.cpp: muscle and soft are both 1e7 Pa and the hard material is 5e7 --
# only 5x stiffer, not the 100x evosoro implies. Lattice 1 mm, gravity -27.468 m/s^2.
E_CHENEY_2013   = {1: 1e7, 2: 1e7, 3: 1e7, 4: 5e7}
LATTICE_CHENEY  = 1e-3                               # m, his Lattice_Dim
GRAVITY_CHENEY  = 27.468                             # m/s^2, his GravAcc (2.8 g; no stated reason)
DENSITY_CHENEY  = 1e6                                # kg/m^3, evosoro and Cheney
POISSON         = 0.35
EHAT            = 1.0 / ((1 - 2 * POISSON) * (1 + POISSON))   # Voxelyze _eHat = E/((1-2nu)(1+nu))
ZETA_BOND       = 1.0                                # evosoro BondDampingZ
ZETA_GLOBAL     = 0.01                               # evosoro SlowDampingZ
ZETA_COLLISION  = 0.8                                # evosoro ColDampingZ
RHO             = 1000.0                             # our voxel density -> 1 g at L = 1 cm
COLLISION_RADIUS = 0.75                              # Voxelyze boundingRadius (voxel units)
ENVELOPE_RADIUS  = 0.625                             # Voxelyze CVX_Collision envelopeRadius
WATCH_RADIUS     = 2 * COLLISION_RADIUS + 1.0         # voxel units (watchDistance = 1)
COLLISION_DEPTH  = int(2 * (2 * 0.75 + 1.0))         # Voxelyze nearby link depth = 5
DT_FRAC          = 0.8                               # safety margin, dt_rule='ours'
DT_FRAC_VX       = 0.7                               # evosoro DtFrac, dt_rule='voxelyze'
FLOOR_TIMECONST  = 5e-4                              # --floor-contact voxelyze: MuJoCo
#   contact time constant. 0.5 ms is 2% of a 40 Hz cycle and >= 25 time steps, which
#   keeps penetration at ~0.14 of a voxel while walking (MuJoCo's 20 ms default: 1.6).
_COLORS = {1: '0 1 0 1', 2: '1 0 0 1', 3: '0 1 1 1', 4: '0 0 1 1'}
_AXES = np.eye(3)


def _qmul(a, b):
    w1, x1, y1, z1 = a.T
    w2, x2, y2, z2 = b.T
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], 1)


def _rotvec(q):
    """Rotation vectors of unit quaternions (w, x, y, z), shortest rotation."""
    q = np.where(q[:, :1] < 0, -q, q)
    v = q[:, 1:]
    s = np.linalg.norm(v, axis=1, keepdims=True)
    ang = 2 * np.arctan2(s, q[:, :1])
    return np.where(s > 1e-12, v * ang / np.maximum(s, 1e-12), 2 * v)


def e_scaled(mat: int, materials: str = "evosoro", voxel_size: float = LATTICE_CHENEY) -> float:
    """Young's modulus rescaled for OUR voxels.

    The dynamics of a voxel lattice depend on E/(rho*L^2) (natural frequency) and rho*g*L/E
    (sag per voxel), so moving from Cheney's rho and L to ours requires
        E_ours = E_his * (rho_ours * L_ours^2) / (rho_his * L_his^2).

    The original 'evosoro' preset corrected only for density and silently assumed our lattice
    was still 1 mm; because ours is 10 mm, it left bodies 200x too soft (14x too floppy in
    frequency). 'cheney2013' applies the full correction, so mass, bond stiffness, natural
    frequency and sag per voxel all match his simulation exactly.
    """
    if materials == "evosoro":
        return E_CHENEY[mat] * RHO / DENSITY_CHENEY          # unchanged: pre-2026-09-24 runs
    return (E_CHENEY_2013[mat] * (RHO * voxel_size ** 2)
            / (DENSITY_CHENEY * LATTICE_CHENEY ** 2))


def gravity_scaled(materials: str = "evosoro", voxel_size: float = LATTICE_CHENEY) -> float:
    """Gravity that reproduces Cheney's sag per voxel on our lattice (rho*g*L/E invariant)."""
    if materials == "evosoro":
        return 9.81
    return GRAVITY_CHENEY * (LATTICE_CHENEY / voxel_size) * (
        e_scaled(1, materials, voxel_size) / E_CHENEY_2013[1]) * (DENSITY_CHENEY / RHO)


def bond_modulus(m1: int, m2: int, materials: str = "evosoro",
                 voxel_size: float = LATTICE_CHENEY) -> float:
    e1 = e_scaled(m1, materials, voxel_size)
    e2 = e_scaled(m2, materials, voxel_size)
    return 2 * e1 * e2 / (e1 + e2)                    # Voxelyze: springs in series


class MuJoCoBeamPhysics(MuJoCoTendonPhysics):
    """Voxelyze-style bodies. Same public interface as MuJoCoTendonPhysics (load_robot, step,
    get_fitness, get_position), so the evaluator and fitness code are shared."""

    def __init__(self, actuation_frequency: float = 10.0, actuation_amplitude: float = 0.2,
                 fitness_mode: str = "directed", max_voxels: Optional[int] = None,
                 friction: Optional[Dict] = None, dt_frac: Optional[float] = None,
                 default_timestep: Optional[float] = None, poisson: bool = True,
                 dt_rule: str = "voxelyze", materials: str = "evosoro",
                 gravity: Optional[float] = None, floor_contact: str = "mujoco",
                 phase_mode: str = "offset", direction: str = "forward",
                 divide_by: str = "body", workspace_voxels: Optional[int] = None):
        # default_timestep is accepted for interface compatibility but not used: each robot gets
        # its own stable step in load_robot (Voxelyze-style).
        super().__init__(default_timestep=0.0005, actuation_frequency=actuation_frequency,
                         actuation_amplitude=actuation_amplitude, fitness_mode=fitness_mode,
                         max_voxels=max_voxels, friction=friction, direction=direction,
                         divide_by=divide_by, workspace_voxels=workspace_voxels)
        if fitness_mode == "efficiency":
            raise ValueError("--fitness efficiency uses actuator effort; the beam body has no "
                             "actuators (its muscles change bond rest lengths)")
        if dt_rule not in ("voxelyze", "ours"):
            raise ValueError(f"dt_rule must be 'voxelyze' or 'ours', got {dt_rule!r}")
        if materials not in ("evosoro", "cheney2013"):
            raise ValueError(f"materials must be 'evosoro' or 'cheney2013', got {materials!r}")
        if phase_mode not in ("offset", "replace"):
            raise ValueError(f"phase_mode must be 'offset' or 'replace', got {phase_mode!r}")
        self.phase_mode = phase_mode
        if floor_contact not in ("mujoco", "voxelyze"):
            raise ValueError(f"floor_contact must be 'mujoco' or 'voxelyze', got {floor_contact!r}")
        self.floor_contact = floor_contact
        self.materials = materials
        self.gravity = gravity                # None = the preset's own value
        self.dt_frac = dt_frac                # None = the step rule's own default
        self.dt_rule = dt_rule
        self.poisson = bool(poisson)
        self.external = None          # optional (n, 6) extra world-frame force/torque (tests)
        self.test_damping = 0.0       # optional global drag rate for static tests only

    # ------------------------------------------------------------------
    def load_robot(self, voxel_grid: np.ndarray, voxel_size: float = 0.01,
                   initial_height: float = 0.0, gait_params=None, clamped=()) -> None:
        """Build the body. `clamped` (tests only): voxel indices fixed to the world."""
        # gait_params is applied at the end of load_robot, once the voxel list exists.
        L = self.voxel_size = float(voxel_size)
        cells = [tuple(int(v) for v in c) for c in np.argwhere(voxel_grid != 0)]
        if not cells:
            raise ValueError("No voxels in grid!")
        mats = np.array([int(voxel_grid[c]) for c in cells])
        self.cells, self.mats, n = cells, mats, len(cells)
        self._n_voxels = n
        self._n_actuated_voxels = int(np.isin(mats, (1, 2)).sum())
        idx = {c: k for k, c in enumerate(cells)}
        m = RHO * L ** 3
        I = m * L * L / 6.0
        self._m, self._I = m, I

        # ---- bonds (face-adjacent pairs, i = negative side, j = positive side) ----
        bi, bj, ba = [], [], []
        for c, k in idx.items():
            for a in range(3):
                nb = (c[0] + (a == 0), c[1] + (a == 1), c[2] + (a == 2))
                if nb in idx:
                    bi.append(k); bj.append(idx[nb]); ba.append(a)
        self.bi, self.bj, self.ba = np.array(bi, int), np.array(bj, int), np.array(ba, int)
        E = np.array([bond_modulus(mats[i], mats[j], self.materials, L)
                      for i, j in zip(bi, bj)])
        self.bE = E
        self.bEhat = E * EHAT                                 # Voxelyze CVX_Material::_eHat
        self.K_ax = E * L
        self.K_sh = E * L
        self.K_b = E * L ** 3 / 12.0
        self.K_t = E * L ** 3 / (12.0 * (1.0 + POISSON))
        # Voxelyze link damping coefficients (sqrt(k) with sqrt(m) factored out), times zeta*sqrt(m)
        zm = ZETA_BOND * np.sqrt(m)
        a2 = self.K_t
        self.d_A1 = zm * np.sqrt(E * L)                       # sqA1
        self.d_B1 = zm * np.sqrt(E * L)                       # sqB1
        self.d_B2 = zm * np.sqrt(E * L ** 2 / 2 * L / 2)      # sqB2xFMp = sqrt(b2*L/2)
        self.d_B3 = zm * np.sqrt(E * L ** 3 / 6 * L * L / 6)  # sqB3xIp  = sqrt(b3*L^2/6)
        self.d_A2 = zm * np.sqrt(a2 * L * L / 6)              # sqA2xIp  = sqrt(a2*L^2/6)
        self.ea = _AXES[self.ba]
        # cyclic permutation taking the bond axis to local x (a proper rotation)
        self._perm = np.stack([(self.ba + k) % 3 for k in range(3)], 1)
        self._iperm = np.argsort(self._perm, axis=1)
        # global damping per voxel (own material)
        Ev = np.array([e_scaled(v, self.materials, L) for v in mats])
        self.g_lin = ZETA_GLOBAL * 2 * np.sqrt(m * Ev * L)
        self.g_rot = ZETA_GLOBAL * 2 * np.sqrt(I * Ev * L ** 3)
        # ---- Poisson bookkeeping (Voxelyze CVX_Voxel::strain(true)) ----
        # An axis with a bond on BOTH sides is constrained by its neighbours ("tension" in
        # Voxelyze); any other axis is free to bulge. A voxel held to the world counts as
        # constrained on any axis it has a bond on (Voxelyze's ext->isFixed branch).
        nb_axis = np.zeros((n, 3), int)
        np.add.at(nb_axis, (self.bi, self.ba), 1)
        np.add.at(nb_axis, (self.bj, self.ba), 1)
        self._nb_axis = nb_axis
        fixed = np.zeros(n, bool)
        fixed[list(set(clamped))] = True
        self._tension = (nb_axis == 2) | (fixed[:, None] & (nb_axis == 1))
        self._half = np.where(nb_axis == 2, 0.5, 1.0)         # two bonds on an axis -> average
        # flattened (voxel, axis) scatter targets: np.bincount is several times faster than
        # np.add.at, and this runs on every bond every step
        self._flat_j = self.bj * 3 + self.ba
        self._flat_i = self.bi * 3 + self.ba
        self._flat_n = n * 3
        # A bond splits its axial strain between its two voxels (CVX_Link::axialStrain,
        # strainRatio = E_pos/E_neg). NOTE this gives the STIFFER voxel the larger share, the
        # opposite of two springs in series (where the soft one takes F/k). It is what Voxelyze
        # does, so we do it too; it only affects the Poisson bookkeeping at soft/bone interfaces
        # (identical materials give an even split), and evolved bodies are ~2% bone.
        ratio = Ev[self.bj] / Ev[self.bi]
        self._f_pos = 2.0 * ratio / (1.0 + ratio)
        self._f_neg = 2.0 / (1.0 + ratio)
        # muscles
        self.v_amp = np.where(np.isin(mats, (1, 2)), self.actuation_amplitude, 0.0)
        self.v_phase = np.where(mats == 2, np.pi, 0.0)       # material gait (Cheney-faithful)

        # ---- surface voxels and Voxelyze collision exclusions ----
        nbrs = [[] for _ in range(n)]
        for i, j in zip(bi, bj):
            nbrs[i].append(j); nbrs[j].append(i)
        surface = np.array([len(nbrs[k]) < 6 for k in range(n)])
        self.surface = surface
        excl = set()
        for s in np.where(surface)[0]:
            seen = {s: 0}
            q = deque([s])
            while q:
                u = q.popleft()
                if seen[u] == COLLISION_DEPTH:
                    continue
                for w in nbrs[u]:
                    if w not in seen:
                        seen[w] = seen[u] + 1
                        q.append(w)
            for w in seen:
                if w > s and surface[w]:
                    excl.add((s, w))
        self.excluded = excl
        sidx = np.where(surface)[0]
        self._sidx = sidx
        spos = {v: a for a, v in enumerate(sidx)}
        near = np.eye(len(sidx), dtype=bool)
        for a_, b_ in excl:
            near[spos[a_], spos[b_]] = near[spos[b_], spos[a_]] = True
        self._near = near
        # collision coefficients per voxel (Voxelyze penetrationStiffness, collisionDampingTranslateC)
        self._kpen = 2 * Ev * L
        self._cpen = ZETA_COLLISION * 2 * np.sqrt(m * Ev * L)
        self._watch = None                      # (ia, ib) candidate pairs, voxel indices
        self._watch_ref = None

        # ---- MJCF ----
        pos = np.array(cells, float) * L
        pos[:, 0] -= pos[:, 0].mean(); pos[:, 1] -= pos[:, 1].mean()
        pos[:, 2] += L / 2 - pos[:, 2].min() + initial_height
        fr = self.friction
        mu0 = 0.7 if fr is None else (fr['mu'] if fr['mode'] == 'single' else fr['mu_s'])
        clamped = set(clamped)
        g_acc = (gravity_scaled(self.materials, L) if self.gravity is None
                 else float(self.gravity))
        self.g_acc = g_acc
        x = [f'<mujoco model="voxel_beam_robot">'
             f'<option timestep="0.0005" gravity="0 0 -{g_acc:.6g}"/>',
             '<visual><global offwidth="1920" offheight="1080"/><quality shadowsize="4096"/>'
             '<map znear="0.01"/></visual>',
             '<asset><texture name="grid" type="2d" builtin="checker" width="512" height="512" '
             'rgb1="0.7 0.75 0.8" rgb2="0.85 0.88 0.9"/><material name="grid" texture="grid" '
             'texrepeat="10 10" texuniform="true" reflectance="0.1"/></asset>',
             '<worldbody>',
             '<geom name="ground" type="plane" size="1 1 0.1" material="grid" contype="0" conaffinity="0"/>',
             '<light pos="0 1 1" dir="0 -1 -0.5" diffuse="0.8 0.8 0.8"/>',
             '<light pos="0.5 1 0" dir="-0.5 -1 0" diffuse="0.4 0.4 0.4"/>']
        for k in range(n):
            p = pos[k]
            joint = '' if k in clamped else f'<freejoint name="joint_{k}"/>'
            x.append(f'<body name="voxel_{k}" pos="{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}">{joint}'
                     f'<inertial pos="0 0 0" mass="{m:.8g}" diaginertia="{I:.8g} {I:.8g} {I:.8g}"/>'
                     f'<geom name="floor_{k}" type="sphere" size="{L/2:.6f}" contype="0" conaffinity="0" group="3"/>'
                     f'<geom name="vis_{k}" type="box" size="{L/2:.6f} {L/2:.6f} {L/2:.6f}" contype="0" '
                     f'conaffinity="0" rgba="{_COLORS[mats[k]]}"/></body>')
        x.append('</worldbody><contact>')
        for k in range(n):
            x.append(f'<pair name="floorpair_{k}" geom1="ground" geom2="floor_{k}" condim="3" '
                     f'friction="{mu0} {mu0} 0.005 0.0001 0.0001"/>')
        x.append('</contact></mujoco>')

        self.model = mujoco.MjModel.from_xml_string('\n'.join(x))
        self.data = mujoco.MjData(self.model)
        self._floor_geom = np.array([mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, f'floor_{k}')
                                     for k in range(n)])
        self._floor_r0 = L / 2
        # per-voxel dof address (None for clamped voxels) for stick-slip speed lookups
        self._ss_vidx = self._ss_sliding = None
        if fr is not None and fr['mode'] == 'stickslip':
            if clamped:
                raise ValueError("stick-slip floor with clamped voxels is not supported")
            adr = self.model.jnt_dofadr[:n]
            self._ss_vidx = np.stack([adr, adr + 1], axis=1)
            self._ss_sliding = np.zeros(n, dtype=bool)
        # interface fields used by the shared code
        self.tendon_info = []
        self.rest_lengths = np.zeros(0)
        self._base_phases = np.zeros(0)
        self._controller = None
        self.current_time = 0.0
        self.default_timestep = self.stable_dt(self.dt_frac)
        self.model.opt.timestep = self.default_timestep
        if self.floor_contact == "voxelyze":
            # A hard floor, because Voxelyze's is effectively hard: its penalty spring
            # k = penetrationStiffness() = 2*E*nomSize gives well under 1% of a voxel of
            # penetration at these loads.
            #
            # MuJoCo's default contact cannot do that here. Its softness is set by a TIME
            # CONSTANT (default 20 ms), and force builds over that time -- but a 40 Hz gait
            # reverses every 25 ms, so the contact never reaches equilibrium and bodies sink
            # 1.6 voxels in while walking. The constant has to be a small fraction of the
            # actuation period, not of the whole run.
            #
            # NOTE a negative solref pair is NOT (stiffness, damping) in N/m: those values act
            # in acceleration space, so writing 2*E*L there gave a floor 1.9x too soft with the
            # evosoro materials and 14.3x too soft with cheney2013 (measured against F/k). That
            # was this engine's floor from 2026-09-24 to 09-28 and it invalidated cheney_corr_s1.
            pid = np.array([mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_PAIR,
                                              f'floorpair_{k}') for k in range(n)])
            # MuJoCo needs the time constant >= 2 time steps to stay stable
            self.model.pair_solref[pid, 0] = max(FLOOR_TIMECONST,
                                                 2.5 * self.default_timestep)
            self.model.pair_solref[pid, 1] = 1.0             # critically damped
            self.model.pair_solimp[pid, 0] = 0.99
            self.model.pair_solimp[pid, 1] = 0.9999
            self.model.pair_solimp[pid, 2] = L / 1000
        self.external = None
        mujoco.mj_forward(self.model, self.data)
        if gait_params is not None:
            # A control CPPN (per-voxel evolvable phase) exposes evaluate_batch; a 4-tuple is
            # the global traveling wave. Same dispatch as the tendon engine.
            if hasattr(gait_params, 'evaluate_batch'):
                self.apply_phase_cppn(gait_params)
            else:
                self.apply_gait_params(gait_params)

    # ------------------------------------------------------------------
    def axial_stiffness(self) -> np.ndarray:
        """Each bond's axial stiffness at rest (Voxelyze CVX_Link::axialStiffness): Ehat*L with
        the volumetric law, the plain a1 = E*L without it."""
        return self.bEhat * self.voxel_size if self.poisson else self.K_ax

    def stable_dt(self, frac: Optional[float] = None) -> float:
        """Largest safe explicit time step for this body.

        dt_rule='voxelyze' (default): Voxelyze's recommendedTimeStep - advance one radian of the
        fastest axial bond mode, times DtFrac 0.7.
        dt_rule='ours': frac / fastest rate, where the rates are each voxel's summed bond stiffness
        over its mass (translation) and inertia (rotation, including the transverse spring acting
        through the L/2 anchor lever arm), and its summed damping over mass / inertia."""
        L, n = self.voxel_size, len(self.cells)
        if len(self.bi) == 0:
            return 0.0005
        k_ax = self.axial_stiffness()
        if self.dt_rule == "voxelyze":
            f = DT_FRAC_VX if frac is None else frac
            return float(min(f / (2 * np.pi * np.sqrt(np.max(k_ax) / self._m)), 0.0005))
        frac = DT_FRAC if frac is None else frac
        def acc(vals):
            out = np.zeros(n)
            np.add.at(out, self.bi, vals); np.add.at(out, self.bj, vals)
            return out
        kt = acc(np.maximum(k_ax, self.K_sh)) + np.where(self.surface, self._kpen, 0.0)
        kr = acc(self.K_b + self.K_sh * (L / 2) ** 2)
        ct = acc(np.maximum(self.d_A1, self.d_B1)) + self.g_lin + np.where(self.surface, self._cpen, 0.0)
        cr = acc(self.d_B3 * 1.5 + self.d_B2 * L / 2) + self.g_rot
        rate = max(np.sqrt(kt.max() / self._m), np.sqrt(kr.max() / self._I),
                   ct.max() / self._m, cr.max() / self._I)
        return float(min(frac / rate, 0.0005))

    def _actuator_count(self) -> int:
        return self._n_actuated_voxels

    # ------------------------------------------------------------------
    def diverged(self) -> bool:
        """True if the simulation blew up. The volumetric law is nonlinear in compression -
        a voxel squeezed until (1 + sum of its constrained strains) approaches zero bulges
        without bound, and the bond force follows - so a body that crushes itself runs away.
        Voxelyze has the same failure (its pow() of a negative base returns NaN); Cheney's
        pipeline discarded such simulations, and so do we."""
        if self.data is None:
            return False
        for w in (mujoco.mjtWarning.mjWARN_BADQACC, mujoco.mjtWarning.mjWARN_BADQVEL,
                  mujoco.mjtWarning.mjWARN_BADQPOS):
            if int(self.data.warning[w].number) > 0:
                return True
        return not (np.all(np.isfinite(self.data.qpos)) and np.all(np.isfinite(self.data.qvel)))

    def get_fitness(self, *args, **kwargs):
        """As the shared implementation, but a body that blew up scores nothing."""
        out = super().get_fitness(*args, **kwargs)
        if not self.diverged():
            return out
        return (0.0, (0.0, 0.0)) if isinstance(out, tuple) else 0.0

    # ------------------------------------------------------------------
    def _norm_coords(self) -> np.ndarray:
        """Each voxel's lattice position normalised to [-1, 1] per axis, plus its distance from
        the body centre — the (x, y, z, dist) the control CPPN is queried on. Taken from the
        lattice indices, so it does not depend on where the body was dropped."""
        c = np.asarray(self.cells, float)
        span = c.max(0) - c.min(0)
        span = np.where(span < 1e-9, 1.0, span)
        n = 2.0 * (c - c.min(0)) / span - 1.0
        dn = np.sqrt((n ** 2).sum(1)) / np.sqrt(3.0)
        return np.column_stack([n, dn]).astype(np.float32)

    def apply_phase_cppn(self, phase_cppn) -> None:
        """Per-voxel evolvable phase (--per-voxel-phase): a co-evolving control CPPN maps each
        voxel's normalised position to an actuation phase, REPLACING the material gait's two
        phases with an arbitrary spatial phase field. The CPPN's first output (tanh, [-1,1])
        scales to [-pi, pi]. Passive voxels keep zero amplitude, so their phase is inert.

        This is what stage 2 of the two-stage protocol optimises on a frozen body
        (Mertan & Cheney 2024).

        phase_mode decides how it combines with the material gait:
          'offset'  (default) ADD the field to the material phase. A near-zero CPPN is then the
                    material gait, so stage 2 starts from the gait the body was evolved with and
                    searches outward. Needed here: a beam champion scores 2.6118 with its material
                    gait and 0.0000 under ANY substituted field, so 'replace' would hand stage 2 a
                    population of zeros with no gradient to climb.
          'replace' overwrite the material phase, matching what the tendon engine does (the
                    springs bodies tolerated it - a random field still scored 1.56 there).
        """
        raw = np.asarray(phase_cppn.evaluate_batch(self._norm_coords())[:, 0], float)
        gain = getattr(phase_cppn, 'phase_gain', None)
        field = (1.0 if gain is None else float(gain)) * np.pi * raw
        self.v_phase = field if self.phase_mode == "replace" else self.v_phase + field

    def apply_gait_params(self, gait_params) -> None:
        """Global traveling wave (--evolve-gait): phase = 2*pi*(kx*xn + ky*yn + kz*zn) + offset
        over the body's bounding box, replacing the material gait."""
        kx, ky, kz, offset = gait_params
        c = np.asarray(self.cells, float)
        span = c.max(0) - c.min(0)
        span = np.where(span < 1e-9, 1.0, span)
        n = (c - c.min(0)) / span
        self.v_phase = (2.0 * np.pi * (kx * n[:, 0] + ky * n[:, 1] + kz * n[:, 2])
                        + offset).astype(float)

    def poisson_strain(self, eps: np.ndarray) -> np.ndarray:
        """Voxelyze CVX_Voxel::strain(true): each voxel's strain on each axis, given every bond's
        axial strain `eps`. Constrained axes take the average of their bonds' shares; free axes
        take the volumetric bulge (1 + sum of the constrained strains)^(-nu) - 1."""
        if len(eps) == 0:                                      # a single voxel has no bonds
            return np.zeros((len(self.cells), 3))
        S = (np.bincount(self._flat_j, self._f_pos * eps, self._flat_n)
             + np.bincount(self._flat_i, self._f_neg * eps, self._flat_n)).reshape(-1, 3)
        S *= self._half
        add = (S * self._tension).sum(1)
        bulge = np.maximum(1.0 + add, 1e-3) ** (-POISSON) - 1.0
        return np.where(self._tension, S, bulge[:, None])

    def axial_bond_force(self, ext: np.ndarray, rest: np.ndarray) -> np.ndarray:
        """Signed axial force in each bond (positive = pulling its two voxels together), from the
        extension beyond rest length. With the volumetric law this is Voxelyze's stress x current
        transverse area; without it, the plain K_ax * extension."""
        if not self.poisson:
            return self.K_ax * ext
        L = self.voxel_size
        eps = ext / rest
        ps = self.poisson_strain(eps)
        one = 1.0 + ps
        tss_v = ps.sum(1, keepdims=True) - ps                  # transverseStrainSum per axis
        area_v = L * L * np.stack([one[:, 1] * one[:, 2], one[:, 0] * one[:, 2],
                                   one[:, 0] * one[:, 1]], 1)  # transverseArea per axis
        i, j, a = self.bi, self.bj, self.ba
        tss = 0.5 * (tss_v[i, a] + tss_v[j, a])
        area = 0.5 * (area_v[i, a] + area_v[j, a])
        return self.bEhat * ((1.0 - POISSON) * eps + POISSON * tss) * area

    def voxel_strain(self, t: float) -> np.ndarray:
        return self.v_amp * np.sin(2.0 * np.pi * self.actuation_frequency * t + self.v_phase)

    # ------------------------------------------------------------------
    def forces(self, s: np.ndarray):
        """Bond (stiffness + Voxelyze damping) and global-damping forces/torques, world frame."""
        d, L = self.data, self.voxel_size
        p = d.xpos[1:]
        R = d.xmat[1:].reshape(-1, 3, 3)
        q = d.xquat[1:]
        w = d.cvel[1:, :3]
        v = d.cvel[1:, 3:]
        i, j = self.bi, self.bj
        n = len(self.cells)
        rest = L * (1.0 + 0.5 * (s[i] + s[j]))
        Ri = R[i]

        # --- stiffness: midpoint mismatch + relative rotation (exact frame element) ---
        hi = np.einsum('bij,bj->bi', Ri, self.ea) * (rest / 2)[:, None]
        hj = -np.einsum('bij,bj->bi', R[j], self.ea) * (rest / 2)[:, None]
        u = (p[j] + hj) - (p[i] + hi)
        mvec = hi - hj
        mlen = np.linalg.norm(mvec, axis=1, keepdims=True)
        nvec = mvec / mlen
        ext = (u * nvec).sum(1)                                            # beyond rest length
        upar = ext[:, None] * nvec
        fax = self.axial_bond_force(ext, rest)
        Fj = -(fax[:, None] * nvec + self.K_sh[:, None] * (u - upar))
        phi = _rotvec(_qmul(q[i] * np.array([1, -1, -1, -1]), q[j]))       # j relative to i, i-frame
        tw = (phi * self.ea).sum(1, keepdims=True)
        tau_j = np.einsum('bij,bj->bi', Ri,
                          -(self.K_b[:, None] * (phi - tw * self.ea) + self.K_t[:, None] * tw * self.ea))
        Tj = tau_j + np.cross(hj, Fj)
        Ti = -tau_j + np.cross(hi, -Fj)
        # The bond axis n = (hi - hj)/|hi - hj| turns with the two voxels, so whenever the axial
        # force differs from K_sh * extension (i.e. with the volumetric law) the energy also
        # depends on the orientations through n. Without this term the bond exerts a net torque
        # on the pair. It vanishes identically when the volumetric law is off, because there
        # K_ax = K_sh and the bond force is simply K * u.
        g = (fax - self.K_sh * ext)[:, None] / mlen
        uperp = u - upar
        Ti = Ti - g * np.cross(hi, uperp)
        Tj = Tj + g * np.cross(hj, uperp)
        Fi = -Fj

        # --- Voxelyze link damping, in voxel i's frame with the bond axis as local x ---
        rel = p[j] - p[i]
        wi_l = np.einsum('bji,bj->bi', Ri, w[i])                            # R_i^T w_i
        r_l = np.einsum('bji,bj->bi', Ri, rel)
        v_l = np.einsum('bji,bj->bi', Ri, v[j] - v[i]) - np.cross(wi_l, r_l)
        w_l = np.einsum('bji,bj->bi', Ri, w[j] - w[i])
        rows = np.arange(len(i))[:, None]
        vx, vy, vz = v_l[rows, self._perm].T
        wx, wy, wz = w_l[rows, self._perm].T
        fneg = np.stack([self.d_A1 * vx, self.d_B1 * vy - self.d_B2 * wz,
                         self.d_B1 * vz + self.d_B2 * wy], 1)
        mneg = -0.5 * np.stack([-self.d_A2 * wx, self.d_B2 * vz + self.d_B3 * wy,
                                -self.d_B2 * vy + self.d_B3 * wz], 1)
        mpos = -0.5 * np.stack([self.d_A2 * wx, self.d_B2 * vz + 2 * self.d_B3 * wy,
                                -self.d_B2 * vy + 2 * self.d_B3 * wz], 1)
        def to_world(loc):
            return np.einsum('bij,bj->bi', Ri, loc[rows, self._iperm])
        fneg_w = to_world(fneg)
        Fi = Fi + fneg_w
        Fj = Fj - fneg_w
        Ti = Ti + to_world(mneg)
        Tj = Tj + to_world(mpos)

        def scatter(vi, vj):
            return np.stack([np.bincount(i, vi[:, c], n) + np.bincount(j, vj[:, c], n)
                             for c in range(3)], 1)
        F = scatter(Fi, Fj) - self.g_lin[:, None] * v + self._collision_forces(p, v, s)
        T = scatter(Ti, Tj) - self.g_rot[:, None] * w
        if self.test_damping:
            F -= self.test_damping * self._m * v
            T -= self.test_damping * self._I * w
        return F, T

    def _collision_forces(self, p, v, s):
        """Voxelyze self-collision over the watch list (see module docstring)."""
        n, L = len(self.cells), self.voxel_size
        out = np.zeros((n, 3))
        sidx = self._sidx
        if len(sidx) < 2:
            return out
        ps = p[sidx]
        if self._watch is None or np.abs(ps - self._watch_ref).max() > 0.5 * L:
            dd = np.linalg.norm(ps[:, None, :] - ps[None, :, :], axis=2)
            a_, b_ = np.where(np.triu((dd < WATCH_RADIUS * L) & ~self._near, 1))
            self._watch = (sidx[a_], sidx[b_])
            self._watch_ref = ps.copy()
        ia, ib = self._watch
        if len(ia) == 0:
            return out
        off = p[ib] - p[ia]
        dist = np.linalg.norm(off, axis=1)
        nom = ENVELOPE_RADIUS * L * ((1 + s[ia]) + (1 + s[ib]))
        pen = nom - dist
        hit = pen > 0
        if not hit.any():
            return out
        ia, ib, off, dist, pen = ia[hit], ib[hit], off[hit], dist[hit], pen[hit]
        unit = off / dist[:, None]
        k = 2.0 / (1.0 / self._kpen[ia] + 1.0 / self._kpen[ib])
        c = 0.5 * (self._cpen[ia] + self._cpen[ib])
        vn = ((v[ib] - v[ia]) * unit).sum(1)
        f = (k * pen - c * vn)[:, None] * unit            # pushes b away from a
        for comp in range(3):
            out[:, comp] += np.bincount(ib, f[:, comp], n) - np.bincount(ia, f[:, comp], n)
        return out

    def step(self) -> None:
        """One step: floor-contact sizes and floor friction are set BEFORE collision detection
        (mj_step1), bond forces from the current state AFTER it, then integrate (mj_step2)."""
        if self.model is None:
            return
        s = self.voxel_strain(self.current_time)
        r = self._floor_r0 * (1.0 + s)
        self.model.geom_size[self._floor_geom, 0] = r
        self.model.geom_rbound[self._floor_geom] = r
        if self._ss_sliding is not None:
            self._update_floor_friction()
        mujoco.mj_step1(self.model, self.data)
        F, T = self.forces(s)
        self.data.xfrc_applied[1:, :3] = F
        self.data.xfrc_applied[1:, 3:] = T
        if self.external is not None:
            self.data.xfrc_applied[1:] += self.external
        mujoco.mj_step2(self.model, self.data)
        self.current_time += self.default_timestep
