"""
Tendon Breathing Test — Material 2: Active 180deg (Red)
=========================================================
5x5x5 cube, all voxels Active 180deg.
Phase = pi (opposite to Material 1).

When mat1 is expanding, mat2 is contracting, and vice versa.
This phase opposition is what drives locomotion in a mixed robot:
  left half = mat1, right half = mat2 → alternating push/pull → movement.

Same metric as mat1: average distance from COM (immune to rolling).
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 70)
print("BREATHING TEST — Material 2: Active 180deg (RED)")
print("All 1036 tendons: phase=pi, kp=100, +-20% rest length, 10Hz")
print("OPPOSITE phase to Material 1 — when green expands, red contracts.")
print("Metric: avg voxel distance from COM  (immune to rolling/tumbling)")
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
print(f"Active tendons: {engine.num_active_tendons}")
print(f"Actuation: sin(2*pi*10*t + pi)  ->  starts contracting, then expands\n")

def avg_spread(xpos, nbody):
    pos = xpos[1:nbody]
    com = np.mean(pos, axis=0)
    return float(np.mean(np.linalg.norm(pos - com, axis=1)))

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

    print("  [Settled — now measuring breathing]")
    print(f"  {'Time':>6}  {'AvgDist(cm)':>12}  {'Osc%':>8}  Notes")
    print("  " + "-"*50)

    spreads = []
    step = 0

    while viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.0003)
        step += 1

        # Sample every 17 steps = 8.5ms — NOT a multiple of the 100ms
        # cycle period, so we hit all phases of the oscillation.
        if step % 17 == 0:
            s = avg_spread(engine.data.xpos, engine.model.nbody)
            spreads.append(s)

            if len(spreads) > 10 and step % 500 == 0:
                var = (max(spreads) - min(spreads)) / np.mean(spreads) * 100
                note = ("BREATHING" if var > 10
                        else "weak" if var > 3
                        else "almost still")
                print(f"  {engine.current_time:6.1f}s  "
                      f"{s*100:12.3f}  "
                      f"{var:+7.1f}%  {note}")
