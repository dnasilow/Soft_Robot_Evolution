"""Test actuation system with visualization"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_physics import MuJoCoPhysicsEngine

print("="*70)
print("ACTUATION TEST - MuJoCo Physics with Sinusoidal Control")
print("="*70)

# Create 4-voxel robot: Active 0 deg, Active 180 deg, Soft passive, Stiff passive
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
voxel_grid[2, 0, 3] = 1  # Active 0 deg (green)
voxel_grid[3, 0, 3] = 2  # Active 180 deg (red)
voxel_grid[4, 0, 3] = 3  # Soft passive (cyan)
voxel_grid[5, 0, 3] = 4  # Stiff passive (blue)

print("\nCreating robot with actuation...")
print("  Material 1 (Green): Active 0 deg - oscillates at phase 0")
print("  Material 2 (Red): Active 180 deg - oscillates at phase pi")
print("  Material 3 (Cyan): Soft passive - no actuation")
print("  Material 4 (Blue): Stiff passive - no actuation")

# Create physics engine with increased actuation for better visibility
engine = MuJoCoPhysicsEngine(default_timestep=0.0005, actuation_frequency=10.0)
engine.actuation_amplitude = 0.80  # Increase to 80% for VERY visible actuation
engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.03)  # Start 3cm above ground

print(f"\nRobot loaded:")
print(f"  Bodies: {engine.model.nbody}")
print(f"  Constraints: {engine.model.neq}")
print(f"  Timestep: {engine.default_timestep}s")
print(f"  Actuation frequency: {engine.actuation_frequency} Hz")
print(f"  Actuation amplitude: +/-{engine.actuation_amplitude*100}%")

print("\nStarting visualization...")
print("Watch the robot oscillate with 10Hz sinusoidal actuation!")
print("Green and Red voxels should pulse (180 deg out of phase)")
print("Close window or press ESC to exit.\n")

# Launch viewer
with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    # Set camera to see the robot clearly
    viewer.cam.lookat[0] = 0.0    # Center of robot (horizontally centered)
    viewer.cam.lookat[1] = 0.0
    viewer.cam.lookat[2] = 0.015  # Look at robot height
    viewer.cam.distance = 0.12    # Closer view
    viewer.cam.azimuth = 45       # Angle to see actuation
    viewer.cam.elevation = -20    # Look slightly down

    # Simulate for 10 seconds
    start_time = time.time()
    while time.time() - start_time < 10.0 and viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.001)  # 60 FPS

print("\nSimulation complete!")
print(f"Final robot position: {engine.get_position()}")
print("="*70)
