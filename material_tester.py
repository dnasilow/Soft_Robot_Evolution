# material_tester.py - Quick test to find good material parameters

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.robot import VoxelMaterial

def test_material_parameters(density, young_modulus, voxel_size=1.0):
    """Test if material parameters give realistic physics"""
    
    # Simulate single voxel (8 nodes, ~28 springs)
    num_nodes = 8
    voxel_volume = voxel_size ** 3
    voxel_mass = density * voxel_volume
    total_mass = voxel_mass  # Single voxel
    mass_per_node = total_mass / num_nodes
    
    # Estimate spring properties (simplified)
    cross_section = voxel_size ** 2
    spring_length = voxel_size  # Average spring length
    spring_stiffness = young_modulus * cross_section / spring_length
    
    # Physics check
    gravity_force_per_node = mass_per_node * 9.81
    spring_extension = gravity_force_per_node / spring_stiffness
    extension_percentage = (spring_extension / voxel_size) * 100
    
    # Results
    print(f"\nMaterial Test:")
    print(f"  Density: {density} kg/m³")
    print(f"  Young's Modulus: {young_modulus:.1e} Pa")
    print(f"  Voxel size: {voxel_size} m")
    print(f"  Total mass: {total_mass:.1f} kg")
    print(f"  Spring stiffness: {spring_stiffness:.1e} N/m")
    print(f"  Gravity force per node: {gravity_force_per_node:.1f} N")
    print(f"  Spring extension: {spring_extension:.4f} m ({extension_percentage:.1f}%)")
    
    # Verdict
    if extension_percentage < 1:
        verdict = "✅ EXCELLENT"
    elif extension_percentage < 5:
        verdict = "✅ GOOD"
    elif extension_percentage < 20:
        verdict = "⚠️  MARGINAL" 
    else:
        verdict = "❌ TOO SOFT"
    
    print(f"  Verdict: {verdict}")
    return extension_percentage < 20  # Return True if acceptable

def find_good_parameters():
    """Test different parameter combinations"""
    print("="*60)
    print("MATERIAL PARAMETER SEARCH")
    print("="*60)
    
    # Test current parameters
    print("\n1. CURRENT PARAMETERS:")
    test_material_parameters(density=800, young_modulus=5e3)
    
    # Test lightweight version
    print("\n2. LIGHTWEIGHT VERSION:")
    test_material_parameters(density=80, young_modulus=5e3)
    
    # Test stiff version  
    print("\n3. STIFF VERSION:")
    test_material_parameters(density=800, young_modulus=5e4)
    
    # Test balanced version
    print("\n4. BALANCED VERSION:")
    test_material_parameters(density=200, young_modulus=2.5e4)
    
    # Test extremely light (foam-like)
    print("\n5. FOAM-LIKE (very light):")
    test_material_parameters(density=50, young_modulus=1e4)
    
    # Test realistic soft rubber
    print("\n6. SOFT RUBBER:")
    test_material_parameters(density=1000, young_modulus=1e6)
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("- For immediate fix: Use LIGHTWEIGHT VERSION (10x lighter)")
    print("- For realism: Use BALANCED VERSION (compromise)")
    print("- For Lipson accuracy: Use SOFT RUBBER (but may be too stiff)")
    print("="*60)

def calculate_target_parameters(target_extension_percent=1.0, voxel_size=1.0):
    """Calculate what parameters we need for target extension"""
    print(f"\n" + "="*60)
    print(f"PARAMETER CALCULATOR")
    print(f"Target: {target_extension_percent}% spring extension under gravity")
    print("="*60)
    
    # Assume reasonable density (water-like)
    density = 1000  # kg/m³
    
    voxel_volume = voxel_size ** 3
    voxel_mass = density * voxel_volume
    mass_per_node = voxel_mass / 8
    gravity_force_per_node = mass_per_node * 9.81
    
    # Target extension
    target_extension = (target_extension_percent / 100) * voxel_size
    required_stiffness = gravity_force_per_node / target_extension
    
    # Back-calculate Young's modulus
    cross_section = voxel_size ** 2
    spring_length = voxel_size
    required_young_modulus = required_stiffness * spring_length / cross_section
    
    print(f"\nFor {target_extension_percent}% extension:")
    print(f"  Required spring stiffness: {required_stiffness:.1e} N/m")
    print(f"  Required Young's modulus: {required_young_modulus:.1e} Pa")
    print(f"  Suggested density: {density} kg/m³")
    
    # Test this combination
    test_material_parameters(density, required_young_modulus, voxel_size)

if __name__ == "__main__":
    find_good_parameters()
    calculate_target_parameters(target_extension_percent=1.0)
    calculate_target_parameters(target_extension_percent=5.0)
