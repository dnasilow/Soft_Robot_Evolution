"""Debug script to understand body positioning"""
import numpy as np
from src.physics.mujoco_converter import voxel_to_mujoco_xml
import mujoco

# Create 3 stacked voxels (same as Test 2)
grid = np.zeros((8, 8, 8), dtype=np.int8)
grid[4, 3, 4] = 4  # Bottom
grid[4, 4, 4] = 3  # Middle
grid[4, 5, 4] = 4  # Top

xml = voxel_to_mujoco_xml(grid, 0.01)

# Find and print worldbody section
start = xml.find('<worldbody')
end = xml.find('</worldbody>') + 12
print("=== WORLDBODY XML ===")
print(xml[start:end])

# Create model and check initial positions
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)

print("\n=== INITIAL POSITIONS (after mj_forward) ===")
print(f"Number of bodies: {model.nbody}")
for i in range(model.nbody):
    print(f"Body {i}: xpos = {data.xpos[i]}")

print(f"\n=== QPOS (free joint state) ===")
print(f"qpos shape: {data.qpos.shape}")
print(f"qpos: {data.qpos[:7]}")  # First 7 = free joint

# Now set qpos[2] = 0.15 and see what happens
print("\n=== AFTER SETTING qpos[2] = 0.15 ===")
data.qpos[2] = 0.15
mujoco.mj_forward(model, data)
for i in range(model.nbody):
    print(f"Body {i}: xpos = {data.xpos[i]}")
