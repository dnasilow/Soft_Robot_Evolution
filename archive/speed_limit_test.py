# speed_limit_test.py - Find why speed is capped at 0.98 m/s

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
import cupy as cp

def diagnose_speed_limiting():
    """Find what's limiting speed to 0.98 m/s"""
    
    print("="*60)
    print("SPEED LIMITING BUG DIAGNOSTIC")
    print("="*60)
    
    # Create simple robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Initialize physics with YOUR EXACT SETTINGS
    physics_engine = CUDAPhysicsEngine(
        max_nodes=2000,
        max_springs=10000,
        default_timestep=0.0002  # Your fixed timestep
    )
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    print("1. PHYSICS ENGINE SETTINGS:")
    print(f"   Gravity: {physics_engine.gravity} m/s²")
    print(f"   Default timestep: {physics_engine.default_timestep} s")
    print(f"   Total mass: {np.sum(cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])):.1f} kg")
    
    # Simulate and track velocity limiting
    print("\n2. VELOCITY TRACKING (1000 steps = 0.2s):")
    
    velocities_history = []
    forces_history = []
    positions_history = []
    
    for step in range(1000):  # 0.2 seconds
        # Get current state BEFORE physics step
        positions = physics_engine.get_positions()
        velocities = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
        forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
        
        # Calculate speeds
        speeds = np.linalg.norm(velocities, axis=1)
        max_speed = np.max(speeds)
        avg_force = np.mean(np.abs(forces))
        
        com = robot.get_center_of_mass(positions)
        
        velocities_history.append(max_speed)
        forces_history.append(avg_force)
        positions_history.append(com[1])
        
        # Physics step
        physics_engine.step(0.0002)
        
        # Print key moments
        if step in [0, 100, 500, 999]:  # 0s, 0.02s, 0.1s, 0.2s
            expected_speed = 9.81 * (step * 0.0002)  # v = g*t for free fall
            print(f"   Step {step:4d} ({step*0.0002:.3f}s): Speed={max_speed:.3f} m/s, Expected={expected_speed:.3f} m/s, Y={com[1]:.3f}m")
            
            # Check for speed limiting
            if max_speed > 0.5 and abs(max_speed - velocities_history[-2]) < 0.001:
                print(f"      ⚠️  SPEED PLATEAU: Speed stopped increasing at {max_speed:.3f} m/s")
    
    # Analyze results
    velocities_history = np.array(velocities_history)
    forces_history = np.array(forces_history)
    positions_history = np.array(positions_history)
    
    max_speed_reached = np.max(velocities_history)
    final_speed = velocities_history[-1]
    expected_final_speed = 9.81 * 0.2  # After 0.2s: v = g*t = 1.96 m/s
    
    print(f"\n3. SPEED ANALYSIS:")
    print(f"   Max speed reached: {max_speed_reached:.3f} m/s")
    print(f"   Final speed: {final_speed:.3f} m/s")
    print(f"   Expected final speed: {expected_final_speed:.3f} m/s")
    print(f"   Speed ratio: {final_speed/expected_final_speed:.3f}")
    
    # Check for speed plateaus
    if len(velocities_history) > 100:
        speed_changes = np.diff(velocities_history[-100:])  # Last 100 steps
        avg_speed_change = np.mean(np.abs(speed_changes))
        
        print(f"   Speed change rate (last 100 steps): {avg_speed_change:.6f} m/s per step")
        
        if avg_speed_change < 0.001:
            print(f"   ❌ SPEED PLATEAU: Speed stopped changing (terminal velocity reached)")
            
            # Find where plateau started
            for i in range(len(velocities_history)-50, 0, -1):
                if abs(velocities_history[i] - velocities_history[-1]) > 0.1:
                    plateau_start = i * 0.0002
                    plateau_speed = velocities_history[-1]
                    print(f"   Plateau started at: {plateau_start:.3f}s at speed {plateau_speed:.3f} m/s")
                    break
        else:
            print(f"   ✅ STILL ACCELERATING: Speed continues to increase")
    
    # Check physics engine limits
    print(f"\n4. CHECKING PHYSICS ENGINE LIMITS:")
    
    # Manually check what limits are set in the integrate function
    # We need to look at the actual physics code
    
    # Test: Apply pure gravity without springs
    print(f"   Testing pure gravity (no springs)...")
    
    # Create new engine for pure gravity test
    gravity_engine = CUDAPhysicsEngine(max_nodes=10, max_springs=10)
    gravity_engine.reset()
    
    # Add single node with mass
    single_node_robot = VoxelRobot(np.zeros((3,3,3), dtype=np.int8), voxel_size=1.0)
    single_node_robot.nodes = [{'position': np.array([0, 2, 0], dtype=np.float32), 'mass': 20.0, 'index': 0}]
    single_node_robot.springs = []  # No springs
    
    # Add to physics (manual approach)
    gravity_engine.num_nodes = 1
    gravity_engine.d_positions[0] = cp.array([0, 2, 0], dtype=cp.float32)
    gravity_engine.d_masses[0] = 20.0
    gravity_engine.d_velocities[0] = cp.array([0, 0, 0], dtype=cp.float32)
    
    print(f"   Pure gravity test (single node, no springs):")
    
    for step in range(500):  # 0.1s
        gravity_engine.step(0.0002)
        
        if step in [99, 199, 299, 499]:  # Print every 0.02s
            vel = cp.asnumpy(gravity_engine.d_velocities[0])
            speed = np.linalg.norm(vel)
            expected = 9.81 * (step + 1) * 0.0002
            
            print(f"      {(step+1)*0.0002:.3f}s: Speed={speed:.3f} m/s, Expected={expected:.3f} m/s")
            
            if speed < expected * 0.9:
                print(f"         ❌ VELOCITY DAMPING: {speed:.3f} < {expected:.3f}")
            elif speed > expected * 1.1:
                print(f"         ❌ VELOCITY BOOST: {speed:.3f} > {expected:.3f}")
            else:
                print(f"         ✅ CORRECT GRAVITY")
    
    final_gravity_speed = np.linalg.norm(cp.asnumpy(gravity_engine.d_velocities[0]))
    expected_gravity_speed = 9.81 * 0.1
    
    print(f"\n5. DIAGNOSIS:")
    print(f"   Pure gravity final speed: {final_gravity_speed:.3f} m/s")
    print(f"   Expected gravity speed: {expected_gravity_speed:.3f} m/s")
    print(f"   Gravity ratio: {final_gravity_speed/expected_gravity_speed:.3f}")
    
    if final_gravity_speed < expected_gravity_speed * 0.9:
        print(f"   ❌ VELOCITY DAMPING in physics engine")
        print(f"   🔧 Check: integrate_positions_vectorized() damping factor")
    elif max_speed_reached < 1.5:
        print(f"   ❌ SPRING RESISTANCE too high") 
        print(f"   🔧 Springs creating artificial terminal velocity")
    else:
        print(f"   ⚠️  Complex interaction between springs and gravity")

def check_physics_limits():
    """Check current physics engine limits"""
    print(f"\n" + "="*60)
    print("CHECKING CURRENT PHYSICS LIMITS")
    print("="*60)
    
    # This would check the actual values in the physics engine
    print("To find the exact limits, check src/physics/cuda_physics.py:")
    print("1. Line ~180: force_limit_mask = force_magnitudes > ????")
    print("2. Line ~188: velocity damping factor: * 0.???")  
    print("3. Line ~194: vel_limit_mask = vel_magnitudes > ????")
    
    print("\nYour fixes should have:")
    print("1. Force limit: 5000+ N (was 50N)")
    print("2. Velocity damping: 0.998+ (was 0.995)")
    print("3. Velocity limit: 20+ m/s (was 10 m/s)")
    
    print("\nIf speed is still capped at 0.98 m/s:")
    print("❌ One of these limits is still too restrictive")
    print("❌ OR there's a different limit we haven't found")

if __name__ == "__main__":
    diagnose_speed_limiting()
    check_physics_limits()