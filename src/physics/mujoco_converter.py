"""Convert voxel robots to MuJoCo XML format"""
import numpy as np
from typing import Dict, List, Tuple

def voxel_to_mujoco_xml(voxel_grid: np.ndarray, voxel_size: float = 0.01, initial_height: float = 0.0) -> str:
    """
    Convert voxel grid to MuJoCo XML model

    Args:
        voxel_grid: 3D numpy array (X, Y, Z) with material IDs
                   0 = empty, 1 = Active 0°, 2 = Active 180°, 3 = Soft passive, 4 = Stiff passive
        voxel_size: Size of each voxel in meters (default 0.01m = 1cm)
        initial_height: Additional height offset in meters (default 0.0 = start on ground)

    Returns:
        MuJoCo XML string
    """
    # Material properties (matching original constants.py)
    materials = {
        1: {'name': 'active_0', 'stiffness': 500.0, 'damping': 1.2, 'density': 200.0, 'color': '0 1 0 0.6', 'phase': 0.0},
        2: {'name': 'active_180', 'stiffness': 500.0, 'damping': 1.2, 'density': 200.0, 'color': '1 0 0 0.6', 'phase': 3.14159},
        3: {'name': 'soft_passive', 'stiffness': 72.17, 'damping': 0.723, 'density': 200.0, 'color': '0 1 1 0.6', 'phase': None},
        4: {'name': 'stiff_passive', 'stiffness': 500.0, 'damping': 5.0, 'density': 200.0, 'color': '0 0 1 0.6', 'phase': None}
    }

    # Find all voxels
    voxels = []
    actuators = []

    for x in range(voxel_grid.shape[0]):
        for y in range(voxel_grid.shape[1]):
            for z in range(voxel_grid.shape[2]):
                material_id = int(voxel_grid[x, y, z])
                if material_id == 0:
                    continue

                mat = materials[material_id]
                pos = np.array([x, y, z]) * voxel_size

                # Calculate mass from density and volume
                volume = voxel_size ** 3
                mass = mat['density'] * volume

                voxel_info = {
                    'id': len(voxels),
                    'pos': pos,
                    'material': mat,
                    'material_id': material_id,
                    'mass': mass
                }
                voxels.append(voxel_info)

    if len(voxels) == 0:
        raise ValueError("No voxels in grid!")

    # Center the robot horizontally (X, Y) and place bottom at Z=0 + initial_height
    positions = np.array([v['pos'] for v in voxels])
    center_xy = np.mean(positions[:, :2], axis=0)  # Only X and Y
    min_z = np.min(positions[:, 2])  # Lowest Z coordinate

    for voxel in voxels:
        # Center X and Y, shift Z so bottom is at ground level (Z=0) + initial_height
        voxel['pos'][0] -= center_xy[0]
        voxel['pos'][1] -= center_xy[1]
        voxel['pos'][2] -= min_z
        voxel['pos'][2] += voxel_size / 2.0  # Add half voxel size so bottom sits on Z=0
        voxel['pos'][2] += initial_height     # Add initial height offset

    # Build XML
    half_size = voxel_size / 2.0

    xml_parts = [
        '<mujoco model="voxel_robot">',
        '  <option timestep="0.0005" gravity="0 0 -9.81"/>',
        '',
        '  <visual>',
        '    <headlight diffuse="0.6 0.6 0.6" ambient="0.5 0.5 0.5" specular="0 0 0"/>',
        '    <rgba haze="0.95 0.95 0.9 1"/>',
        '    <global offwidth="1920" offheight="1080"/>',
        '    <quality shadowsize="4096"/>',
        '    <map force="0.1" znear="0.01"/>',
        '  </visual>',
        '',
        '  <asset>',
        '    <texture name="grid" type="2d" builtin="checker" width="512" height="512"',
        '             rgb1="0.7 0.75 0.8" rgb2="0.85 0.88 0.9"/>',
        '    <material name="grid" texture="grid" texrepeat="10 10" texuniform="true" reflectance="0.1"/>',
        '  </asset>',
        '',
        '  <worldbody>',
        '    <!-- Checkered ground plane with collision -->',
        '    <geom name="ground" type="plane" size="1 1 0.1" material="grid" friction="1 0.005 0.0001" condim="3"/>',
        '    ',
        '    <!-- Red origin marker -->',
        '    <geom name="origin_marker" type="sphere" size="0.005" pos="0 0 0" rgba="1 0 0 1" contype="0" conaffinity="0"/>',
        '    ',
        '    <!-- XYZ Axis indicators: X=Red, Y=Green, Z=Blue (UP!) -->',
        '    <geom name="x_axis" type="capsule" fromto="0 0 0 0.05 0 0" size="0.001" rgba="1 0 0 0.8" contype="0" conaffinity="0"/>',
        '    <geom name="y_axis" type="capsule" fromto="0 0 0 0 0.05 0" size="0.001" rgba="0 1 0 0.8" contype="0" conaffinity="0"/>',
        '    <geom name="z_axis" type="capsule" fromto="0 0 0 0 0 0.05" size="0.001" rgba="0 0 1 0.8" contype="0" conaffinity="0"/>',
        '    ',
        '    <!-- Lighting -->',
        '    <light pos="0 1 1" dir="0 -1 -0.5" diffuse="0.8 0.8 0.8"/>',
        '    <light pos="0.5 1 0" dir="-0.5 -1 0" diffuse="0.4 0.4 0.4"/>',
        ''
    ]

    # Add each voxel as a body with joints
    for i, voxel in enumerate(voxels):
        x, y, z = voxel['pos']
        mat = voxel['material']

        # All voxels need free joints to be able to move
        # They are connected via equality constraints (soft springs)
        joint_type = 'free'

        xml_parts.append(f'    <body name="voxel_{i}" pos="{x:.6f} {y:.6f} {z:.6f}">')

        # Add box geometry with collision properties
        xml_parts.append(f'      <geom name="geom_{i}" type="box" size="{half_size} {half_size} {half_size}" '
                        f'rgba="{mat["color"]}" mass="{voxel["mass"]:.6f}" friction="1 0.005 0.0001" condim="3"/>')

        # Each voxel gets its own free joint so it can move
        xml_parts.append(f'      <joint name="joint_{i}" type="{joint_type}"/>')

        xml_parts.append(f'    </body>')

    xml_parts.append('')
    xml_parts.append('  </worldbody>')
    xml_parts.append('')

    # Use equality constraints to connect voxels
    # Connect via edges, face diagonals, and space diagonals for full structural integrity
    xml_parts.append('  <equality>')

    # Calculate connection distances
    edge_dist = voxel_size  # Face-adjacent (edge neighbors)
    face_diag_dist = voxel_size * np.sqrt(2)  # Face diagonal
    space_diag_dist = voxel_size * np.sqrt(3)  # Space diagonal

    for i, v1 in enumerate(voxels):
        for j, v2 in enumerate(voxels):
            if j <= i:
                continue

            # Check distance between voxels
            dist = np.linalg.norm(v1['pos'] - v2['pos'])
            tolerance = voxel_size * 0.01  # 1% tolerance

            # Determine connection type and stiffness
            connection_type = None
            solref = None

            if abs(dist - edge_dist) < tolerance:
                # Edge connection (face-adjacent neighbors)
                connection_type = "edge"
                solref = "0.02 1"  # Stiff springs for edges
            elif abs(dist - face_diag_dist) < tolerance:
                # Face diagonal connection
                connection_type = "face_diag"
                solref = "0.03 1"  # Slightly softer for diagonals
            elif abs(dist - space_diag_dist) < tolerance:
                # Space diagonal connection
                connection_type = "space_diag"
                solref = "0.04 1"  # Even softer for space diagonals

            if connection_type:
                xml_parts.append(f'    <connect body1="voxel_{i}" body2="voxel_{j}" '
                               f'anchor="0 0 0" solimp="0.9 0.95 0.001" solref="{solref}"/>')

    xml_parts.append('  </equality>')
    xml_parts.append('')
    xml_parts.append('</mujoco>')

    return '\n'.join(xml_parts)


def create_simple_test_xml() -> str:
    """Create a simple test case: single voxel cube"""
    voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
    voxel_grid[2, 1, 3] = 4  # Single stiff passive voxel
    return voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)


def create_4voxel_test_xml() -> str:
    """Create 4-voxel test case matching test_4voxel_simple.py"""
    voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
    voxel_grid[2, 1, 3] = 1  # Active 0°
    voxel_grid[3, 1, 3] = 2  # Active 180°
    voxel_grid[4, 1, 3] = 3  # Soft passive
    voxel_grid[5, 1, 3] = 4  # Stiff passive
    return voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)
