"""
Tendon Test - Material 2: Active 180deg
5x5x5 cube, all voxels Active 180deg (red)
Expected: Strong uniform breathing/pulsing at 10Hz (opposite phase to mat 1)
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 70)
print("TENDON TEST - Material 2: Active 180deg (Red)")
print("=" * 70)
print("\n5x5x5 cube - ALL voxels Active 180deg")
print("All tendons oscillate IN PHASE at 10Hz (opposite to Material 1)")
print("Expected: Strong uniform breathing/pulsing")
print("=" * 70)

voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(2, 7):
    for y in range(2, 7):
        for z in range(2, 7):
            voxel_grid[x, y, z] = 2  # Active 180deg

print("\nBuilding robot...")
engine = MuJoCoTendonPhysics(
    default_timestep=0.0005,
    actuation_frequency=10.0,
    actuation_amplitude=0.20,
)
engine.load_robot(voxel_grid, voxel_size=0.01, initial_height=0.0, kp=100)

print(f"  Voxels:   {np.count_nonzero(voxel_grid)}")
print(f"  Tendons:  {len(engine.tendon_info)}")
print(f"  Frequency: {engine.actuation_frequency}Hz")
print(f"  Amplitude: +-{engine.actuation_amplitude*100:.0f}%")

print("\nStarting 15-second test...")
print("Watch for breathing/pulsing motion!\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.05]
    viewer.cam.distance = 0.30
    viewer.cam.azimuth = 45
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    # Settle
    for _ in range(2000):
        engine.step()
        viewer.sync()
        time.sleep(0.001)

    sizes = []
    start_time = time.time()
    step = 0

    while time.time() - start_time < 15.0 and viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.001)

        if step % 200 == 0:
            positions = np.array([engine.data.xpos[i] for i in range(1, engine.model.nbody)])
            size = np.linalg.norm(np.max(positions, axis=0) - np.min(positions, axis=0))
            sizes.append(size)

            if step % 1000 == 0 and len(sizes) > 1:
                variation = (max(sizes) - min(sizes)) / np.mean(sizes) * 100
                print(f"  t={engine.current_time:.1f}s: size={size*100:.2f}cm  variation=+-{variation:.2f}%")

        step += 1

print("\n" + "=" * 70)
print("TENDON MATERIAL 2 RESULTS: Active 180deg")
print("=" * 70)
if len(sizes) > 1:
    variation = (max(sizes) - min(sizes)) / np.mean(sizes) * 100
    print(f"Size variation: +-{variation:.2f}%")
    print(f"Min: {min(sizes)*100:.2f}cm  Max: {max(sizes)*100:.2f}cm  Avg: {np.mean(sizes)*100:.2f}cm")
    if variation > 5:
        print("\n[PASS] STRONG oscillation detected!")
    elif variation > 2:
        print("\n[OK] Visible oscillation")
    elif variation > 0.5:
        print("\n[WEAK] Weak oscillation - check kp or amplitude")
    else:
        print("\n[FAIL] Almost no oscillation")
print("=" * 70)
