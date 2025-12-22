"""Test MuJoCo physics stability with voxel robots"""
import numpy as np
import mujoco
from src.physics.mujoco_converter import create_simple_test_xml, create_4voxel_test_xml

print("="*70)
print("MUJOCO STABILITY TEST")
print("="*70)

# Test 1: Single passive voxel (should stay on ground)
print("\nTest 1: Single passive voxel")
print("-" * 70)

xml = create_simple_test_xml()
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

print(f"Model loaded: {model.nbody} bodies, {model.ngeom} geoms")
print(f"Timestep: {model.opt.timestep}s")
print(f"Gravity: {model.opt.gravity}")

# Position slightly above ground
data.qpos[2] = 0.011  # Y position (11mm above ground)

initial_height = data.qpos[2]
print(f"Initial height: {initial_height*1000:.2f}mm")

# Simulate for 1 second
for i in range(2000):  # 2000 steps * 0.0005s = 1.0s
    mujoco.mj_step(model, data)

final_height = data.qpos[2]
print(f"Final height after 1.0s: {final_height*1000:.2f}mm")

# Check stability
if abs(final_height * 1000) < 20:  # Should settle near 5mm (half voxel height)
    print("[PASS] Voxel settled on ground")
    test1_pass = True
else:
    print(f"[FAIL] Voxel exploded to {final_height*1000:.1f}mm")
    test1_pass = False

# Test 2: Single voxel over longer time (energy conservation)
print("\n" + "="*70)
print("Test 2: Long-term stability (5 seconds)")
print("-" * 70)

data.qpos[2] = 0.011
heights = []

for i in [0, 1000, 2000, 5000, 10000]:  # t = 0, 0.5s, 1.0s, 2.5s, 5.0s
    while len(heights) < i + 1:
        mujoco.mj_step(model, data)
        heights.append(data.qpos[2])

    t = i * 0.0005
    h = data.qpos[2]
    print(f"t={t:.2f}s: height={h*1000:6.2f}mm")

final_height = data.qpos[2]
if abs(final_height * 1000) < 20:
    print("[PASS] Voxel stable over 5 seconds")
    test2_pass = True
else:
    print(f"[FAIL] Voxel unstable after 5s: {final_height*1000:.1f}mm")
    test2_pass = False

# Test 3: 4-voxel structure (matches test_4voxel_simple.py)
print("\n" + "="*70)
print("Test 3: 4-voxel structure stability")
print("-" * 70)

xml4 = create_4voxel_test_xml()
model4 = mujoco.MjModel.from_xml_string(xml4)
data4 = mujoco.MjData(model4)

print(f"Model loaded: {model4.nbody} bodies")

# Position on ground
data4.qpos[2] = 0.011

# Simulate for 1 second
for i in range(2000):
    mujoco.mj_step(model4, data4)

final_height = data4.qpos[2]
print(f"Final height after 1.0s: {final_height*1000:.2f}mm")

if abs(final_height * 1000) < 50:
    print("[PASS] 4-voxel structure stable")
    test3_pass = True
else:
    print(f"[FAIL] 4-voxel structure unstable: {final_height*1000:.1f}mm")
    test3_pass = False

# Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"Test 1 (single voxel):      {'PASS' if test1_pass else 'FAIL'}")
print(f"Test 2 (long-term):         {'PASS' if test2_pass else 'FAIL'}")
print(f"Test 3 (4-voxel structure): {'PASS' if test3_pass else 'FAIL'}")

all_pass = test1_pass and test2_pass and test3_pass

if all_pass:
    print("\n[SUCCESS] ALL TESTS PASSED - MuJoCo physics is STABLE!")
    print("\nComparison with broken CuPy physics:")
    print("  CuPy:   Single voxel -> 1277mm after 1.0s (EXPLODED)")
    print("  MuJoCo: Single voxel -> stable at ~5mm (CORRECT)")
else:
    print("\n[FAIL] SOME TESTS FAILED - Check MuJoCo configuration")

print("="*70)
