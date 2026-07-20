"""
Voxel grid -> MuJoCo flex (deformable) model  [B5 reformulation]

Replaces the free-rigid-body-per-voxel + spatial-tendon model with a native
deformable body:
  - Each occupied voxel is meshed into 5 tetrahedra (shared corner nodes ->
    one connected continuum). This is the `flexcomp type="direct"` substrate:
    internal cohesion + self-intersection resistance come from cheap FEM edges,
    NOT from thousands of contact constraints (the tendon model's ~99% cost).
  - Muscle: materials 1 (phase 0deg) and 2 (phase 180deg) get position-actuated
    spatial tendons along their x-edges, driven open-loop at a global frequency
    (same actuation scheme as the tendon model's open-loop mode).

v1 limitations (documented; flex is an accepted FRESH baseline):
  - Materials 3 (soft) and 4 (stiff) are passive; per-material stiffness is NOT
    differentiated (flex `young` is per-flex, not per-element). Presence + the two
    muscle phases ARE preserved, so morphology/gait structure still evolve.
  - selfcollide="none": far-apart parts can pass through each other (rare). The
    FEM handles local (adjacent) self-intersection, which is the load-bearing case.

Material IDs (unchanged): 0=empty, 1=muscle 0deg, 2=muscle 180deg, 3=soft, 4=stiff.
"""
import numpy as np
import mujoco

# 8 cube corners as (dx,dy,dz)
_CORNERS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
_A, _B, _C, _D, _E, _F, _G, _H = range(8)
# standard 5-tet split of a cube (indices into _CORNERS); shares nodes across cells
_TETS = [(_A, _B, _D, _E), (_B, _C, _D, _G), (_B, _D, _E, _G),
         (_B, _E, _F, _G), (_D, _E, _G, _H)]
# the 4 axis-parallel edges of a cube, as (corner_lo, corner_hi)
_X_EDGES = [(_A, _B), (_D, _C), (_E, _F), (_H, _G)]   # forward (push/pull)
_Y_EDGES = [(_A, _D), (_B, _C), (_E, _H), (_F, _G)]   # lateral
_Z_EDGES = [(_A, _E), (_B, _F), (_C, _G), (_D, _H)]   # vertical (lift/plant)


