"""
Demo 2: Three Cubes Drop (Connected)
=====================================
Three voxels in a line: Green (active) — Cyan (soft) — Blue (stiff).
All dropped from 20cm, connected by tendons.

Shows:
- All three fall together as one connected unit (tendons = internal springs)
- Active (green) tendons will start oscillating once settled
- Soft (cyan) segment deforms more than stiff (blue) segment
- The spring connections prevent the cubes from flying apart
"""
import numpy as np
import mujoco
import mujoco.viewer
import time
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics

print("=" * 60)
print("DEMO 2 — Three Cubes Drop (Connected by Tendons)")
print("=" * 60)
print("Row of 3 voxels:  Green(active) — Cyan(soft) — Blue(stiff)")
print("Connected by spatial tendons — they fall as one unit.")
print("After settling, active (green) tendons start breathing.")
print("Close the window to exit.")
print("=" * 60)

grid = np.zeros((5, 3, 3), dtype=np.int8)
grid[1, 1, 1] = 1   # Active 0deg (green)
grid[2, 1, 1] = 3   # Soft passive (cyan)
grid[3, 1, 1] = 4   # Stiff passive (blue)

engine = MuJoCoTendonPhysics(
    default_timestep=0.0005,
    actuation_frequency=10.0,
    actuation_amplitude=0.20,
)
engine.load_robot(grid, voxel_size=0.02, initial_height=0.25)

# Print tendon breakdown
edges       = [t for t in engine.tendon_info if t['connection_type'] == 'face']
active_t    = [t for t in engine.tendon_info if t['is_active']]
passive_t   = [t for t in engine.tendon_info if not t['is_active']]

# Compute kp values dynamically from actual tendon_info (no hardcoding)
kp_gc = next((t['kp'] for t in edges if {t['mat1'],t['mat2']}=={1,3}), None)
kp_cb = next((t['kp'] for t in passive_t if {t['mat1'],t['mat2']}=={3,4}), None)
kp_cc = next((t['kp'] for t in passive_t if t['mat1']==3 and t['mat2']==3), None)
kp_bb = next((t['kp'] for t in passive_t if t['mat1']==4 and t['mat2']==4), None)

print(f"\nVoxels: 3   |   Tendons: {len(engine.tendon_info)}")
print(f"Active tendons (green involved): {len(active_t)}")
print(f"  - green-cyan edge: kp={kp_gc}  (min of active=100, soft=50 → 50)")
print(f"Passive tendons (cyan-blue):    {len(passive_t)}")
print(f"  - cyan-blue kp={kp_cb}  (min rule: soft=50, stiff=100 → 50)")
print(f"Separation printed every 0.5s — watch it oscillate ~+-2mm (the breathing)\n")

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.12]
    viewer.cam.distance = 0.35
    viewer.cam.azimuth  = 20
    viewer.cam.elevation = -15
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    t_print    = 0.0
    sep_history = []

    while viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.0008)

        if engine.current_time - t_print >= 0.5:
            positions = engine.data.xpos[1:engine.model.nbody]
            zs  = [f"{p[2]*100:.1f}cm" for p in positions]
            sep = np.linalg.norm(positions[0] - positions[-1])
            sep_history.append(sep)

            if len(sep_history) > 1:
                osc_mm = (max(sep_history) - min(sep_history)) * 1000
                note = f"  <- green-cyan spring breathing +-{osc_mm:.1f}mm" if osc_mm > 0.5 else ""
            else:
                note = ""

            print(f"  t={engine.current_time:.1f}s  "
                  f"heights={zs}  "
                  f"green-blue sep={sep*100:.2f}cm{note}")
            t_print = engine.current_time
