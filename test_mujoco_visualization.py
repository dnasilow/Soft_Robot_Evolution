"""Visualize MuJoCo physics: free fall, multiple voxels, and actuating robot"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_converter import voxel_to_mujoco_xml

print("="*70)
print("MUJOCO VISUALIZATION TESTS")
print("="*70)
print("\nViewer Controls:")
print("  - Left-drag: Rotate camera")
print("  - Right-drag: Pan camera")
print("  - Scroll wheel: Zoom")
print("  - Double-click: Track object")
print("  - ESC or close window: Move to next test")
print("\nEach test will run for 10 seconds (or until you press ESC)")
print("="*70)

# Test 1: Single voxel free fall
print("\n[Test 1] Single voxel free fall from 20cm")
print("Starting visualization...")

voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
voxel_grid[4, 4, 4] = 4  # Single stiff passive voxel

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# Position 20cm above ground
data.qpos[1] = 0.20  # Y position (free joint: x,y,z,qw,qx,qy,qz)
data.qpos[3] = 1.0   # Quaternion w component (identity rotation)

# Launch interactive viewer
start_time = time.time()
with mujoco.viewer.launch_passive(model, data) as viewer:
    # Set camera to look at voxel
    mujoco.mj_forward(model, data)
    viewer.cam.lookat[:] = data.xpos[1]
    viewer.cam.distance = 0.5
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -20

    # Simulation loop - run for at least 10 seconds
    while time.time() - start_time < 10.0:
        mujoco.mj_step(model, data)
        viewer.sync()

        # Exit if user closes window
        if not viewer.is_running():
            break

        # Small delay to control frame rate (~60 FPS)
        time.sleep(0.001)

print("Test 1 complete!\n")
input("Press ENTER to continue to Test 2...")

# Test 2: Three voxels stacked vertically falling
print("\n[Test 2] Three voxels stacked vertically falling from 15cm")
print("Starting visualization...")

voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
voxel_grid[4, 3, 4] = 4  # Bottom - Stiff passive (blue)
voxel_grid[4, 4, 4] = 3  # Middle - Soft passive (cyan)
voxel_grid[4, 5, 4] = 4  # Top - Stiff passive (blue)

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# Position higher up
data.qpos[1] = 0.15  # Y position
data.qpos[3] = 1.0   # Quaternion w

start_time = time.time()
with mujoco.viewer.launch_passive(model, data) as viewer:
    # Camera for 3 stacked voxels
    mujoco.mj_forward(model, data)
    viewer.cam.lookat[:] = data.xpos[1]
    viewer.cam.distance = 0.5
    viewer.cam.azimuth = 60
    viewer.cam.elevation = -15

    while time.time() - start_time < 10.0:
        mujoco.mj_step(model, data)
        viewer.sync()

        if not viewer.is_running():
            break

        time.sleep(0.001)

print("Test 2 complete!\n")
input("Press ENTER to continue to Test 3...")

# Test 3: Actuating soft robot on ground (4 voxels)
print("\n[Test 3] Actuating soft robot - 4 voxels with active materials")
print("GREEN = Active 0°, RED = Active 180°, CYAN = Soft passive, BLUE = Stiff passive")
print("Starting visualization...")

voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
# 4 voxels in a line, on ground level (Y=1)
voxel_grid[2, 1, 3] = 1  # Active 0° (green)
voxel_grid[3, 1, 3] = 2  # Active 180° (red)
voxel_grid[4, 1, 3] = 3  # Soft passive (cyan)
voxel_grid[5, 1, 3] = 4  # Stiff passive (blue)

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# Start on ground (default position)
data.qpos[3] = 1.0  # Quaternion w

print("\nNOTE: Actuation not yet implemented in this version.")
print("Robot will sit statically on ground. Next step: add sinusoidal actuation!")

start_time = time.time()
with mujoco.viewer.launch_passive(model, data) as viewer:
    # Camera for 4-voxel robot on ground
    mujoco.mj_forward(model, data)
    # Average position of first few voxels
    center_pos = np.mean([data.xpos[i] for i in range(1, min(5, model.nbody))], axis=0)
    viewer.cam.lookat[:] = center_pos
    viewer.cam.distance = 0.3
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -25

    while time.time() - start_time < 10.0:
        mujoco.mj_step(model, data)
        viewer.sync()

        if not viewer.is_running():
            break

        time.sleep(0.001)

print("Test 3 complete!\n")

print("="*70)
print("ALL VISUALIZATIONS COMPLETE")
print("="*70)
print("\nNext steps:")
print("  - Implement actuation (sinusoidal control of spring rest lengths)")
print("  - Add force sensors and contact visualization")
print("  - Create MuJoCoPhysicsEngine wrapper for evolution integration")
print("="*70)
