"""Visualize a 3x3x3 cube of voxels falling and settling"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_converter import voxel_to_mujoco_xml

print("="*70)
print("3×3×3 VOXEL CUBE - Interactive Visualization")
print("="*70)
print("\nViewer Controls:")
print("  - Left-drag: Rotate camera")
print("  - Right-drag: Pan camera")
print("  - Scroll wheel: Zoom")
print("  - Double-click: Track the cube")
print("  - ESC or close window: Exit")
print("\nA 3×3×3 cube (27 voxels) will fall from 25cm height.")
print("Watch it bounce, deform, and settle on the ground!")
print("="*70)

# Create 3×3×3 cube of stiff passive voxels
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)

for x in range(3, 6):  # 3x3x3 cube centered in grid
    for y in range(3, 6):
        for z in range(3, 6):
            voxel_grid[x, y, z] = 4  # Stiff passive (blue)

print(f"\nBuilding 3×3×3 cube (27 voxels)...")

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

print(f"Model created: {model.nbody} bodies, {model.neq} constraints")

# Position 25cm above ground
data.qpos[1] = 0.25  # Y position
data.qpos[3] = 1.0   # Quaternion w
# Add slight rotation for interesting dynamics
data.qpos[4] = 0.1   # Small x rotation
data.qpos[6] = 0.1   # Small z rotation

print("\nStarting visualization...")
print("Watch the soft-connected voxels deform on impact!")
print("Close the window or press ESC to exit.\n")

# Launch viewer
with mujoco.viewer.launch_passive(model, data) as viewer:
    # Set camera for better view of the cube
    mujoco.mj_forward(model, data)
    # Look at center of mass of all voxels
    center_pos = np.mean([data.xpos[i] for i in range(1, model.nbody)], axis=0)
    viewer.cam.lookat[:] = center_pos
    viewer.cam.distance = 0.6  # Closer view
    viewer.cam.azimuth = 130   # Good angle to see cube
    viewer.cam.elevation = -25  # Look down at the action

    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(0.001)

print("\nVisualization closed.")
print("="*70)
