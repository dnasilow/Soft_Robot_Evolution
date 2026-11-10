"""Visualize MuJoCo physics: free fall, multiple voxels, and actuating robot"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_converter import voxel_to_mujoco_xml
from src.physics.mujoco_physics import MuJoCoPhysicsEngine

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

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01, initial_height=0.20)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# Robot starts 20cm above ground (specified in XML via initial_height parameter)
# Z is height in MuJoCo (gravity = [0, 0, -9.81])
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

xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01, initial_height=0.15)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# Robot starts 15cm above ground (specified in XML via initial_height parameter)
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
# 4 voxels in a line, on ground level
voxel_grid[2, 1, 3] = 1  # Active 0 deg (green)
voxel_grid[3, 1, 3] = 2  # Active 180 deg (red)
voxel_grid[4, 1, 3] = 3  # Soft passive (cyan)
voxel_grid[5, 1, 3] = 4  # Stiff passive (blue)

# Use MuJoCoPhysicsEngine with actuation
print("\nActuation: Modulating constraint stiffness at 2Hz with 50% amplitude")
engine = MuJoCoPhysicsEngine(default_timestep=0.0005, actuation_frequency=2.0)
engine.actuation_amplitude = 0.50
engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.0)

start_time = time.time()
with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    # Camera for 4-voxel robot on ground
    mujoco.mj_forward(engine.model, engine.data)
    center_pos = np.mean([engine.data.xpos[i] for i in range(1, min(5, engine.model.nbody))], axis=0)
    viewer.cam.lookat[:] = center_pos
    viewer.cam.distance = 0.3
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -25

    # Enable contact visualization
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = True
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = True

    while time.time() - start_time < 10.0:
        engine.step()  # This applies actuation automatically
        viewer.sync()

        if not viewer.is_running():
            break

        time.sleep(0.001)

print("Test 3 complete!\n")

print("="*70)
print("ALL VISUALIZATIONS COMPLETE")
print("="*70)
print("\nImplementation Status:")
print("  ✓ Actuation: Implemented (stiffness modulation at 2Hz)")
print("  ✓ Contact visualization: Enabled (green points, force arrows)")
print("  ✓ MuJoCoPhysicsEngine: Implemented in src/physics/mujoco_physics.py")
print("\nNote: Actuation currently modulates constraint stiffness.")
print("      For stronger visible movement, consider actuator-based approach.")
print("="*70)
