"""
Tendon Breathing Test — Material 1: Active 0deg (Green)
=========================================================
5x5x5 cube, all voxels Active 0deg.
ALL 1036 tendons oscillate IN PHASE at 10Hz.
Expected: strong uniform breathing — cube expands and contracts like a lung.
Watch the size pulsing. Terminal prints +-% oscillation live.
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 70)
print("BREATHING TEST — Material 1: Active 0deg (GREEN)")
print("All tendons phase=0  |  10Hz  |  +-20% rest length")
print("Expected: strong uniform pulsing (all voxels in phase)")
print("Close the window to exit.")
print("=" * 70)

grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(2, 7):
    for y in range(2, 7):
        for z in range(2, 7):
            grid[x, y, z] = 1

engine = MuJoCoTendonPhysics(
    default_timestep=0.0005,
    actuation_frequency=10.0,
    actuation_amplitude=0.20,
)
engine.load_robot(grid, voxel_size=0.01, initial_height=0.0)

print(f"\nVoxels: {np.count_nonzero(grid)}   |   Tendons: {len(engine.tendon_info)}")
print(f"Active tendons: {engine.num_active_tendons}   |   Passive: 0\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.03]
    viewer.cam.distance = 0.25
    viewer.cam.azimuth  = 45
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    # Settle 1 second
    for _ in range(2000):
        engine.step()
        viewer.sync()
        time.sleep(0.0003)

    sizes  = []
    t_prev = 0.0
    step   = 0

    while viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.0003)
        step += 1

        if step % 100 == 0:
            pos  = engine.data.xpos[1:engine.model.nbody]
            size = np.linalg.norm(np.max(pos, axis=0) - np.min(pos, axis=0))
            sizes.append(size)

            if len(sizes) > 2 and step % 500 == 0:
                var = (max(sizes) - min(sizes)) / np.mean(sizes) * 100
                print(f"  t={engine.current_time:.1f}s   size={size*100:.2f}cm   oscillation=+-{var:.1f}%")
