# spring_model_debug.py - Find why springs cause expansion instead of equilibrium

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
import cupy as cp

def debug_spring_model():
    """Debug why springs cause expansion instead of compression resistance"""
    
    print("="*60)
    print("SPRING MODEL BUG DIAGNOSTIC")
    print("="*60)
    
    # Create simple robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Move to test position
    offset = np.array([1.0, 1.0, 1.0])
    for node in robot.nodes:
        node['position'] += offset
    
    # Initialize physics with HIGH force limit (the problematic setting)
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100, default_timestep=0.0002)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    print("1. INITIAL SPRING STATE:")
    
    # Get initial spring state
    initial_positions = physics_engine.get_positions()
    rest_lengths = cp.asnumpy(physics_engine.d_rest_lengths[:physics_engine.num_springs])
    spring_stiffnesses = cp.asnumpy(physics_engine.d_stiffnesses[:physics_engine.num_springs])
    
    # Calculate initial spring lengths
    initial_spring_lengths = []
    spring_node1 = cp.asnumpy(physics_engine.d_spring_node1[:physics_engine.num_springs])
    spring_node2 = cp.asnumpy(physics_engine.d_spring_node2[:physics_engine.num_springs])
    
    for i in range(physics_engine.num_springs):
        pos1 = initial_positions[spring_node1[i]]
        pos2 = initial_positions[spring_node2[i]]
        length = np.linalg.norm(pos2 - pos1)
        initial_spring_lengths.append(length)
    
    initial_spring_lengths = np.array(initial_spring_lengths)
    
    print(f"   Number of springs: {physics_engine.num_springs}")
    print(f"   Rest lengths: min={np.min(rest_lengths):.3f}, max={np.max(rest_lengths):.3f}, avg={np.mean(rest_lengths):.3f}")
    print(f"   Current lengths: min={np.min(initial_spring_lengths):.3f}, max={np.max(initial_spring_lengths):.3f}, avg={np.mean(initial_spring_lengths):.3f}")
    
    # Check if springs are initially compressed/extended
    extensions = initial_spring_lengths - rest_lengths
    print(f"   Extensions: min={np.min(extensions):.6f}, max={np.max(extensions):.6f}, avg={np.mean(extensions):.6f}")
    
    if np.max(np.abs(extensions)) > 0.001:
        print(f"   ⚠️  SPRINGS NOT AT REST: Initial extensions up to {np.max(np.abs(extensions)):.3f}m")
    else:
        print(f"   ✅ Springs at rest initially")
    
    print(f"\n2. STEP-BY-STEP SPRING FORCE ANALYSIS:")
    
    # Manually simulate a few steps with detailed logging
    for step in range(5):
        print(f"\n   Step {step}:")
        
        # Get current state
        positions = physics_engine.get_positions()
        com = robot.get_center_of_mass(positions)
        
        # Calculate current spring lengths and forces MANUALLY
        current_lengths = []
        manual_spring_forces = []
        
        for i in range(physics_engine.num_springs):
            pos1 = positions[spring_node1[i]]
            pos2 = positions[spring_node2[i]]
            current_length = np.linalg.norm(pos2 - pos1)
            current_lengths.append(current_length)
            
            # Manual spring force calculation (same as physics engine)
            extension = current_length - rest_lengths[i]
            spring_force_magnitude = spring_stiffnesses[i] * extension
            manual_spring_forces.append(spring_force_magnitude)
        
        current_lengths = np.array(current_lengths)
        manual_spring_forces = np.array(manual_spring_forces)
        
        # Check spring force directions
        expansion_forces = np.sum(manual_spring_forces[manual_spring_forces > 0])  # Forces pushing outward
        compression_forces = np.sum(manual_spring_forces[manual_spring_forces < 0])  # Forces pulling inward
        
        avg_extension = np.mean(current_lengths - rest_lengths)
        total_spring_force = np.sum(np.abs(manual_spring_forces))
        
        print(f"      COM: [{com[0]:.3f}, {com[1]:.3f}, {com[2]:.3f}]")
        print(f"      Avg spring length: {np.mean(current_lengths):.6f}m (rest: {np.mean(rest_lengths):.6f}m)")
        print(f"      Avg extension: {avg_extension:.6f}m")
        print(f"      Expansion forces: {expansion_forces:.1f} N")
        print(f"      Compression forces: {compression_forces:.1f} N")
        print(f"      Net force: {expansion_forces + compression_forces:.1f} N")
        print(f"      Total spring force: {total_spring_force:.1f} N")
        
        # Analyze force balance
        gravity_force = 160.0 * 9.81  # 1569 N downward
        net_spring_force = expansion_forces + compression_forces
        
        if avg_extension > 0.001:  # Robot expanding
            print(f"      🎈 ROBOT EXPANDING: Avg extension +{avg_extension*1000:.1f}mm")
            if expansion_forces > abs(compression_forces):
                print(f"         Problem: Expansion forces ({expansion_forces:.1f}N) > Compression forces ({abs(compression_forces):.1f}N)")
        elif avg_extension < -0.001:  # Robot compressing
            print(f"      🗜️  ROBOT COMPRESSING: Avg compression {-avg_extension*1000:.1f}mm")
            if abs(compression_forces) > expansion_forces:
                print(f"         Problem: Compression forces ({abs(compression_forces):.1f}N) > Expansion forces ({expansion_forces:.1f}N)")
        else:
            print(f"      ✅ ROBOT STABLE: Minimal extension/compression")
        
        # Check for force balance
        if abs(net_spring_force) > gravity_force:
            print(f"      ❌ FORCE IMBALANCE: Net spring force ({abs(net_spring_force):.1f}N) > Gravity ({gravity_force:.1f}N)")
            print(f"         This will cause uncontrolled motion!")
        
        # Take physics step
        physics_engine.step(0.0002)
        
        # Check for explosion
        new_positions = physics_engine.get_positions()
        movement = np.max(np.linalg.norm(new_positions - positions, axis=1))
        if movement > 0.01:  # More than 1cm movement in 0.0002s
            print(f"      💥 EXPLOSION DETECTED: Max node movement {movement*100:.1f}cm in 0.0002s")
            break
    
    print(f"\n3. ROOT CAUSE ANALYSIS:")
    
    # Check for common spring model bugs
    print(f"   Checking for common spring model bugs...")
    
    # Bug 1: Sign error in force application
    print(f"   Bug check 1: Force direction")
    print(f"      Springs under compression should push outward (resist compression)")
    print(f"      Springs under tension should pull inward (resist stretching)")
    
    # Bug 2: Rest length corruption
    print(f"   Bug check 2: Rest length stability")
    final_rest_lengths = cp.asnumpy(physics_engine.d_rest_lengths[:physics_engine.num_springs])
    rest_length_change = np.max(np.abs(final_rest_lengths - rest_lengths))
    if rest_length_change > 0.001:
        print(f"      ❌ REST LENGTHS CHANGED: Max change {rest_length_change:.6f}m")
        print(f"         Something is modifying rest lengths during simulation!")
    else:
        print(f"      ✅ Rest lengths stable")
    
    # Bug 3: Actuator interference
    print(f"   Bug check 3: Actuator interference")
    if physics_engine.num_actuators > 0:
        print(f"      ❌ ACTUATORS ACTIVE: {physics_engine.num_actuators} actuators might modify springs")
    else:
        print(f"      ✅ No actuators active")
    
    # Bug 4: Numerical instability
    print(f"   Bug check 4: Numerical stability")
    max_stiffness = np.max(spring_stiffnesses)
    min_mass = 20.0  # Approximate node mass
    critical_timestep = 0.1 / np.sqrt(max_stiffness / min_mass)
    current_timestep = 0.0002
    
    print(f"      Max spring stiffness: {max_stiffness:.1e} N/m")
    print(f"      Critical timestep: {critical_timestep:.6f} s")
    print(f"      Current timestep: {current_timestep:.6f} s")
    print(f"      Stability ratio: {current_timestep/critical_timestep:.3f} (should be < 1.0)")
    
    if current_timestep > critical_timestep:
        print(f"      ❌ TIMESTEP TOO LARGE: Numerical instability likely")
    else:
        print(f"      ✅ Timestep stable")

