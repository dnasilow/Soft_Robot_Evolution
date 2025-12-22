"""Convert voxel robots to MuJoCo XML format"""
import numpy as np
from typing import Dict, List, Tuple

def voxel_to_mujoco_xml(voxel_grid: np.ndarray, voxel_size: float = 0.01) -> str:
    """
    Convert voxel grid to MuJoCo XML model

    Args:
        voxel_grid: 3D numpy array (X, Y, Z) with material IDs
                   0 = empty, 1 = Active 0°, 2 = Active 180°, 3 = Soft passive, 4 = Stiff passive
        voxel_size: Size of each voxel in meters (default 0.01m = 1cm)

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

    # Build XML
    half_size = voxel_size / 2.0

    xml_parts = [
        '<mujoco model="voxel_robot">',
        '  <option timestep="0.0005" gravity="0 -9.81 0"/>',
        '',
        '  <worldbody>',
        '    <!-- Ground plane -->',
        '    <geom name="ground" type="plane" size="10 10 0.1" rgba="0.9 0.9 0.9 1"/>',
        ''
    ]

    # Add each voxel as a body with joints
    for i, voxel in enumerate(voxels):
        x, y, z = voxel['pos']
        mat = voxel['material']

        # First voxel is free-floating (6-DOF), others connect via ball joints
        if i == 0:
            joint_type = 'free'
        else:
            joint_type = None  # Will add ball joints between voxels

        xml_parts.append(f'    <body name="voxel_{i}" pos="{x:.6f} {y:.6f} {z:.6f}">')

        # Add box geometry
        xml_parts.append(f'      <geom name="geom_{i}" type="box" size="{half_size} {half_size} {half_size}" '
                        f'rgba="{mat["color"]}" mass="{voxel["mass"]:.6f}"/>')

        if joint_type:
            xml_parts.append(f'      <joint name="root_joint" type="{joint_type}"/>')

        xml_parts.append(f'    </body>')

    xml_parts.append('')
    xml_parts.append('  </worldbody>')
    xml_parts.append('')

    # Use equality constraints to connect voxels (simpler than tendons for initial version)
    xml_parts.append('  <equality>')

    for i, v1 in enumerate(voxels):
        for j, v2 in enumerate(voxels):
            if j <= i:
                continue

            # Check if voxels are adjacent
            dist = np.linalg.norm(v1['pos'] - v2['pos'])

            # Edge connection
            if abs(dist - voxel_size) < voxel_size * 0.01:
                # Connect constraint maintains soft distance
                xml_parts.append(f'    <connect body1="voxel_{i}" body2="voxel_{j}" '
                               f'anchor="0 0 0" solimp="0.9 0.95 0.001" solref="0.02 1"/>')

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