def build_flex_spec(voxel_grid, voxel_size=0.01, initial_height=0.0,
                    young=1.0e4, poisson=0.2, muscle_kp=600.0,
                    timestep=0.0005, muscle_amp_headroom=1.6,
                    wave_phase_n=None, multi_axis=False,
                    z_phase_offset=np.pi / 2, include_y=False, y_phase_offset=np.pi,
                    feet=False, foot_radius_frac=0.35, foot_friction=3.0,
                    gait_params=None):
    """Return (spec, base_phases) — an uncompiled MjSpec flex robot + per-actuator phase.

    base_phases[k] is the open-loop phase of muscle actuator k. By default the phase
    is material-derived (0 for mat 1, pi for mat 2) — a 2-phase standing pattern.
    If wave_phase_n is set, phase = 2*pi*wave_phase_n * (edge_center_x / body_x_len),
    a TRAVELING WAVE (diagnostic / C6 groundwork; the spike showed waves locomote far
    better than 2-phase on a flex continuum).
    """
    grid = np.asarray(voxel_grid)
    occ = np.argwhere(grid != 0)
    if len(occ) == 0:
        raise ValueError("empty voxel grid")

    # --- unique corner nodes (dedup by integer lattice coord) ---
    node_index = {}
    node_coords = []
    def node_id(coord):
        k = tuple(int(c) for c in coord)
        if k not in node_index:
            node_index[k] = len(node_coords)
            node_coords.append(k)
        return node_index[k]

    # --- tets (element connectivity) ---
    elems = []
    for (i, j, k) in occ:
        corner_ids = [node_id((i + dx, j + dy, k + dz)) for (dx, dy, dz) in _CORNERS]
        for tet in _TETS:
            elems.append(tuple(corner_ids[c] for c in tet))

    coords = np.array(node_coords, dtype=float)
    coords -= coords.min(axis=0)                      # min corner at origin
    coords *= voxel_size
    n_nodes = len(coords)
    n_vox = int(len(occ))

    pts = " ".join(f"{v:.5f}" for xyz in coords for v in xyz)
    els = " ".join(str(v) for e in elems for v in e)
    z_off = initial_height + voxel_size * 0.5
    total_mass = max(1e-3, n_vox * 1.0e-3)            # ~1 g per voxel

    # collision bitmasks. Without feet: flex<->floor only. With feet, a 3-group scheme
    # so grip "feet" touch the FLOOR only (not each other, not the flex body):
    #   floor ct=4 ca=3 ; flex ct=1 ca=4 ; foot ct=2 ca=4
    #   flex-floor: 1&3 -> yes ; foot-floor: 2&3 -> yes ; foot-flex/foot-foot -> 0 (no)
    if feet:
        floor_ct, floor_ca, flex_ct, flex_ca = 4, 3, 1, 4
    else:
        floor_ct, floor_ca, flex_ct, flex_ca = 1, 1, 1, 1

    xml = f"""
    <mujoco>
      <option timestep="{timestep}" gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="ground" type="plane" size="5 5 0.1" pos="0 0 0"
              friction="0.7 0.005 0.0001" condim="3" contype="{floor_ct}" conaffinity="{floor_ca}"/>
        <flexcomp name="vx" type="direct" dim="3" pos="0 0 {z_off:.5f}"
                  mass="{total_mass:.5f}" radius="{voxel_size*0.5:.5f}"
                  point="{pts}" element="{els}">
          <elasticity young="{young}" poisson="{poisson}"/>
          <contact internal="false" selfcollide="none" contype="{flex_ct}" conaffinity="{flex_ca}"/>
        </flexcomp>
      </worldbody>
    </mujoco>"""
    spec = mujoco.MjSpec.from_string(xml)

    # light damping on node slide joints for stability
    for b in spec.worldbody.bodies:
        for jt in b.joints:
            jt.damping = 0.5

    # --- muscles: one position-actuated tendon per unique x-edge of a muscle voxel ---
    body_of = {}                                       # node index -> spec body
    for b in spec.worldbody.bodies:
        if b.name.startswith("vx_"):
            body_of[int(b.name.split("_")[1])] = b

    # --- grip "feet": small friction spheres on bottom-layer nodes (floor-only contact) ---
    n_feet = 0
    if feet:
        zmin = float(coords[:, 2].min())
        r = voxel_size * foot_radius_frac
        for n in range(n_nodes):
            if coords[n][2] - zmin < 1e-6 and n in body_of:
                g = body_of[n].add_geom(name=f"foot{n}")
                g.type = mujoco.mjtGeom.mjGEOM_SPHERE
                g.size[0] = r
                g.pos[2] = -voxel_size * 0.5      # hang below the body so it's the contact point
                g.contype, g.conaffinity, g.condim = 2, 4, 3
                g.friction[0] = foot_friction
                g.density = 30.0
                g.rgba[:] = [0.9, 0.2, 0.2, 1.0]
                n_feet += 1

    # which cube-edge axes carry muscles, and each axis's phase offset. Offsetting
    # the vertical (z) muscles ~90deg from the forward (x) muscles turns each region's
    # motion into a rowing/elliptical stroke (contract+lift / extend+plant) => real crawl.
    axis_edges = [(_X_EDGES, 0.0)]
    if multi_axis:
        axis_edges.append((_Z_EDGES, z_phase_offset))
        if include_y:
            axis_edges.append((_Y_EDGES, y_phase_offset))

    edge_info = {}                             # (nodeA,nodeB) -> (material_base, axis_offset)
    for (i, j, k) in occ:
        mat = int(grid[i, j, k])
        if mat not in (1, 2):
            continue
        base = 0.0 if mat == 1 else np.pi
        corner_ids = [node_id((i + dx, j + dy, k + dz)) for (dx, dy, dz) in _CORNERS]
        for (edges, offset) in axis_edges:
            for (lo, hi) in edges:
                a, b = corner_ids[lo], corner_ids[hi]
                key = (min(a, b), max(a, b))
                edge_info.setdefault(key, (base, offset))   # first claimer sets phase

    body_x_len = max(float(np.ptp(coords[:, 0])), 1e-6)
    cmin = coords.min(0)
    cext = np.where((coords.max(0) - cmin) < 1e-6, 1.0, coords.max(0) - cmin)
    base_phases = []
    for n, ((a, b), (mbase, offset)) in enumerate(edge_info.items()):
        if gait_params is not None:
            # C6 evolvable gait: spatial traveling wave phase(x,y,z) from evolved genes
            # [kx,ky,kz,goff], plus the per-axis stroke offset (x=push, z=lift).
            kx, ky, kz, goff = gait_params
            ecn = (0.5 * (coords[a] + coords[b]) - cmin) / cext
            phase = 2.0 * np.pi * (kx * ecn[0] + ky * ecn[1] + kz * ecn[2]) + goff + offset
        elif wave_phase_n is not None:
            # fixed traveling wave along x + per-axis offset => crawling stroke
            edge_cx = 0.5 * (coords[a][0] + coords[b][0])
            phase = 2.0 * np.pi * wave_phase_n * edge_cx / body_x_len + offset
        else:
            phase = mbase + offset
        ba, bb = body_of[a], body_of[b]
        sa = ba.add_site(name=f"ms_a{n}", pos=[0, 0, 0], size=[0.002, 0, 0])
        sb = bb.add_site(name=f"ms_b{n}", pos=[0, 0, 0], size=[0.002, 0, 0])
        t = spec.add_tendon(name=f"m{n}")
        t.wrap_site(sa.name)
        t.wrap_site(sb.name)
        act = spec.add_actuator(name=f"act{n}")
        act.trntype = mujoco.mjtTrn.mjTRN_TENDON
        act.target = t.name
        act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
        act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        act.gainprm[0] = muscle_kp
        act.biasprm[1] = -muscle_kp
        act.ctrlrange[0] = 0.0
        act.ctrlrange[1] = voxel_size * muscle_amp_headroom
        act.ctrllimited = 1
        base_phases.append(phase)

    return spec, np.array(base_phases, dtype=float), dict(
        n_nodes=n_nodes, n_vox=n_vox, n_elem=len(elems),
        n_muscles=len(base_phases), n_feet=n_feet)
