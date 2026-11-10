"""
Test Material 3: Soft Passive - Pure 5x5x5 cube
NO actuation - should NOT oscillate
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_actuated_physics import MuJoCoActuatedPhysics

print("="*70)
print("MATERIAL 3 TEST: Soft Passive (Cyan)")
print("="*70)
print("\n5x5x5 cube - ALL voxels are Soft Passive")
print("NO actuation - This is the CONTROL test")
print("Expected: NO oscillation (just gravity settling)")
print("="*70)

# Create 5x5x5 cube - ALL Soft Passive
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(2, 7):
    for y in range(2, 7):
        for z in range(2, 7):
            voxel_grid[x, y, z] = 3  # All Soft Passive (cyan)

print(f"\nBuilding robot...")
engine = MuJoCoActuatedPhysics(default_timestep=0.0005, actuation_frequency=10.0)
engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.15)

print(f"  Voxels: {np.count_nonzero(voxel_grid)}")
print(f"  Springs: {engine.model.neq}")
print(f"  Note: No active materials - no actuation will occur")

print("\nStarting 15-second test...")
print("Should see NO oscillation (control test)\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.15]
    viewer.cam.distance = 0.30
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    # Settle
    for _ in range(2000):
        engine.step()
        viewer.sync()
        time.sleep(0.001)

    # Measure
    sizes = []
    start_time = time.time()
    step = 0

    while time.time() - start_time < 15.0 and viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.001)

        if step % 200 == 0:
            positions = np.array([engine.data.xpos[i] for i in range(1, engine.model.nbody)])
            min_pos = np.min(positions, axis=0)
            max_pos = np.max(positions, axis=0)
            size = np.linalg.norm(max_pos - min_pos)
            sizes.append(size)

            if step % 1000 == 0:
                if len(sizes) > 1:
                    variation = (max(sizes) - min(sizes)) / np.mean(sizes) * 100
                    print(f"  t={engine.current_time:.1f}s: Size={size*100:.2f}cm, Variation so far: ±{variation:.2f}%")

        step += 1

print("\n" + "="*70)
print("MATERIAL 3 RESULTS: Soft Passive (CONTROL)")
print("="*70)
if len(sizes) > 1:
    variation = (max(sizes) - min(sizes)) / np.mean(sizes) * 100
    print(f"Size variation: ±{variation:.2f}%")
    print(f"Min: {min(sizes)*100:.2f}cm")
    print(f"Max: {max(sizes)*100:.2f}cm")
    print(f"Avg: {np.mean(sizes)*100:.2f}cm")

    if variation > 0.5:
        print("\n⚠ Unexpected variation (should be near zero for passive material)")
    else:
        print("\n✓ Correct: No oscillation (as expected for passive material)")
print("="*70)
