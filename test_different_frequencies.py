"""
Test different actuation frequencies to find optimal visual feedback

Tests: 1Hz, 2Hz, 4Hz, 8Hz
Shows which frequency gives best visible oscillation
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_actuated_physics import MuJoCoActuatedPhysics

print("="*70)
print("FREQUENCY COMPARISON TEST")
print("="*70)
print("\nTesting different actuation frequencies:")
print("  1Hz - Very slow (0.5s per cycle)")
print("  2Hz - Current default (0.25s per cycle)")
print("  4Hz - Faster (0.125s per cycle)")
print("  8Hz - Very fast (0.0625s per cycle)")
print("\nYou'll test each for 10 seconds. Press ENTER between tests.")
print("="*70)

# Create 3x3x3 cube for faster testing (smaller than 5x5x5)
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(3, 6):
    for y in range(3, 6):
        for z in range(3, 6):
            voxel_grid[x, y, z] = 1  # All Active 0° (green)

frequencies = [1.0, 2.0, 4.0, 8.0]

for freq in frequencies:
    print(f"\n{'='*70}")
    print(f"Testing {freq}Hz ({1.0/freq:.3f}s per cycle)")
    print(f"{'='*70}")

    input(f"Press ENTER to start {freq}Hz test...")

    # Create engine with this frequency
    engine = MuJoCoActuatedPhysics(default_timestep=0.0005, actuation_frequency=freq)
    engine.actuation_amplitude = 0.20  # ±20%
    engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.15)

    print(f"  Voxels: {np.count_nonzero(voxel_grid)}")
    print(f"  Springs: {engine.model.neq}")
    print(f"  Frequency: {freq}Hz")
    print(f"  Amplitude: ±{engine.actuation_amplitude*100}%")
    print(f"\nWatch for {1.0/freq:.3f}s breathing cycles...")

    with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
        # Camera setup
        viewer.cam.lookat[:] = [0.0, 0.0, 0.15]
        viewer.cam.distance = 0.25
        viewer.cam.azimuth = 45
        viewer.cam.elevation = -20

        # Enable COM visualization
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = True

        # Settle first
        for _ in range(2000):
            engine.step()
            viewer.sync()
            time.sleep(0.001)

        # Measure oscillation
        sizes = []
        start_time = time.time()
        step = 0

        print("\n  Measuring oscillation...")

        while time.time() - start_time < 10.0 and viewer.is_running():
            engine.step()
            viewer.sync()
            time.sleep(0.001)

            # Measure size every 100ms
            if step % 200 == 0:
                positions = np.array([engine.data.xpos[i] for i in range(1, engine.model.nbody)])
                min_pos = np.min(positions, axis=0)
                max_pos = np.max(positions, axis=0)
                size = np.linalg.norm(max_pos - min_pos)
                sizes.append(size)

            step += 1

    # Report results
    if len(sizes) > 1:
        variation = (max(sizes) - min(sizes)) / np.mean(sizes) * 100
        print(f"\n  Results for {freq}Hz:")
        print(f"    Size variation: ±{variation:.1f}%")
        print(f"    Min size: {min(sizes)*100:.2f}cm")
        print(f"    Max size: {max(sizes)*100:.2f}cm")

        if variation < 1.0:
            print(f"    ⚠️  Very weak oscillation")
        elif variation < 3.0:
            print(f"    ⚡ Weak but visible")
        elif variation < 8.0:
            print(f"    ✓  Good oscillation")
        else:
            print(f"    ✓✓ Strong oscillation!")

print(f"\n{'='*70}")
print("Testing complete!")
print("\nRecommendation based on results above:")
print("  - Choose frequency with strongest oscillation")
print("  - Typical range: 4-5Hz for soft robots")
print("  - Higher frequency = less time for damping to kill motion")
print("="*70)
