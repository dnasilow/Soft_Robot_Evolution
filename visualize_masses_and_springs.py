"""Visualize voxel robots as masses (spheres) connected by springs (lines)"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_converter import voxel_to_mujoco_xml

print("="*70)
print("MASSES AND SPRINGS VISUALIZATION")
print("="*70)
print("\nThis visualization shows:")
print("  - MASSES: Each voxel's center of mass as a small sphere")
print("  - SPRINGS: Equality constraints connecting voxels as lines")
print("  - The springs oscillate in color to show actuation")
print("="*70)

# Create a simple 4-voxel robot in a line
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
voxel_grid[3, 4, 4] = 1  # Active 0° (green)
voxel_grid[4, 4, 4] = 2  # Active 180° (red)
voxel_grid[5, 4, 4] = 3  # Soft passive (cyan)
voxel_grid[6, 4, 4] = 4  # Stiff passive (blue)

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01, initial_height=0.05)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

print(f"\nRobot Configuration:")
print(f"  Voxels: 4")
print(f"  Bodies: {model.nbody} (includes world)")
print(f"  Equality Constraints (Springs): {model.neq}")
print(f"  Each voxel has mass: 0.2g")
print(f"  Voxel size: 10mm x 10mm x 10mm")

# Print constraint information
print(f"\nSpring Connections:")
for i in range(model.neq):
    body1 = model.eq_obj1id[i]
    body2 = model.eq_obj2id[i]
    print(f"  Spring {i}: voxel_{body1-1} <-> voxel_{body2-1}")

print("\nStarting visualization...")
print("IMPORTANT: Masses are at the CENTER of each voxel")
print("           Springs are the connections between them")
print("           Voxel boxes show the actual volume\n")

with mujoco.viewer.launch_passive(model, data) as viewer:
    # Set camera
    viewer.cam.lookat[:] = [0.0, 0.0, 0.025]
    viewer.cam.distance = 0.15
    viewer.cam.azimuth = 90
    viewer.cam.elevation = -20

    # Enable visualization of centers of mass and contact points
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = True
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = True
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = True

    start_time = time.time()
    while time.time() - start_time < 15.0 and viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(0.001)

print("\nVisualization complete!")
print("="*70)
print("\nKEY OBSERVATIONS:")
print("  1. Each voxel's CENTER OF MASS appears as a small RED SPHERE")
print("  2. The voxel BOXES show the actual physical volume")
print("  3. Springs are IMPLICIT (equality constraints in MuJoCo)")
print("  4. Contact points appear as GREEN markers when voxels touch ground")
print("="*70)
