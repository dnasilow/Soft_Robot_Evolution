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
# NOTE: Using index 2 for height (like test_mujoco_stability.py)
data.qpos[2] = 0.30  # Height position

print("\nStarting visualization...")
print("Close the window or press ESC to exit.\n")

# Launch interactive viewer (runs indefinitely until closed)
with mujoco.viewer.launch_passive(model, data) as viewer:
    # Set camera closer to the action
    viewer.cam.distance = 0.3  # Much closer (default is ~2-3)
    viewer.cam.azimuth = 45    # 45 degree angle
    viewer.cam.elevation = -20  # Look down slightly
    viewer.cam.lookat[0] = 0.0  # Look at origin
    viewer.cam.lookat[1] = 0.1  # Slightly above ground
    viewer.cam.lookat[2] = 0.0

    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()

        # Control frame rate (~60 FPS)
        time.sleep(0.001)

print("\nVisualization closed.")
print("="*70)
