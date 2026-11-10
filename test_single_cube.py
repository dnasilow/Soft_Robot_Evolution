"""Simple test: Single cube falling and settling on ground"""
import numpy as np
import mujoco
from src.physics.mujoco_converter import voxel_to_mujoco_xml

print("="*70)
print("SINGLE CUBE TEST - MuJoCo Physics")
print("="*70)

print("\nCreating MuJoCo model with single stiff passive voxel...")
voxel_grid = np.zeros((8, 8, 8), dtype=np.int8)
voxel_grid[4, 4, 4] = 4  # Single stiff passive voxel

initial_height = 0.05  # 5cm above ground
xml = voxel_to_mujoco_xml(voxel_grid, voxel_size=0.01, initial_height=initial_height)

# Load model
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

print(f"Model loaded successfully!")
print(f"  Bodies: {model.nbody}")
print(f"  Geoms: {model.ngeom}")
print(f"  Timestep: {model.opt.timestep}s")
print(f"  Gravity: {model.opt.gravity}")

# Robot starts 5cm above ground (specified in XML via initial_height parameter)
# qpos for free joint: [x, y, z, qw, qx, qy, qz]
# Z is height in MuJoCo (gravity = [0, 0, -9.81])

print(f"\nInitial height: {initial_height*100:.1f}cm")
print("\nSimulating 3 seconds...")

# Simulate
simulation_time = 3.0
timestep = 0.0005
steps = int(simulation_time / timestep)

for i in range(steps):
    mujoco.mj_step(model, data)

    # Print every 0.5 seconds
    if i % 1000 == 0:
        t = i * timestep
        h = data.qpos[2]  # Z position = HEIGHT
        print(f"  t={t:.2f}s: height={h*1000:6.2f}mm")

final_height = data.qpos[2]  # Z position = HEIGHT

print(f"\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"Initial height: {initial_height*1000:.1f}mm")
print(f"Final height:   {final_height*1000:.2f}mm")
print(f"\nCube settled on ground: {'YES' if abs(final_height*1000) < 15 else 'NO'}")
print("="*70)
