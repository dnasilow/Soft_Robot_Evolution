# Quick test script - save as test_voxel_sizes.py

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot

def test_voxel_size(voxel_size, description):
    """Test physics stability with different voxel sizes"""
    print(f"\n{'='*50}")
    print(f"TESTING: {description} (voxel_size = {voxel_size}m)")
    print('='*50)
    
    # Create simple 2x2x2 cube
    voxel_grid = np.zeros((10, 10, 10), dtype=np.int8)
    voxel_grid[5:7, 6:8, 5:7] = 3  # 2x2x2 passive cube, elevated
    
    robot = VoxelRobot(voxel_grid, voxel_size=voxel_size)
    
    # Analyze spring properties
    springs = robot.get_springs()
    nodes = robot.get_nodes()
    
    print(f"Robot stats:")
    print(f"  Nodes: {len(nodes['position'])}")
    print(f"  Springs: {len(springs['indices'])}")
    print(f"  Node masses: {nodes['mass'][0]:.6f} kg")
    
    # Spring analysis
    min_stiffness = np.min(springs['stiffness'])
    max_stiffness = np.max(springs['stiffness'])
    avg_stiffness = np.mean(springs['stiffness'])
    
    print(f"Spring stiffness:")
    print(f"  Min: {min_stiffness:.1e} N/m")
    print(f"  Max: {max_stiffness:.1e} N/m") 
    print(f"  Avg: {avg_stiffness:.1e} N/m")
    
    # Calculate critical timestep
    avg_mass = np.mean(nodes['mass'])
    dt_critical = 2 * np.sqrt(avg_mass / avg_stiffness)
    print(f"  Critical timestep: {dt_critical:.1e} s")
    
    # Current timestep
    current_dt = 0.0001  # Your current timestep
    stability_ratio = current_dt / dt_critical
    print(f"  Current timestep: {current_dt:.1e} s")
    print(f"  Stability ratio: {stability_ratio:.2f} (should be < 1.0)")
    
    if stability_ratio > 1.0:
        print(f"  ⚠️  UNSTABLE: Timestep {stability_ratio:.1f}x too large!")
    elif stability_ratio > 0.5:
        print(f"  ⚡ MARGINAL: Close to instability limit")
    else:
        print(f"  ✅ STABLE: Good stability margin")
    
    # Quick physics test
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=500, default_timestep=current_dt)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    initial_pos = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_pos)
    
    # Run 10 steps
    for _ in range(10):
        physics_engine.step()
    
    final_pos = physics_engine.get_positions()
    final_com = robot.get_center_of_mass(final_pos)
    
    y_change = final_com[1] - initial_com[1]
    
    print(f"Quick physics test (10 steps):")
    print(f"  Y displacement: {y_change:.4f} m")
    
    if abs(y_change) > 0.1:
        print(f"  💥 EXPLOSION: Moved {abs(y_change):.2f}m in 10 steps!")
        return False
    elif y_change < -0.001:
        print(f"  ✅ STABLE FALL: Falling normally")
        return True
    else:
        print(f"  ✅ STABLE: Minimal movement")
        return True

if __name__ == "__main__":
    # Test different voxel sizes
    test_cases = [
        (0.01, "Tiny voxels (1cm) - Expected: EXPLOSION"),
        (0.02, "Small voxels (2cm) - Your current size"),
        (0.05, "Medium voxels (5cm) - Should be stable"),
        (0.10, "Large voxels (10cm) - Very stable"),
    ]
    
    results = []
    for voxel_size, description in test_cases:
        stable = test_voxel_size(voxel_size, description)
        results.append((voxel_size, stable))
    
    print(f"\n{'='*50}")
    print("SUMMARY: Voxel Size vs Stability")
    print('='*50)
    for voxel_size, stable in results:
        status = "✅ STABLE" if stable else "💥 UNSTABLE"
        print(f"  {voxel_size:4.2f}m: {status}")
    
    print(f"\nRECOMMENDATION:")
    stable_sizes = [size for size, stable in results if stable]
    if stable_sizes:
        recommended = min(stable_sizes)  # Smallest stable size
        print(f"  Use voxel_size = {recommended}m for stable simulation")
        print(f"  This gives you the smallest stable voxels")
    else:
        print(f"  All sizes unstable - reduce Young's modulus instead!")