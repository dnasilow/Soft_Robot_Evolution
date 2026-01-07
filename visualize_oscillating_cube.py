"""Visualize 5x5x5 cube with strong oscillation for clear actuation visualization"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_physics import MuJoCoPhysicsEngine

print("="*70)
print("OSCILLATING CUBE - 5x5x5 Active Material")
print("="*70)
print("\nThis demonstration creates a 5x5x5 cube (125 voxels) made entirely")
print("of Active 0° material (green). All springs oscillate IN PHASE at 2Hz.")
print("\nThe cube starts suspended in air to avoid ground friction.")
print("You should see CLEAR pulsing/breathing motion!")
print("="*70)

# Create 5x5x5 cube of all Active 0° material
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(2, 7):  # 5x5x5 cube
    for y in range(2, 7):
        for z in range(2, 7):
            voxel_grid[x, y, z] = 1  # All Active 0° (green)

print(f"\nCreating 5x5x5 cube...")
print(f"  Total voxels: {np.count_nonzero(voxel_grid)}")
print(f"  Material: Active 0° (all springs oscillate together)")
print(f"  Actuation: ±100% amplitude at 2Hz")
print(f"  Initial position: Suspended 20cm above ground")

# Create physics engine with VERY high actuation amplitude
engine = MuJoCoPhysicsEngine(default_timestep=0.0005, actuation_frequency=2.0)
engine.actuation_amplitude = 1.0  # 100% amplitude for maximum visibility!
engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.20)

print(f"\nRobot loaded:")
print(f"  Bodies: {engine.model.nbody}")
print(f"  Springs (constraints): {engine.model.neq}")
print(f"  Actuation amplitude: ±{engine.actuation_amplitude*100:.0f}%")
print(f"  This means springs oscillate from VERY SOFT to VERY STIFF")

print("\nStarting visualization...")
print("Watch the cube BREATHE - it should pulse in and out!")
print("Close window or press ESC to exit.\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    # Set camera to see the whole cube
    viewer.cam.lookat[:] = [0.0, 0.0, 0.20]  # Look at cube center
    viewer.cam.distance = 0.35  # Far enough to see whole cube
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -20

    # Enable center of mass visualization
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = True

    # Let it settle for a moment
    print("Letting cube settle for 2 seconds...")
    for _ in range(4000):  # 2 seconds
        engine.step()
        viewer.sync()
        time.sleep(0.001)

    print("Now watch the oscillation!")

    # Record some measurements
    initial_size = None
    sizes = []
    times = []

    start_time = time.time()
    step = 0
    while time.time() - start_time < 15.0 and viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.001)

        # Measure cube size every 0.1 seconds
        if step % 200 == 0:
            # Calculate bounding box size
            positions = np.array([engine.data.xpos[i] for i in range(1, engine.model.nbody)])
            min_pos = np.min(positions, axis=0)
            max_pos = np.max(positions, axis=0)
            size = np.linalg.norm(max_pos - min_pos)

            if initial_size is None:
                initial_size = size

            sizes.append(size)
            times.append(engine.current_time)

            if step % 1000 == 0:  # Print every 0.5 seconds
                change = ((size - initial_size) / initial_size) * 100
                print(f"  t={engine.current_time:.2f}s: Size={size*100:.2f}cm (change: {change:+.1f}%)")

        step += 1

print("\nSimulation complete!")

if len(sizes) > 0:
    size_variation = max(sizes) - min(sizes)
    avg_size = np.mean(sizes)
    variation_percent = (size_variation / avg_size) * 100
    print(f"\nMeasured oscillation:")
    print(f"  Average cube size: {avg_size*100:.2f}cm")
    print(f"  Size variation: {size_variation*100:.2f}cm (±{variation_percent:.1f}%)")
    print(f"  Min size: {min(sizes)*100:.2f}cm")
    print(f"  Max size: {max(sizes)*100:.2f}cm")

print(f"\nFinal robot position: {engine.get_position()}")
print("="*70)
