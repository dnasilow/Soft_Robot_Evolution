# physics_bug_test.py - Find the physics engine bug

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot, MATERIALS
import cupy as cp

def test_physics_engine_bug():
    """Find why springs work in theory but not in physics engine"""
    
    print("="*60)
    print("PHYSICS ENGINE BUG DIAGNOSTIC")
    print("="*60)
    
    # Create same robot as diagnostic
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3  # Single light blue voxel
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Move robot to test position (same as test file)
    offset = np.array([1.0, 1.0, 1.0])
    for node in robot.nodes:
        node['position'] += offset
    
    # Check spring properties before physics
    springs = robot.get_springs()
    nodes = robot.get_nodes()
    
    print("1. ROBOT PROPERTIES (before physics):")
    print(f"   Nodes: {len(robot.nodes)}")
    print(f"   Springs: {len(robot.springs)}")
    print(f"   Total mass: {np.sum(nodes['mass']):.1f} kg")
    print(f"   Avg spring stiffness: {np.mean(springs['stiffness']):.1e} N/m")
    
    # Initialize physics engine with SAME settings as test
    physics_engine = CUDAPhysicsEngine(
        max_nodes=2000,
        max_springs=10000,
        default_timestep=0.001
    )
    
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    # Check what physics engine received
    print("\n2. PHYSICS ENGINE RECEIVED:")
    gpu_stiffness = cp.asnumpy(physics_engine.d_stiffnesses[:physics_engine.num_springs])
    gpu_masses = cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])
    
    print(f"   GPU spring stiffness: {gpu_stiffness[:5]}...")
    print(f"   GPU average stiffness: {np.mean(gpu_stiffness):.1e} N/m")
    print(f"   GPU total mass: {np.sum(gpu_masses):.1f} kg")
    
    # Check if values match
    original_avg = np.mean(springs['stiffness'])
    gpu_avg = np.mean(gpu_stiffness)
    ratio = gpu_avg / original_avg
    
    print(f"   Transfer ratio: {ratio:.3f}")
    if ratio < 0.9:
        print(f"   ❌ PROBLEM: GPU didn't receive correct stiffness!")
    else:
        print(f"   ✅ Transfer OK: GPU has correct stiffness")
    
    # Test static equilibrium (no motion, just forces)
    print("\n3. STATIC EQUILIBRIUM TEST:")
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)
    
    print(f"   Initial COM: [{initial_com[0]:.2f}, {initial_com[1]:.2f}, {initial_com[2]:.2f}]")
    
    # Run 1 physics step to see forces
    physics_engine.step(0.001)
    
    # Check what happened
    after_1_step = physics_engine.get_positions()
    step_1_com = robot.get_center_of_mass(after_1_step)
    displacement_1_step = step_1_com - initial_com
    
    print(f"   After 1 step: [{step_1_com[0]:.2f}, {step_1_com[1]:.2f}, {step_1_com[2]:.2f}]")
    print(f"   Displacement: [{displacement_1_step[0]:.4f}, {displacement_1_step[1]:.4f}, {displacement_1_step[2]:.4f}]")
    
    if abs(displacement_1_step[1]) > 0.01:  # More than 1cm in 1 step
        print(f"   ❌ UNSTABLE: Moved {displacement_1_step[1]*100:.1f}cm in 0.001s!")
        print(f"   This suggests physics instability or wrong force limits")
    else:
        print(f"   ✅ STABLE: Small movement per step")
    
    # Test longer simulation with monitoring
    print("\n4. MONITORED SIMULATION (100 steps = 0.1s):")
    
    positions_history = []
    force_history = []
    
    for step in range(100):
        # Record state before step
        pos = physics_engine.get_positions()
        forces = cp.asnumpy(physics_engine.d_forces[:physics_engine.num_nodes])
        
        com = robot.get_center_of_mass(pos)
        avg_force = np.mean(np.abs(forces))
        
        positions_history.append(com[1])  # Y coordinate
        force_history.append(avg_force)
        
        # Physics step
        physics_engine.step(0.001)
        
        # Check for explosion
        if np.any(np.abs(pos) > 100):
            print(f"   ❌ EXPLOSION at step {step}!")
            break
    
    # Analyze results
    positions_history = np.array(positions_history)
    force_history = np.array(force_history)
    
    total_fall = positions_history[0] - positions_history[-1]
    max_force = np.max(force_history)
    avg_force = np.mean(force_history)
    
    print(f"   Fall in 0.1s: {total_fall:.4f} m")
    print(f"   Max force: {max_force:.1f} N")
    print(f"   Avg force: {avg_force:.1f} N")
    
    # Expected vs actual
    expected_gravity_force = np.sum(gpu_masses) * 9.81  # Total gravity force
    print(f"   Expected gravity force: {expected_gravity_force:.1f} N")
    
    if max_force < expected_gravity_force * 0.1:
        print(f"   ❌ FORCE LIMITING: Max force {max_force:.1f}N << gravity {expected_gravity_force:.1f}N")
        print(f"   🔧 SOLUTION: Increase force limits in physics engine")
    elif avg_force < expected_gravity_force * 0.5:
        print(f"   ⚠️  FORCE DAMPING: Average force is too low")
    else:
        print(f"   ✅ FORCES OK: Reasonable force levels")
    
    # Check compression over time
    if len(positions_history) > 50:
        early_pos = np.mean(positions_history[:10])   # First 0.01s
        late_pos = np.mean(positions_history[-10:])   # Last 0.01s
        compression_rate = (early_pos - late_pos) / 0.1  # m/s
        
        print(f"\n5. COMPRESSION ANALYSIS:")
        print(f"   Compression rate: {compression_rate:.3f} m/s")
        print(f"   In 1 second: {compression_rate:.3f} m ({compression_rate*100:.1f}%)")
        
        if compression_rate > 0.5:  # More than 50cm/s compression
            print(f"   ❌ RAPID COLLAPSE: Will become pancake in {1.0/compression_rate:.1f}s")
        elif compression_rate > 0.1:
            print(f"   ⚠️  SLOW COLLAPSE: Significant compression happening")
        else:
            print(f"   ✅ STABLE: Minimal compression")

if __name__ == "__main__":
    test_physics_engine_bug()