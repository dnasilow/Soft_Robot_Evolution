"""
5x5x5 Oscillating Cube with Proper ±20% Rest Length Modulation

This version uses the new actuated physics engine that modulates
rest lengths by ±20%, which should create MUCH more visible oscillation!
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_actuated_physics import MuJoCoActuatedPhysics

print("="*70)
print("5x5x5 OSCILLATING CUBE - Proper ±20% Rest Length Modulation")
print("="*70)
print("\nThis version implements REAL rest-length based actuation:")
print("  - Springs oscillate between 80% and 120% of rest length")
print("  - All voxels are Active 0° (oscillate in phase)")
print("  - Suspended in air to avoid friction")
print("  - Full diagonal spring connections for rigidity")
print("\nYou should see CLEAR, STRONG pulsing motion!")
print("="*70)

# Create 5x5x5 cube of all Active 0° material
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(2, 7):
    for y in range(2, 7):
        for z in range(2, 7):
            voxel_grid[x, y, z] = 1  # All Active 0° (green)

print(f"\nCreating 5x5x5 cube...")
print(f"  Total voxels: {np.count_nonzero(voxel_grid)}")
print(f"  Material: Active 0° (all springs oscillate in phase)")
print(f"  Actuation: ±20% REST LENGTH at 2Hz")
print(f"  Spring types: Edge + Face Diagonal + Space Diagonal")
print(f"  Initial position: Suspended 15cm above ground")

# Create actuated physics engine
engine = MuJoCoActuatedPhysics(default_timestep=0.0005, actuation_frequency=2.0)
engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.15)

print(f"\nRobot loaded:")
print(f"  Bodies: {engine.model.nbody}")
print(f"  Springs: {engine.model.neq}")
print(f"  Rest length modulation: ±{engine.actuation_amplitude*100:.0f}%")
print(f"  Initial distances recorded: {len(engine.initial_distances)}")

print("\nStarting visualization...")
print("Watch the cube BREATHE with ±20% size oscillation!")
print("Close window or press ESC to exit.\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    # Camera setup
    viewer.cam.lookat[:] = [0.0, 0.0, 0.15]
    viewer.cam.distance = 0.30
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -20

    # Enable visualizations
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = True
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = True

    # Settle for a moment
    print("Settling for 1 second...")
    for _ in range(2000):
        engine.step()
        viewer.sync()
        time.sleep(0.001)

    print("Now oscillating! Watch closely...")

    # Measure oscillation
    sizes = []
    times = []
    initial_size = None

    start_time = time.time()
    step = 0

    while time.time() - start_time < 20.0 and viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.001)

        # Measure every 0.1 seconds
        if step % 200 == 0:
            positions = np.array([engine.data.xpos[i] for i in range(1, engine.model.nbody)])
            min_pos = np.min(positions, axis=0)
            max_pos = np.max(positions, axis=0)
            size = np.linalg.norm(max_pos - min_pos)

            if initial_size is None:
                initial_size = size

            sizes.append(size)
            times.append(engine.current_time)

            if step % 1000 == 0:  # Print every 0.5s
                change_percent = ((size - initial_size) / initial_size) * 100
                print(f"  t={engine.current_time:.2f}s: Size={size*100:.2f}cm (change: {change_percent:+.1f}%)")

        step += 1

print("\nSimulation complete!")

if len(sizes) > 1:
    size_variation = max(sizes) - min(sizes)
    avg_size = np.mean(sizes)
    variation_percent = (size_variation / avg_size) * 100

    print(f"\nMeasured oscillation:")
    print(f"  Average cube size: {avg_size*100:.2f}cm")
    print(f"  Size variation: {size_variation*100:.2f}cm (±{variation_percent:.1f}%)")
    print(f"  Min size: {min(sizes)*100:.2f}cm")
    print(f"  Max size: {max(sizes)*100:.2f}cm")
    print(f"\nExpected: ±20% oscillation")
    print(f"Achieved: ±{variation_percent:.1f}% (should be much larger now!)")

print(f"\nFinal position: {engine.get_position()}")
print("="*70)
