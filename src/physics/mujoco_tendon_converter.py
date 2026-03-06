"""
MuJoCo Tendon-Based Converter

Generates MuJoCo XML with:
- Sites on every voxel body (attachment points for tendons)
- Spatial tendons for ALL adjacent pairs (edge + face diagonal + space diagonal)
- Position actuators for ALL tendons (ctrl = target tendon length)

Actuation: ctrl[i] = rest_length[i] * (1 + amplitude * sin(omega*t + phase))
"""
import numpy as np
from typing import List, Tuple, Dict


def voxel_to_tendon_xml(
    voxel_grid: np.ndarray,
    voxel_size: float = 0.01,
    initial_height: float = 0.0,
    kp: float = 100.0
) -> Tuple[str, List[Dict]]:
    """
    Convert voxel grid to MuJoCo XML with tendon-based actuation.

    Args:
        voxel_grid: 3D numpy array with material IDs
                    0=empty, 1=Active 0deg, 2=Active 180deg,
                    3=Soft passive, 4=Stiff passive
        voxel_size: Size of each voxel in meters (default 0.01m = 1cm)
        initial_height: Starting height above ground in meters
        kp: Position actuator gain (force = kp * (ctrl - current_length))

    Returns:
        (xml_string, tendon_info_list)
        tendon_info_list: list of dicts with keys:
            - 'body1_idx': index of first voxel
            - 'body2_idx': index of second voxel
            - 'mat1': material ID of body1
            - 'mat2': material ID of body2
            - 'connection_type': 'edge', 'face_diag', or 'space_diag'
    """
    materials = {
        1: {'name': 'active_0',    'density': 200.0, 'color': '0 1 0 0.6', 'phase': 0.0},
        2: {'name': 'active_180',  'density': 200.0, 'color': '1 0 0 0.6', 'phase': 3.14159},
        3: {'name': 'soft_passive','density': 200.0, 'color': '0 1 1 0.6', 'phase': None},
        4: {'name': 'stiff_passive','density': 200.0,'color': '0 0 1 0.6', 'phase': None},
    }

    # Collect voxels
    voxels = []
    for x in range(voxel_grid.shape[0]):
        for y in range(voxel_grid.shape[1]):
            for z in range(voxel_grid.shape[2]):
                material_id = int(voxel_grid[x, y, z])
                if material_id == 0:
                    continue
                mat = materials[material_id]
                pos = np.array([x, y, z], dtype=float) * voxel_size
                volume = voxel_size ** 3
                mass = mat['density'] * volume
                voxels.append({
                    'id': len(voxels),
                    'pos': pos,
                    'material': mat,
                    'material_id': material_id,
                    'mass': mass,
                })

    if len(voxels) == 0:
        raise ValueError("No voxels in grid!")

    # Center X, Y; place bottom at initial_height
    positions = np.array([v['pos'] for v in voxels])
    center_xy = np.mean(positions[:, :2], axis=0)
    min_z = np.min(positions[:, 2])
    for v in voxels:
        v['pos'][0] -= center_xy[0]
        v['pos'][1] -= center_xy[1]
        v['pos'][2] -= min_z
        v['pos'][2] += voxel_size / 2.0   # sit on ground
        v['pos'][2] += initial_height

    half_size = voxel_size / 2.0

    # --- Find adjacent pairs ---
    edge_dist       = voxel_size
    face_diag_dist  = voxel_size * np.sqrt(2)
    space_diag_dist = voxel_size * np.sqrt(3)
    tolerance = voxel_size * 0.01

    tendon_pairs = []   # list of (i, j, connection_type)
    tendon_info  = []   # metadata returned to caller

    for i, v1 in enumerate(voxels):
        for j, v2 in enumerate(voxels):
            if j <= i:
                continue
            dist = np.linalg.norm(v1['pos'] - v2['pos'])
            if abs(dist - edge_dist) < tolerance:
                ctype = 'edge'
            elif abs(dist - face_diag_dist) < tolerance:
                ctype = 'face_diag'
            elif abs(dist - space_diag_dist) < tolerance:
                ctype = 'space_diag'
            else:
                continue
            tendon_pairs.append((i, j, ctype))
            tendon_info.append({
                'body1_idx': i,
                'body2_idx': j,
                'mat1': v1['material_id'],
                'mat2': v2['material_id'],
                'connection_type': ctype,
            })

    # --- Build XML ---
    xml = []
    xml.append('<mujoco model="voxel_tendon_robot">')
    xml.append('  <option timestep="0.0005" gravity="0 0 -9.81"/>')
    xml.append('')

    # Visual
    xml.append('  <visual>')
    xml.append('    <headlight diffuse="0.6 0.6 0.6" ambient="0.5 0.5 0.5" specular="0 0 0"/>')
    xml.append('    <rgba haze="0.95 0.95 0.9 1"/>')
    xml.append('    <global offwidth="1920" offheight="1080"/>')
    xml.append('    <quality shadowsize="4096"/>')
    xml.append('    <map force="0.1" znear="0.01"/>')
    xml.append('  </visual>')
    xml.append('')

    # Assets
    xml.append('  <asset>')
    xml.append('    <texture name="grid" type="2d" builtin="checker" width="512" height="512"')
    xml.append('             rgb1="0.7 0.75 0.8" rgb2="0.85 0.88 0.9"/>')
    xml.append('    <material name="grid" texture="grid" texrepeat="10 10" texuniform="true" reflectance="0.1"/>')
    xml.append('  </asset>')
    xml.append('')

    # World body
    xml.append('  <worldbody>')
    xml.append('    <geom name="ground" type="plane" size="1 1 0.1" material="grid" friction="0.7 0.005 0.0001" condim="3"/>')
    xml.append('    <geom name="origin_marker" type="sphere" size="0.005" pos="0 0 0" rgba="1 0 0 1" contype="0" conaffinity="0"/>')
    xml.append('    <geom name="x_axis" type="capsule" fromto="0 0 0 0.05 0 0" size="0.001" rgba="1 0 0 0.8" contype="0" conaffinity="0"/>')
    xml.append('    <geom name="y_axis" type="capsule" fromto="0 0 0 0 0.05 0" size="0.001" rgba="0 1 0 0.8" contype="0" conaffinity="0"/>')
    xml.append('    <geom name="z_axis" type="capsule" fromto="0 0 0 0 0 0.05" size="0.001" rgba="0 0 1 0.8" contype="0" conaffinity="0"/>')
    xml.append('    <light pos="0 1 1" dir="0 -1 -0.5" diffuse="0.8 0.8 0.8"/>')
    xml.append('    <light pos="0.5 1 0" dir="-0.5 -1 0" diffuse="0.4 0.4 0.4"/>')
    xml.append('')

    for i, v in enumerate(voxels):
        x, y, z = v['pos']
        mat = v['material']
        xml.append(f'    <body name="voxel_{i}" pos="{x:.6f} {y:.6f} {z:.6f}">')
        xml.append(f'      <joint name="joint_{i}" type="free"/>')
        xml.append(f'      <geom name="geom_{i}" type="box" size="{half_size} {half_size} {half_size}" '
                   f'rgba="{mat["color"]}" mass="{v["mass"]:.6f}" friction="0.6 0.005 0.0001" condim="3"/>')
        # One site at the body center (origin of this body frame)
        xml.append(f'      <site name="site_{i}" pos="0 0 0" size="0.001"/>')
        xml.append(f'    </body>')

    xml.append('  </worldbody>')
    xml.append('')

    # Tendons - spatial tendons connecting site pairs
    xml.append('  <tendon>')
    for k, (i, j, ctype) in enumerate(tendon_pairs):
        xml.append(f'    <spatial name="tendon_{k}">')
        xml.append(f'      <site site="site_{i}"/>')
        xml.append(f'      <site site="site_{j}"/>')
        xml.append(f'    </spatial>')
    xml.append('  </tendon>')
    xml.append('')

    # Actuators - position actuators on every tendon
    # kv=0 prevents velocity feedback which can cause instability
    # ctrlrange covers all connection types (edge=0.01, face_diag=0.0141, space_diag=0.0173)
    xml.append('  <actuator>')
    for k in range(len(tendon_pairs)):
        xml.append(f'    <position name="act_{k}" tendon="tendon_{k}" '
                   f'kp="{kp:.1f}" kv="0" ctrlrange="0 0.05"/>')
    xml.append('  </actuator>')
    xml.append('')
    xml.append('</mujoco>')

    return '\n'.join(xml), tendon_info
