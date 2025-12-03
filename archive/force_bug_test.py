# force_bug_test.py - Find where forces are disappearing

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
import cupy as cp

def debug_force_disappearing():
    """Find exactly where forces are disappearing"""
    
    print("="*60)
    print("FORCE DISAPPEARING BUG DIAGNOSTIC")
    print("="*60)
    
    # Create simple robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Initialize physics
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    print("1. INITIAL STATE:")
    print(f"   Gravity: {physics_engine.gravity} m/s²")
    print(f"   Nodes: {physics_engine.num_nodes}")
    print(f"   Springs: {physics_engine.num_springs}")
    
    # Check masses
    gpu_masses = cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])
    total_mass = np.sum(gpu_masses)
    expected_gravity_force = total_mass * physics_engine.gravity
    
    print(f"   Total mass: {total_mass:.1f} kg")
    print(f"   Expected gravity force: {expected_gravity_force:.1f} N")
    
    # STEP-BY-STEP FORCE TRACKING
    print("\n2. STEP-BY-STEP FORCE TRACKING:")
    
    # Start with clean state
    physics_engine.d_forces.fill(0)
    physics_engine.d_velocities.fill(0)
    
    print("   Step 2a: Forces after reset:")
    forces_after_reset = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    print(f"      Force sum: {np.sum(np.abs(forces_after_reset)):.1f} N (should be 0)")
    
    # Apply gravity manually (like in integrate_positions_vectorized)
    print("   Step 2b: Applying gravity manually...")
    active_slice = slice(0, physics_engine.num_nodes)
    physics_engine.d_forces[active_slice, 1] -= physics_engine.d_masses[active_slice] * physics_engine.gravity
    
    forces_after_gravity = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    gravity_force_applied = np.sum(np.abs(forces_after_gravity))
    
    print(f"      Force sum after gravity: {gravity_force_applied:.1f} N")
    print(f"      Y-forces: {forces_after_gravity[:, 1]}")
    
    if gravity_force_applied < expected_gravity_force * 0.9:
        print(f"      ❌ GRAVITY APPLICATION FAILED!")
        return
    else:
        print(f"      ✅ Gravity applied correctly")
    
    # Check force limiting
    print("   Step 2c: Testing force limiting...")
    force_magnitudes = cp.linalg.norm(physics_engine.d_forces[active_slice], axis=1)
    max_force_magnitude = cp.max(force_magnitudes)
    
    print(f"      Max force magnitude: {float(max_force_magnitude):.1f} N")
    
    # Apply the EXACT force limiting from your updated physics
    print("   Step 2d: Applying force limiting...")
    
    # Check current force limit setting
    print(f"      Checking current force limit logic...")
    
    # This is what your physics engine should be doing:
    force_limit = 5000.0  # From our earlier fix
    force_limit_mask = force_magnitudes > force_limit
    num_limited = cp.sum(force_limit_mask)
    
    print(f"      Force limit: {force_limit} N")
    print(f"      Forces over limit: {int(num_limited)}")
    
    if cp.any(force_limit_mask):
        print(f"      APPLYING FORCE LIMITING...")
        scale_factors = force_limit / (force_magnitudes + 1e-6)
        physics_engine.d_forces[active_slice][force_limit_mask] *= scale_factors[force_limit_mask, cp.newaxis]
    
    forces_after_limiting = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    force_after_limiting_sum = np.sum(np.abs(forces_after_limiting))
    
    print(f"      Force sum after limiting: {force_after_limiting_sum:.1f} N")
    
    if force_after_limiting_sum < gravity_force_applied * 0.1:
        print(f"      ❌ FORCE LIMITING DESTROYED FORCES!")
        print(f"      🔧 Force limit {force_limit}N is too low for gravity {expected_gravity_force:.1f}N")
    else:
        print(f"      ✅ Force limiting OK")
    
    # Test acceleration calculation
    print("   Step 2e: Testing acceleration calculation...")
    accelerations = physics_engine.d_forces[active_slice] / physics_engine.d_masses[active_slice, cp.newaxis]
    max_acceleration = cp.max(cp.linalg.norm(accelerations, axis=1))
    
    print(f"      Max acceleration: {float(max_acceleration):.1f} m/s²")
    print(f"      Expected gravity acceleration: 9.81 m/s²")
    
    if float(max_acceleration) < 1.0:
        print(f"      ❌ ACCELERATION TOO LOW: Something is capping forces")
    else:
        print(f"      ✅ Acceleration reasonable")
    
    # Test full physics step
    print("\n3. TESTING FULL PHYSICS STEP:")
    
    # Reset and do one complete step
    physics_engine.d_forces.fill(0)
    physics_engine.d_velocities.fill(0)
    
    print("   Running physics_engine.step(0.001)...")
    physics_engine.step(0.001)
    
    final_forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
    final_force_sum = np.sum(np.abs(final_forces))
    
    print(f"   Forces after complete step: {final_force_sum:.1f} N")
    
    if final_force_sum < 1.0:
        print(f"   ❌ STEP CLEARS ALL FORCES: Bug in step() method")
        print(f"   🔧 Forces are being zeroed at end of step")
    else:
        print(f"   ✅ Step preserves forces")
    
    # Check if forces are cleared at end
    print("\n4. CHECKING FORCE CLEARING:")
    print("   Forces should be cleared at end of integrate_positions_vectorized()")
    print(f"   Current forces: {final_force_sum:.1f} N (should be 0 if cleared)")
    
    if final_force_sum < 0.1:
        print(f"   ✅ Forces properly cleared (this is normal)")
        print(f"   ❌ BUT: This means forces during simulation were also ~0")
        print(f"   🔧 PROBLEM: Forces are being limited/capped to near-zero during simulation")
    
    print(f"\n🎯 DIAGNOSIS:")
    print(f"   The force limiting logic is too aggressive!")
    print(f"   Gravity force: {expected_gravity_force:.1f} N")
    print(f"   Current limit: {force_limit} N")
    if expected_gravity_force > force_limit:
        print(f"   ❌ LIMIT TOO LOW: {expected_gravity_force:.1f}N > {force_limit}N")
        print(f"   🔧 SOLUTION: Increase force limit to {expected_gravity_force * 2:.0f}N")

if __name__ == "__main__":
    debug_force_disappearing()