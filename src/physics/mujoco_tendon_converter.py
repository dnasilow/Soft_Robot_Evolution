"""
MuJoCo Tendon-Based Converter

Generates MuJoCo XML with:
- Sites on every voxel body (attachment points for tendons)
- Spatial tendons for FACE-ADJACENT pairs only (6-connectivity)
- Position actuators with per-tendon kp based on material type

Only face neighbours (Manhattan distance = 1) are connected by springs.
Diagonal connections (edge-diagonal, space-diagonal) are excluded because:
  - Faces physically touch and share area; diagonals share only an edge or
    a point — there is no physical interface to transmit force through.
  - 26 springs per interior voxel generated forces of 200+g, launching
    robots into the air. 6 face springs reduces peak force by ~4x.
  - Matches the Voxelyze/Cheney-2013 standard for voxel soft-robot sims.

Material kp values:
  Active (mat1/mat2): kp = 100
  Soft passive (mat3): kp = 50   (2x softer than stiff)
  Stiff passive (mat4): kp = 100
  Mixed: kp = min(kp1, kp2)

Boundary phase (mat1 + mat2 tendon): pi/2  (average of 0 and pi)
Active + passive: phase of the active material
Both passive: is_active = False, ctrl held at rest length
"""
import numpy as np
from typing import List, Tuple, Dict, Optional

# -----------------------------------------------------------------
# Constants
# -----------------------------------------------------------------
_KP    = {1: 100.0, 2: 100.0, 3: 50.0, 4: 100.0}
_PHASE = {1: 0.0, 2: np.pi}   # passive materials have no entry

# 3 face-neighbour offsets that enumerate every unique face-adjacent pair
# once (we only walk in the "positive" half-space; the reverse direction is
# covered when the neighbour processes its own row).
_FACE_OFFSETS = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]

_ALL_OFFSETS = [('face', o) for o in _FACE_OFFSETS]


# -----------------------------------------------------------------
# Public helpers
# -----------------------------------------------------------------
def count_active_tendons(voxel_grid: np.ndarray) -> int:
    """
    Count tendons where at least one endpoint is an active material (1 or 2).
    O(n) with n = number of filled voxels.
    Does NOT require loading MuJoCo — used to size CPGController before evaluation.
    """
    # Build grid-coord lookup
    active_set = {1, 2}
    coord_mat: Dict[Tuple[int, int, int], int] = {}
    for x in range(voxel_grid.shape[0]):
        for y in range(voxel_grid.shape[1]):
            for z in range(voxel_grid.shape[2]):
                m = int(voxel_grid[x, y, z])
                if m != 0:
                    coord_mat[(x, y, z)] = m

    count = 0
    for (x, y, z), m1 in coord_mat.items():
        for _, (dx, dy, dz) in _ALL_OFFSETS:
            nb = (x + dx, y + dy, z + dz)
            if nb in coord_mat:
                m2 = coord_mat[nb]
                if m1 in active_set or m2 in active_set:
                    count += 1
    return count


def _tendon_kp(mat1: int, mat2: int) -> float:
    return min(_KP[mat1], _KP[mat2])


def _tendon_phase(mat1: int, mat2: int) -> Optional[float]:
    """
    Returns actuation phase in radians, or None if tendon is passive.
    mat1+mat2 boundary → pi/2 (average).
    """
    p1 = _PHASE.get(mat1)   # None for passive
    p2 = _PHASE.get(mat2)   # None for passive
    if p1 is None and p2 is None:
        return None          # both passive
    phases = [p for p in (p1, p2) if p is not None]
    return sum(phases) / len(phases)


