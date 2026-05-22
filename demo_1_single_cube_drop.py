"""
Demo 1: Single Cube Drop with Bounce
======================================
One stiff-passive (blue) voxel dropped from 25cm with elastic contact.

Key parameters:
  solref="0.005 0.2"  → 5ms contact spring, damping ratio 0.2 (underdamped = bouncy)
  solimp="0.9 0.99 0.001" → high contact impedance (hard contact)
  friction = 0.3      → lower friction so energy isn't absorbed sideways

No tendons — single free body under gravity.
"""
import numpy as np
import mujoco
import mujoco.viewer
import time

# ── Minimal XML: one blue box, elastic contact, drop from 25 cm ──────────────
XML = """
<mujoco model="bounce_demo">
  <option timestep="0.0005" gravity="0 0 -9.81"/>

  <visual>
    <headlight diffuse="0.6 0.6 0.6" ambient="0.5 0.5 0.5" specular="0 0 0"/>
    <rgba haze="0.95 0.95 0.9 1"/>
    <map force="0.1" znear="0.005"/>
  </visual>

  <asset>
    <texture name="grid" type="2d" builtin="checker" width="512" height="512"
             rgb1="0.7 0.75 0.8" rgb2="0.85 0.88 0.9"/>
    <material name="grid" texture="grid" texrepeat="10 10" texuniform="true" reflectance="0.1"/>
  </asset>

  <default>
    <!-- elastic contact: low damping ratio = bouncy, solimp = hard contact -->
    <geom solref="0.004 0.15" solimp="0.9 0.99 0.001" condim="3"/>
  </default>

  <worldbody>
    <light pos="0 1 1" dir="0 -1 -0.5" diffuse="0.8 0.8 0.8"/>
    <geom name="ground" type="plane" size="1 1 0.1" material="grid"
          friction="0.3 0.005 0.0001"/>

    <!-- axis markers -->
    <geom name="x_axis" type="capsule" fromto="0 0 0 0.05 0 0"
          size="0.001" rgba="1 0 0 0.8" contype="0" conaffinity="0"/>
    <geom name="z_axis" type="capsule" fromto="0 0 0 0 0 0.05"
          size="0.001" rgba="0 0 1 0.8" contype="0" conaffinity="0"/>

    <!-- the cube: 2 cm, stiff-passive blue, dropped from 25 cm -->
    <body name="cube" pos="0 0 0.25">
      <freejoint name="cube_free"/>
      <geom name="cube_geom" type="box" size="0.01 0.01 0.01"
            rgba="0.1 0.1 0.9 0.85" mass="0.0016"/>
    </body>
  </worldbody>
</mujoco>
"""

print("=" * 60)
print("DEMO 1 — Single Cube Drop  (elastic contact)")
print("=" * 60)
print("One blue voxel (2 cm, 1.6 g) dropped from 25 cm.")
print("solref damping_ratio=0.15 → underdamped → bounces.")
print("Close the window to exit.")
print("=" * 60)

model = mujoco.MjModel.from_xml_string(XML)
data  = mujoco.MjData(model)

# index of cube body (1, worldbody is 0)
CUBE_BODY = 1

print(f"\nCube mass: {model.body_mass[CUBE_BODY]*1000:.1f} g  |  "
      f"half-size: {model.geom_size[1,0]*100:.0f} mm  |  "
      f"drop: 25 cm\n")

with mujoco.viewer.launch_passive(model, data) as viewer:
    viewer.cam.lookat[:] = [0.0, 0.0, 0.12]
    viewer.cam.distance  = 0.55
    viewer.cam.azimuth   = 30
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    last_print = -0.1
    t_hit      = None   # time of first ground contact
    bounces    = 0
    prev_vz    = 0.0
    sim_time   = 0.0
    dt         = 0.0005

    while viewer.is_running():
        mujoco.mj_step(model, data)
        sim_time += dt
        viewer.sync()
        time.sleep(0.0005)   # ~real-time (0.5ms step, 0.5ms sleep)

        z  = data.xpos[CUBE_BODY][2]        # height of cube centre
        vz = data.cvel[CUBE_BODY][5]        # z-velocity

        # Detect bounce (velocity switches from negative to positive near ground)
        if z < 0.03 and prev_vz < -0.01 and vz > 0.0:
            bounces += 1
            if t_hit is None:
                t_hit = sim_time
            peak_speed = abs(prev_vz)
            print(f"  BOUNCE {bounces}  t={sim_time:.3f}s  "
                  f"z={z*100:.1f}cm  speed={peak_speed:.2f}m/s")

        prev_vz = vz

        # Print height every 0.05 s
        if sim_time - last_print >= 0.05:
            phase = "FALLING" if vz < -0.05 else ("BOUNCING" if vz > 0.05 else "SETTLED")
            print(f"  t={sim_time:.2f}s  z={z*100:.1f}cm  vz={vz:+.2f}m/s  [{phase}]")
            last_print = sim_time

        if sim_time > 4.0:
            print(f"\nSimulation ended. Total bounces detected: {bounces}")
            print("Close window to exit.")
            while viewer.is_running():
                viewer.sync()
                time.sleep(0.05)
            break
