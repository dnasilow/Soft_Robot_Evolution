# direct_spring_test.py - Run this to see what's actually happening

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.robot import VoxelRobot, MATERIALS

def direct_spring_test():
    """Direct test to see what spring stiffness is actually being used"""
    
    print("="*60)
    print("DIRECT SPRING STIFFNESS DIAGNOSTIC")
    print("="*60)
    
    # Check materials first
    print("1. CHECKING MATERIALS:")
    material_3 = MATERIALS[3]  # Light blue soft passive
    print(f"   Material 3 Young's modulus: {material_3.young_modulus:.1e} Pa")
    print(f"   Material 3 Density: {material_3.density} kg/m³")
    
    if material_3.young_modulus >= 1e5:
        print(f"   ✅ MATERIALS UPDATED: {material_3.young_modulus:.1e} Pa is stiff")
    else:
        print(f"   ❌ MATERIALS NOT UPDATED: {material_3.young_modulus:.1e} Pa is still soft")
        return
    
    # Create simple robot
    print("\n2. CREATING ROBOT:")
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3  # Single light blue voxel
    
    robot = VoxelRobot(voxel_grid, voxel_size=1.0)
    
    print(f"   Created robot with {len(robot.nodes)} nodes, {len(robot.springs)} springs")
    
    # Check spring properties
    print("\n3. CHECKING SPRING STIFFNESS:")
    springs = robot.get_springs()
    nodes = robot.get_nodes()
    
    stiffness_values = springs['stiffness']
    print(f"   Min stiffness: {np.min(stiffness_values):.1e} N/m")
    print(f"   Max stiffness: {np.max(stiffness_values):.1e} N/m")
    print(f"   Average stiffness: {np.mean(stiffness_values):.1e} N/m")
    
    # Calculate expected stiffness manually
    voxel_size = 1.0
    cross_section = voxel_size ** 2
    typical_spring_length = voxel_size  # Edge length
    expected_edge_stiffness = material_3.young_modulus * cross_section / typical_spring_length
    
    print(f"   Expected edge stiffness: {expected_edge_stiffness:.1e} N/m")
    
    # Compare actual vs expected
    avg_stiffness = np.mean(stiffness_values)
    ratio = avg_stiffness / expected_edge_stiffness
    print(f"   Actual/Expected ratio: {ratio:.3f}")
    
    if ratio < 0.01:
        print(f"   ❌ SPRINGS WAY TOO SOFT: Something is wrong with spring calculation")
    elif ratio < 0.1:
        print(f"   ⚠️  SPRINGS TOO SOFT: Partial problem")
    elif ratio > 0.1:
        print(f"   ✅ SPRINGS REASONABLE: Close to expected values")
    
    # Calculate compression
    print("\n4. COMPRESSION ANALYSIS:")
    total_mass = np.sum(nodes['mass'])
    gravity_force_per_node = (total_mass / 8) * 9.81
    spring_extension = gravity_force_per_node / avg_stiffness
    
    print(f"   Total mass: {total_mass:.1f} kg")
    print(f"   Gravity force per node: {gravity_force_per_node:.1f} N")
    print(f"   Spring extension: {spring_extension:.4f} m ({spring_extension*100:.1f}%)")
    
    if spring_extension > 0.2:  # More than 20cm
        print(f"   ❌ WILL BECOME PANCAKE: {spring_extension*100:.0f}% compression!")
        print(f"   🔧 PROBLEM: Springs still too soft despite material update")
    elif spring_extension > 0.05:  # More than 5cm
        print(f"   ⚠️  WILL DEFORM: {spring_extension*100:.0f}% compression")
    else:
        print(f"   ✅ WILL MAINTAIN SHAPE: {spring_extension*100:.1f}% compression")
    
    # Show spring calculation details
    print("\n5. SPRING CALCULATION DETAILS:")
    print(f"   Material Young's modulus: {material_3.young_modulus:.1e} Pa")
    print(f"   Cross-sectional area: {cross_section:.3f} m²")
    print(f"   Spring length: {typical_spring_length:.3f} m")
    print(f"   Raw stiffness: E*A/L = {expected_edge_stiffness:.1e} N/m")
    
    # Look at individual spring types
    print("\n6. SPRING TYPE BREAKDOWN:")
    for i in range(min(5, len(robot.springs))):
        spring = robot.springs[i]
        print(f"   Spring {i}: stiffness={spring['stiffness']:.1e} N/m, length={spring['rest_length']:.3f}m")

if __name__ == "__main__":
    direct_spring_test()