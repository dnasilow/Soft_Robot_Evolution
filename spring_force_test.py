# spring_force_test.py - Check if springs are fighting gravity during compression

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
import cupy as cp

def debug_spring_forces_during_step():
    """Check if springs resist compression during physics step"""
    
    print("="*60)
    print("SPRING FORCE DURING COMPRESSION DIAGNOSTIC")
    print("="*60)
    
    # Create robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Move to test position
    offset = np.array([1.0, 1.0, 1.0])
    for node in robot.nodes:
        node['position'] += offset
    
    # Initialize physics
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    print("1. INITIAL SETUP:")
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)
    
    # Calculate initial spring lengths
    initial_spring_lengths = []
    spring_indices = cp.asnumpy(physics_engine.d_spring_node1[:physics_engine.num_springs])
    spring_indices2 = cp.asnumpy(physics_engine.d_spring_node2[:physics_engine.num_springs])
    rest_lengths = cp.asnumpy(physics_engine.d_rest_lengths[:physics_engine.num_springs])
    
    for i in range(physics_engine.num_springs):
        node1_idx = spring_indices[i]
        node2_idx = spring_indices2[i]
        pos1 = initial_positions[node1_idx]
        pos2 = initial_positions[node2_idx]
        current_length = np.linalg.norm(pos2 - pos1)
        initial_spring_lengths.append(current_length)
    
    initial_spring_lengths = np.array(initial_spring_lengths)
    
    print(f"   Initial COM: [{initial_com[0]:.2f}, {initial_com[1]:.2f}, {initial_com[2]:.2f}]")
    print(f"   Number of springs: {physics_engine.num_springs}")
    print(f"   Avg rest length: {np.mean(rest_lengths):.3f} m")
    print(f"   Avg current length: {np.mean(initial_spring_lengths):.3f} m")
    print(f"   Initial compression: {np.mean((rest_lengths - initial_spring_lengths) / rest_lengths * 100):.1f}%")
    
    # Simulate with detailed spring monitoring
    print("\n2. COMPRESSION SIMULATION (10 steps):")
    
    for step in range(10):
        print(f"\n   Step {step}:")
        
        # Get current positions
        current_positions = physics_engine.get_positions()
        current_com = robot.get_center_of_mass(current_positions)
        
        # Calculate current spring lengths and forces
        current_spring_lengths = []
        for i in range(physics_engine.num_springs):
            node1_idx = spring_indices[i]
            node2_idx = spring_indices2[i]
            pos1 = current_positions[node1_idx]
            pos2 = current_positions[node2_idx]
            current_length = np.linalg.norm(pos2 - pos1)
            current_spring_lengths.append(current_length)
        
        current_spring_lengths = np.array(current_spring_lengths)
        
        # Calculate spring forces manually
        spring_extensions = current_spring_lengths - rest_lengths
        spring_stiffnesses = cp.asnumpy(physics_engine.d_stiffnesses[:physics_engine.num_springs])
        spring_forces = spring_stiffnesses * spring_extensions
        
        total_spring_force = np.sum(np.abs(spring_forces))
        compression_pct = np.mean((rest_lengths - current_spring_lengths) / rest_lengths * 100)
        
        print(f"      COM: [{current_com[0]:.2f}, {current_com[1]:.2f}, {current_com[2]:.2f}]")
        print(f"      Avg spring length: {np.mean(current_spring_lengths):.4f} m")
        print(f"      Compression: {compression_pct:.1f}%")
        print(f"      Total spring force: {total_spring_force:.1f} N")
        
        # Check if springs are resisting compression
        gravity_force = 160.0 * 9.81  # Total gravity
        spring_resistance_ratio = total_spring_force / gravity_force
        
        print(f"      Spring resistance ratio: {spring_resistance_ratio:.3f} (1.0 = balances gravity)")
        
        if compression_pct > 1.0 and spring_resistance_ratio < 0.1:
            print(f"      ❌ SPRINGS NOT RESISTING: {compression_pct:.1f}% compression but only {spring_resistance_ratio:.3f}x resistance")
        elif compression_pct > 10.0:
            print(f"      ❌ EXCESSIVE COMPRESSION: {compression_pct:.1f}% despite springs")
        else:
            print(f"      ✅ Reasonable behavior")
        
        # Take physics step
        physics_engine.step(0.001)
    
    # Final analysis
    final_positions = physics_engine.get_positions()
    final_com = robot.get_center_of_mass(final_positions)
    total_compression = initial_com[1] - final_com[1]
    
    print(f"\n3. FINAL ANALYSIS (after 10 steps = 0.01s):")
    print(f"   Initial Y: {initial_com[1]:.3f} m")
    print(f"   Final Y: {final_com[1]:.3f} m")
    print(f"   Total fall: {total_compression:.4f} m")
    print(f"   Fall rate: {total_compression/0.01:.2f} m/s")
    
    # Calculate final spring compression
    final_spring_lengths = []
    for i in range(physics_engine.num_springs):
        node1_idx = spring_indices[i]
        node2_idx = spring_indices2[i]
        pos1 = final_positions[node1_idx]
        pos2 = final_positions[node2_idx]
        current_length = np.linalg.norm(pos2 - pos1)
        final_spring_lengths.append(current_length)
    
    final_spring_lengths = np.array(final_spring_lengths)
    final_compression_pct = np.mean((rest_lengths - final_spring_lengths) / rest_lengths * 100)
    
    print(f"   Final spring compression: {final_compression_pct:.1f}%")
    
    if final_compression_pct > 5.0:
        print(f"   ❌ SIGNIFICANT COMPRESSION: Springs not working effectively")
        print(f"   🔧 Possible issues:")
        print(f"      - Spring force calculation bug")
        print(f"      - Integration timestep too large") 
        print(f"      - Force application bug")
    else:
        print(f"   ✅ Compression within reasonable limits")