# -----------------------------------------------------------------
# Main converter
# -----------------------------------------------------------------
def voxel_to_tendon_xml(
    voxel_grid: np.ndarray,
    voxel_size: float = 0.01,
    initial_height: float = 0.0,
) -> Tuple[str, List[Dict]]:
    """
    Convert voxel grid to MuJoCo XML with tendon-based actuation.

    Args:
        voxel_grid: 3D numpy array with material IDs
                    0=empty, 1=Active 0deg, 2=Active 180deg,
                    3=Soft passive, 4=Stiff passive
        voxel_size: Size of each voxel in meters (default 0.01m = 1cm)
        initial_height: Starting height above ground in metres

    Returns:
        (xml_string, tendon_info_list)
        tendon_info_list entries have keys:
            body1_idx, body2_idx, mat1, mat2,
            connection_type, kp, base_phase (float or None), is_active (bool)
    """
    _colors = {
        1: '0 1 0 0.6',   # green
        2: '1 0 0 0.6',   # red
        3: '0 1 1 0.6',   # cyan
        4: '0 0 1 0.6',   # blue
    }
    _density = {1: 200.0, 2: 200.0, 3: 200.0, 4: 200.0}

    # ------------------------------------------------------------------
    # 1. Collect voxels, store integer grid coordinates
    # ------------------------------------------------------------------
    voxels = []
    coord_to_idx: Dict[Tuple[int, int, int], int] = {}

    for x in range(voxel_grid.shape[0]):
        for y in range(voxel_grid.shape[1]):
            for z in range(voxel_grid.shape[2]):
                m = int(voxel_grid[x, y, z])
                if m == 0:
                    continue
                idx = len(voxels)
                coord_to_idx[(x, y, z)] = idx
                voxels.append({
                    'id':          idx,
                    'grid':        (x, y, z),
                    'pos':         np.array([x, y, z], dtype=float) * voxel_size,
                    'material_id': m,
                    'color':       _colors[m],
                    'mass':        _density[m] * voxel_size ** 3,
                })

    if len(voxels) == 0:
        raise ValueError("No voxels in grid!")

    # ------------------------------------------------------------------
    # 2. Centre X/Y; sit on ground
    # ------------------------------------------------------------------
    positions = np.array([v['pos'] for v in voxels])
    cx, cy = np.mean(positions[:, 0]), np.mean(positions[:, 1])
    min_z   = np.min(positions[:, 2])
    for v in voxels:
        v['pos'][0] -= cx
        v['pos'][1] -= cy
        v['pos'][2] -= min_z
        v['pos'][2] += voxel_size / 2.0   # bottom face on Z=0
        v['pos'][2] += initial_height

    half = voxel_size / 2.0

    # ------------------------------------------------------------------
    # 3. Find adjacent pairs — O(n × 13) instead of O(n²)
    # ------------------------------------------------------------------
    tendon_pairs = []   # (i, j, ctype)
    tendon_info  = []

    for (gx, gy, gz), i in coord_to_idx.items():
        m1 = voxels[i]['material_id']
        for ctype, (dx, dy, dz) in _ALL_OFFSETS:
            nb = (gx + dx, gy + dy, gz + dz)
            if nb not in coord_to_idx:
                continue
            j  = coord_to_idx[nb]
            m2 = voxels[j]['material_id']
            bp = _tendon_phase(m1, m2)
            kp = _tendon_kp(m1, m2)
            tendon_pairs.append((i, j, ctype))
            tendon_info.append({
                'body1_idx':       i,
                'body2_idx':       j,
                'mat1':            m1,
                'mat2':            m2,
                'connection_type': ctype,
                'kp':              kp,
                'base_phase':      bp,
                'is_active':       bp is not None,
            })

    # ------------------------------------------------------------------
    # 4. Build XML
    # ------------------------------------------------------------------
    xml = []
    xml.append('<mujoco model="voxel_tendon_robot">')
    xml.append('  <option timestep="0.0005" gravity="0 0 -9.81"/>')
    xml.append('')
    xml.append('  <visual>')
    xml.append('    <headlight diffuse="0.6 0.6 0.6" ambient="0.5 0.5 0.5" specular="0 0 0"/>')
    xml.append('    <rgba haze="0.95 0.95 0.9 1"/>')
    xml.append('    <global offwidth="1920" offheight="1080"/>')
    xml.append('    <quality shadowsize="4096"/>')
    xml.append('    <map force="0.1" znear="0.01"/>')
    xml.append('  </visual>')
    xml.append('')
    xml.append('  <asset>')
    xml.append('    <texture name="grid" type="2d" builtin="checker" width="512" height="512"')
    xml.append('             rgb1="0.7 0.75 0.8" rgb2="0.85 0.88 0.9"/>')
    xml.append('    <material name="grid" texture="grid" texrepeat="10 10"'
               ' texuniform="true" reflectance="0.1"/>')
    xml.append('  </asset>')
    xml.append('')
    xml.append('  <worldbody>')
    xml.append('    <geom name="ground" type="plane" size="1 1 0.1" material="grid"'
               ' friction="0.7 0.005 0.0001" condim="3"/>')
    xml.append('    <geom name="origin_marker" type="sphere" size="0.005" pos="0 0 0"'
               ' rgba="1 0 0 1" contype="0" conaffinity="0"/>')
    xml.append('    <geom name="x_axis" type="capsule" fromto="0 0 0 0.05 0 0"'
               ' size="0.001" rgba="1 0 0 0.8" contype="0" conaffinity="0"/>')
    xml.append('    <geom name="y_axis" type="capsule" fromto="0 0 0 0 0.05 0"'
               ' size="0.001" rgba="0 1 0 0.8" contype="0" conaffinity="0"/>')
    xml.append('    <geom name="z_axis" type="capsule" fromto="0 0 0 0 0 0.05"'
               ' size="0.001" rgba="0 0 1 0.8" contype="0" conaffinity="0"/>')
    xml.append('    <light pos="0 1 1" dir="0 -1 -0.5" diffuse="0.8 0.8 0.8"/>')
    xml.append('    <light pos="0.5 1 0" dir="-0.5 -1 0" diffuse="0.4 0.4 0.4"/>')
    xml.append('')

    for v in voxels:
        x, y, z = v['pos']
        xml.append(f'    <body name="voxel_{v["id"]}" pos="{x:.6f} {y:.6f} {z:.6f}">')
        xml.append(f'      <joint name="joint_{v["id"]}" type="free"/>')
        xml.append(f'      <geom name="geom_{v["id"]}" type="box"'
                   f' size="{half} {half} {half}"'
                   f' rgba="{v["color"]}" mass="{v["mass"]:.6f}"'
                   f' friction="0.6 0.005 0.0001" condim="3"/>')
        xml.append(f'      <site name="site_{v["id"]}" pos="0 0 0" size="0.001"/>')
        xml.append(f'    </body>')

    xml.append('  </worldbody>')
    xml.append('')

    # Tendons
    xml.append('  <tendon>')
    for k, (i, j, _) in enumerate(tendon_pairs):
        xml.append(f'    <spatial name="tendon_{k}">')
        xml.append(f'      <site site="site_{i}"/>')
        xml.append(f'      <site site="site_{j}"/>')
        xml.append(f'    </spatial>')
    xml.append('  </tendon>')
    xml.append('')

    # Actuators — each gets its own kp from tendon_info
    xml.append('  <actuator>')
    for k, info in enumerate(tendon_info):
        xml.append(f'    <position name="act_{k}" tendon="tendon_{k}"'
                   f' kp="{info["kp"]:.1f}" kv="0" ctrlrange="0 0.05"/>')
    xml.append('  </actuator>')
    xml.append('')
    xml.append('</mujoco>')

    return '\n'.join(xml), tendon_info
