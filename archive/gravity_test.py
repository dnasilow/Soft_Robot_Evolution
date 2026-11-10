# gravity_test.py - Diagnose gravity problems

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def test_gravity_pure():
    """Test pure gravity without springs"""
    print("="*60)
    print("PURE GRAVITY TEST (No Springs)")
    print("="*60)
    
    # Create minimal robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3  # Single passive voxel
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Get robot properties
    nodes = robot.get_nodes()
    total_mass = np.sum(nodes['mass'])
    
    print(f"Test setup:")
    print(f"  Robot mass: {total_mass:.1f} kg")
    print(f"  Expected gravity force: {total_mass * 9.81:.1f} N")
    print(f"  Expected acceleration: 9.81 m/s²")
    
    # Initialize physics
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    # DISABLE SPRINGS to test pure gravity
    import cupy as cp
    physics_engine.d_stiffnesses.fill(0.0)  # No spring forces
    
    print(f"\nPhysics engine settings:")
    print(f"  Gravity: {physics_engine.gravity} m/s²")
    print(f"  Force limit: 50.0 N (PROBLEM: {total_mass * 9.81:.0f}N > 50N)")
    print(f"  Velocity limit: 10.0 m/s")
    print(f"  Velocity damping: 0.995 per step")
    
    # Get initial state
    initial_pos = physics_engine.get_positions()
    initial_y = np.mean(initial_pos[:, 1])
    
    print(f"\nStarting simulation:")
    print(f"  Initial height: {initial_y:.3f} m")
    print(f"  Expected free fall from 1m: {np.sqrt(2*1/9.81):.3f} seconds")
    
    # Track motion
    timestep = 0.001
    positions = []
    velocities = []
    forces = []
    times = []
    
    for step in range(1000):  # 1 second
        # Record state
        pos = physics_engine.get_positions()
        current_y = np.mean(pos[:, 1])
        
        # Get physics internals
        vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
        force = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
        current_vel_y = np.mean(vel[:, 1])
        current_force_y = np.mean(force[:, 1])
        
        positions.append(current_y)
        velocities.append(current_vel_y)
        forces.append(current_force_y)
        times.append(step * timestep)
        
        # Step physics
        physics_engine.step(timestep)
        
        # Print key moments
        if step in [0, 100, 500, 999]:  # 0s, 0.1s, 0.5s, 1.0s
            time_s = step * timestep
            print(f"  {time_s:.1f}s: Y={current_y:.3f}m, Vy={current_vel_y:.2f}m/s, Fy={current_force_y:.1f}N")
    
    # Analysis
    positions = np.array(positions)
    velocities = np.array(velocities)
    forces = np.array(forces)
    
    fall_distance = initial_y - positions[-1]
    max_velocity = np.max(np.abs(velocities))
    avg_force = np.mean(forces)
    
    print(f"\nResults after 1 second:")
    print(f"  Fall distance: {fall_distance:.3f} m")
    print(f"  Max velocity: {max_velocity:.2f} m/s")
    print(f"  Average force: {avg_force:.1f} N")
    
    # Expected vs actual
    expected_fall = 0.5 * 9.81 * 1.0**2  # s = 0.5*g*t²
    expected_velocity = 9.81 * 1.0  # v = g*t
    
    print(f"\nExpected (perfect gravity):")
    print(f"  Fall distance: {expected_fall:.3f} m")
    print(f"  Final velocity: {expected_velocity:.2f} m/s")
    
    # Diagnosis
    fall_ratio = fall_distance / expected_fall
    vel_ratio = max_velocity / expected_velocity
    force_ratio = abs(avg_force) / (total_mass * 9.81)
    
    print(f"\nDiagnosis:")
    print(f"  Fall ratio: {fall_ratio:.3f} (1.0 = perfect)")
    print(f"  Velocity ratio: {vel_ratio:.3f} (1.0 = perfect)")
    print(f"  Force ratio: {force_ratio:.3f} (1.0 = perfect)")
    
    if fall_ratio < 0.1:
        print(f"  ❌ GRAVITY BROKEN: Falling {100*fall_ratio:.1f}% of expected distance")
        print(f"  🔧 SOLUTION: Increase force limit from 50N to {total_mass * 9.81 * 2:.0f}N")
    elif fall_ratio < 0.8:
        print(f"  ⚠️  GRAVITY WEAK: Falling {100*fall_ratio:.1f}% of expected distance")
        print(f"  🔧 SOLUTION: Reduce damping or increase force limit")
    else:
        print(f"  ✅ GRAVITY WORKING: {100*fall_ratio:.1f}% of expected performance")
    
    return fall_ratio > 0.8

def fix_gravity_limits():
    """Show how to fix the gravity limits"""
    print("\n" + "="*60)
    print("GRAVITY FIX INSTRUCTIONS")
    print("="*60)
    
    print("In src/physics/cuda_physics.py, find this line (~180):")
    print("  force_limit_mask = force_magnitudes > 50.0")
    print("\nReplace with:")
    print("  force_limit_mask = force_magnitudes > 10000.0  # Much higher limit")
    print("\nAlso find this line (~188):")
    print("  self.d_velocities[active_slice] = self.d_velocities[active_slice] * 0.995 + accelerations * dt")
    print("\nReplace with:")
    print("  self.d_velocities[active_slice] = self.d_velocities[active_slice] * 0.999 + accelerations * dt")
    print("  # Less aggressive damping (0.1% instead of 0.5%)")
    
    print("\n🎯 Expected improvement:")
    print("  - Robot should fall much faster")
    print("  - More realistic physics behavior")
    print("  - Proper response to gravity")

if __name__ == "__main__":
    works = test_gravity_pure()
    if not works:
        fix_gravity_limits()
    else:
        print("\n✅ Gravity is working correctly!")