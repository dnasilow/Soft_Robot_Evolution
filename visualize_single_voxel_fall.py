"""Simple visualization: Single voxel falling and bouncing"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_converter import voxel_to_mujoco_xml

print("="*70)
print("SINGLE VOXEL FREE FALL - Interactive Visualization")
print("="*70)
print("\nViewer Controls:")
print("  - Left-drag: Rotate camera")
print("  - Right-drag: Pan camera")
print("  - Scroll wheel: Zoom")
print("  - Double-click: Track the falling voxel")
print("  - ESC or close window: Exit")
print("\nThe voxel will fall from 30cm and bounce/settle on the ground.")
print("Window will stay open until you close it or press ESC.")
print("="*70)

# Create single voxel
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
voxel_grid[4, 4, 4] = 4  # Single stiff passive voxel (blue)

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# Position 30cm above ground for a nice drop
# Gravity is [0, -9.81, 0] which acts on Y axis
# So Y is UP/DOWN (height), not Z!
data.qpos[1] = 0.30  # Y position = HEIGHT

print("\nStarting visualization...")
print("Close the window or press ESC to exit.\n")

# Launch interactive viewer (runs indefinitely until closed)
with mujoco.viewer.launch_passive(model, data) as viewer:
    # Set camera to look at origin where axis markers are
    viewer.cam.lookat[0] = 0.0   # X
    viewer.cam.lookat[1] = 0.15  # Y (look halfway to voxel height)
    viewer.cam.lookat[2] = 0.0   # Z
    viewer.cam.distance = 0.6    # Distance from lookat point
    viewer.cam.azimuth = 45      # 45 degree angle
    viewer.cam.elevation = -30   # Look down to see origin and cube

    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()

        # Control frame rate (~60 FPS)
        time.sleep(0.001)

print("\nVisualization closed.")
print("="*70)
