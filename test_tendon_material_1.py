"""
Tendon Breathing Test — Material 1: Active 0deg (Green)
=========================================================
5x5x5 cube, all voxels Active 0deg.
ALL 1036 tendons oscillate IN PHASE at 10Hz, +-8% rest length.

Amplitude reduced from 0.20 to 0.08 so the cube stays roughly in
place on the ground instead of rolling away. Rolling is correct physics
(ground asymmetry) but makes the breathing hard to observe visually.
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 70)
print("BREATHING TEST — Material 1: Active 0deg (GREEN)")
print("All 1036 tendons: phase=0, kp=100, +-8% rest length, 10Hz")
print("Metric: avg voxel distance from COM  (immune to rolling/tumbling)")
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
    actuation_amplitude=0.08,
)
engine.load_robot(grid, voxel_size=0.01, initial_height=0.0)

print(f"\nVoxels: {np.count_nonzero(grid)}   |   Tendons: {len(engine.tendon_info)}")
print(f"Active tendons: {engine.num_active_tendons}")
print(f"Actuation: sin(2*pi*10*t + 0)  ->  ctrl oscillates +-8% around rest length\n")

def avg_spread(xpos, nbody):
    """Average distance of each voxel from their collective COM.
    Pure deformation metric — invariant to translation and rotation."""
    pos = xpos[1:nbody]                          # skip worldbody
    com = np.mean(pos, axis=0)
    return float(np.mean(np.linalg.norm(pos - com, axis=1)))

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.03]
    viewer.cam.distance = 0.25
    viewer.cam.azimuth  = 45
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    # Settle 1 second (actuation running)
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
        # (every 100 steps = 50ms = exactly half-period → zero-crossings only → aliasing)
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
