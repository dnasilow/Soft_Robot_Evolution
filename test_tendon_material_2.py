"""
Tendon Breathing Test — Material 2: Active 180deg (Red)
=========================================================
5x5x5 cube, all voxels Active 180deg.
ALL tendons oscillate at 10Hz with phase=PI.
Expected: same strong breathing as Material 1 but half-cycle offset.
(When mat1 expands, mat2 contracts — this opposition creates locomotion
 when the two materials are combined in one robot.)
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 70)
print("BREATHING TEST — Material 2: Active 180deg (RED)")
print("All tendons phase=pi  |  10Hz  |  +-20% rest length")
print("Expected: strong uniform pulsing (OPPOSITE phase to Material 1)")
print("Close the window to exit.")
print("=" * 70)

grid = np.zeros((8, 8, 8), dtype=np.int8)
for x in range(2, 7):
    for y in range(2, 7):
        for z in range(2, 7):
            grid[x, y, z] = 2

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

    for _ in range(2000):
        engine.step()
        viewer.sync()
        time.sleep(0.0003)

    sizes = []
    step  = 0
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