def test_equilibrium_physics():
    """Test what SHOULD happen with correct spring physics"""
    print(f"\n" + "="*60)
    print("THEORETICAL EQUILIBRIUM ANALYSIS")
    print("="*60)
    
    # Calculate expected equilibrium
    total_mass = 160.0  # kg
    gravity = 9.81  # m/s²
    total_gravity_force = total_mass * gravity  # 1569 N
    
    # Typical spring properties
    avg_stiffness = 75000.0  # N/m
    num_springs = 28
    
    # In equilibrium: total spring force = total gravity force
    # If springs compress by 'x', each spring force = k * x
    # Total spring force = num_springs * k * x = total_gravity_force
    # Therefore: x = total_gravity_force / (num_springs * k)
    
    expected_compression = total_gravity_force / (num_springs * avg_stiffness)
    
    print(f"EXPECTED EQUILIBRIUM:")
    print(f"   Total gravity force: {total_gravity_force:.1f} N")
    print(f"   Number of springs: {num_springs}")
    print(f"   Average spring stiffness: {avg_stiffness:.1e} N/m")
    print(f"   Expected compression: {expected_compression:.6f} m ({expected_compression*1000:.2f} mm)")
    print(f"   Expected compression ratio: {expected_compression:.4%}")
    
    print(f"\nWHAT SHOULD HAPPEN:")
    print(f"   1. Robot starts at rest length")
    print(f"   2. Gravity pulls robot down")
    print(f"   3. Springs compress by {expected_compression*1000:.2f}mm")
    print(f"   4. Spring forces balance gravity")
    print(f"   5. Robot reaches stable equilibrium")
    print(f"   6. Robot maintains cubic shape with slight compression")
    
    print(f"\nWHAT'S ACTUALLY HAPPENING:")
    print(f"   ❌ Robot expands instead of compresses")
    print(f"   ❌ Robot flies upward instead of falls down")  
    print(f"   ❌ Springs create net outward force instead of inward resistance")
    
    print(f"\nCONCLUSION:")
    print(f"   There's a fundamental bug in spring force calculation or application")
    print(f"   The spring model is generating forces in the wrong direction")

if __name__ == "__main__":
    debug_spring_model()
    test_equilibrium_physics()