"""
Demo 1: Single Cube Drop
========================
One stiff-passive (blue) voxel dropped from 20cm.
Shows: gravity, ground contact, tendon-less free body.
A single voxel has NO tendons (tendons need 2 bodies).
It's purely a free rigid body — just falls and bounces.
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 60)
print("DEMO 1 — Single Cube Drop")
print("=" * 60)
print("One stiff-passive (blue) voxel, dropped from 20cm.")
print("NO tendons — pure free rigid body under gravity.")
print("Watch it fall, bounce, and settle.")
print("Close the window to exit.")
print("=" * 60)

grid = np.zeros((3, 3, 3), dtype=np.int8)
grid[1, 1, 1] = 4   # single stiff-passive voxel (blue)

engine = MuJoCoTendonPhysics(default_timestep=0.0005)
engine.load_robot(grid, voxel_size=0.02, initial_height=0.20)  # 2cm cube, 20cm up

print(f"\nVoxels: 1   |   Tendons: {len(engine.tendon_info)}   |   Height: 20cm")
print(f"Voxel size: 2cm cube   |   Mass: {engine.model.body_mass[1]*1000:.1f}g\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.12]
    viewer.cam.distance = 0.45
    viewer.cam.azimuth  = 30
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    t_print = 0.0
    while viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.0008)  # ~real-time

        if engine.current_time - t_print >= 0.5:
            z = engine.data.xpos[1][2]
            vz = engine.data.cvel[1][5] if engine.model.nbody > 1 else 0
            print(f"  t={engine.current_time:.1f}s   height={z*100:.1f}cm")
            t_print = engine.current_time