def test_static_spring_forces():
    """Test if springs can balance gravity in static equilibrium"""
    
    print(f"\n" + "="*60)
    print("STATIC SPRING EQUILIBRIUM TEST")
    print("="*60)
    
    # Test: If we manually compress springs, do they generate enough force?
    
    # Material properties
    from src.physics.robot import MATERIALS
    material = MATERIALS[3]
    
    # Spring calculation
    voxel_size = 1.0
    cross_section = voxel_size ** 2
    spring_length = voxel_size
    edge_stiffness = material.young_modulus * cross_section / spring_length
    
    print(f"1. THEORETICAL SPRING FORCE:")
    print(f"   Young's modulus: {material.young_modulus:.1e} Pa")
    print(f"   Edge spring stiffness: {edge_stiffness:.1e} N/m")
    
    # Single voxel has 28 springs total
    # - 12 edge springs (length = 1.0m) 
    # - 12 face springs (length = √2 ≈ 1.414m)
    # - 4 body springs (length = √3 ≈ 1.732m)
    
    edge_springs = 12
    face_springs = 12  
    body_springs = 4
    
    face_length = np.sqrt(2)
    body_length = np.sqrt(3)
    
    face_stiffness = edge_stiffness * spring_length / face_length  # Adjust for length
    body_stiffness = edge_stiffness * spring_length / body_length
    
    print(f"   Face spring stiffness: {face_stiffness:.1e} N/m")
    print(f"   Body spring stiffness: {body_stiffness:.1e} N/m")
    
    # Test compression resistance
    compression_distances = [0.01, 0.05, 0.1, 0.2]  # 1cm, 5cm, 10cm, 20cm
    
    print(f"\n2. COMPRESSION RESISTANCE:")
    gravity_force = 160.0 * 9.81  # 1569.7 N
    
    for compression in compression_distances:
        # Assume compression affects all springs proportionally
        edge_force = edge_springs * edge_stiffness * compression
        face_force = face_springs * face_stiffness * compression  
        body_force = body_springs * body_stiffness * compression
        
        total_spring_force = edge_force + face_force + body_force
        balance_ratio = total_spring_force / gravity_force
        
        print(f"   {compression*100:4.0f}% compression: {total_spring_force:8.1f} N (ratio: {balance_ratio:.2f})")
        
        if balance_ratio >= 1.0:
            print(f"        ✅ Springs can balance gravity at {compression*100:.0f}% compression")
            break
    else:
        print(f"        ❌ Springs cannot balance gravity even at 20% compression!")

if __name__ == "__main__":
    debug_spring_forces_during_step()
    test_static_spring_forces()