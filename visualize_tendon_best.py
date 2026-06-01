"""
Visualize the best evolved soft robot from best_robot_tendon.pkl
"""
import pickle
import time
import numpy as np
import mujoco
import mujoco.viewer
from src.physics.mujoco_tendon_physics import MuJoCoTendonPhysics
from src.physics.mujoco_tendon_converter import count_active_tendons

PKL = "best_robot_tendon.pkl"

with open(PKL, "rb") as f:
    saved = pickle.load(f)

genome     = saved["genome"]
controller = saved.get("controller")
fitness    = saved.get("fitness", float("nan"))

num_voxels  = int((genome != 0).sum())
num_active  = count_active_tendons(genome)
mat_counts  = {m: int((genome == m).sum()) for m in range(1, 5)}

print("=" * 60)
print("BEST EVOLVED ROBOT")
print("=" * 60)
print(f"  Fitness      : {fitness:.4f} m")
print(f"  Voxels       : {num_voxels}")
print(f"  Active tendons: {num_active}")
print(f"  Material breakdown:")
mat_names = {1: "Active 0deg  (green)", 2: "Active 180deg (red)",
             3: "Soft passive (cyan)", 4: "Stiff passive (blue)"}
for m, name in mat_names.items():
    if mat_counts[m] > 0:
        print(f"    mat{m} {name}: {mat_counts[m]} voxels")
print("Close the viewer window to exit.")
print("=" * 60)

engine = MuJoCoTendonPhysics(
    default_timestep=0.0005,
    actuation_frequency=10.0,
    actuation_amplitude=0.08,
)
engine.load_robot(genome, voxel_size=0.01, initial_height=0.0)

if controller is not None:
    try:
        engine.set_controller(controller)
        print("Controller: loaded from file")
    except ValueError:
        print("Controller: size mismatch — using open-loop actuation")
else:
    print("Controller: none saved — using open-loop actuation")

# Centre the camera on the robot's starting position
start_com = np.mean(engine.data.xpos[1:engine.model.nbody], axis=0)

with mujoco.viewer.launch_passive(engine.model, engine.data) as viewer:
    viewer.cam.lookat[:] = start_com
    viewer.cam.distance  = 0.35
    viewer.cam.azimuth   = 45
    viewer.cam.elevation = -20
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_COM] = False

    # Settle
    for _ in range(1000):
        engine.step()
        viewer.sync()
        time.sleep(0.0002)

    print("\n  [Running — watch it move]")
    t_print = 0.0

    while viewer.is_running():
        engine.step()
        viewer.sync()
        time.sleep(0.0002)

        if engine.current_time - t_print >= 1.0:
            com = np.mean(engine.data.xpos[1:engine.model.nbody], axis=0)
            dist = float(np.linalg.norm(com[:2] - start_com[:2]))
            print(f"  t={engine.current_time:.1f}s  "
                  f"pos=({com[0]*100:.1f}, {com[1]*100:.1f}, {com[2]*100:.1f}) cm  "
                  f"dist_from_start={dist*100:.1f} cm")
            # Track camera behind the robot
            viewer.cam.lookat[:] = com
            t_print = engine.current_time
