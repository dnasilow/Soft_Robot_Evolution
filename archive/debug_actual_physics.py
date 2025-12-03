# Debug what the physics engine is actually using - save as debug_actual_physics.py

import numpy as np
import sys
import os
import cupy as cp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot, MATERIALS

def debug_physics_engine_values():
    """Debug what values the physics engine is actually using"""
    print("="*60)
    print("DEBUGGING ACTUAL PHYSICS ENGINE VALUES")
    print("="*60)
    
    # Create simple robot
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3
    
    # Create robot with debug prints
    class DebugVoxelRobot(VoxelRobot):
        def _create_voxel_springs_fast(self, corners, material):
            """Debug version that prints actual values"""
            springs = []
            
            spring_patterns = {
                'edge': [(0,1), (0,2), (0,4), (1,3), (1,5), (2,3), (2,6), (3,7), (4,5), (4,6), (5,7), (6,7)],
                'face': [(0,3), (1,2), (0,5), (1,4), (0,6), (2,4), (1,7), (3,5), (2,7), (3,6), (4,7), (5,6)],
                'body': [(0,7), (1,6), (2,5), (3,4)]
            }
            
            print(f"\nDEBUG: Creating springs for material {material}")
            print(f"Material Young's modulus: {material.young_modulus}")
            print(f"Material density: {material.density}")
            print(f"Voxel size: {self.voxel_size}")
            
            target_stiffness_map = {
                'edge': 1000.0,
                'face': 500.0,
                'body': 100.0
            }
            
            spring_count = 0
            for spring_type, pattern in spring_patterns.items():
                for i, j in pattern:
                    if i < len(corners) and j < len(corners):
                        node1_idx = corners[i]
                        node2_idx = corners[j]
                        
                        if self._spring_exists(springs, node1_idx, node2_idx):
                            continue
                        
                        pos1 = self.nodes[node1_idx]['position']
                        pos2 = self.nodes[node2_idx]['position']
                        rest_length = np.linalg.norm(pos2 - pos1)
                        
                        stiffness = target_stiffness_map[spring_type]
                        damping = 0.1 * np.sqrt(stiffness * 0.1)
                        
                        spring_count += 1
                        if spring_count <= 3:  # Print first few springs
                            print(f"  Spring {spring_count} ({spring_type}): stiffness={stiffness:.1f} N/m, length={rest_length:.3f}m")
                        
                        springs.append({
                            'indices': [node1_idx, node2_idx],
                            'rest_length': rest_length,
                            'stiffness': stiffness,
                            'damping': damping,
                            'is_actuator': material.is_actuated,
                            'actuation_phase': material.actuation_phase if material.is_actuated else 0.0,
                            'material': material
                        })
            
            print(f"Total springs created: {len(springs)}")
            return springs
    
    robot = DebugVoxelRobot(voxel_grid, voxel_size=1.0)
    
    # Check what robot actually has
    springs_data = robot.get_springs()
    print(f"\nROBOT SPRING VALUES:")
    print(f"Number of springs: {len(springs_data['stiffness'])}")
    print(f"Stiffness values: {springs_data['stiffness'][:5]}...")  # First 5
    print(f"Average stiffness: {np.mean(springs_data['stiffness']):.2e} N/m")
    print(f"Min stiffness: {np.min(springs_data['stiffness']):.2e} N/m")
    print(f"Max stiffness: {np.max(springs_data['stiffness']):.2e} N/m")
    
    # Initialize physics engine
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    print(f"\nPHYSICS ENGINE VALUES:")
    print(f"Gravity: {physics_engine.gravity} m/s²")
    print(f"Number of nodes: {physics_engine.num_nodes}")
    print(f"Number of springs: {physics_engine.num_springs}")
    
    # Check GPU arrays
    gpu_stiffness = cp.asnumpy(physics_engine.d_stiffnesses[:physics_engine.num_springs])
    gpu_masses = cp.asnumpy(physics_engine.d_masses[:physics_engine.num_nodes])
    
    print(f"GPU stiffness values: {gpu_stiffness[:5]}...")
    print(f"GPU average stiffness: {np.mean(gpu_stiffness):.2e} N/m")
    print(f"GPU masses: {gpu_masses}")
    print(f"GPU average mass: {np.mean(gpu_masses):.3f} kg")
    
    # Manual force calculation
    total_mass = np.sum(gpu_masses)
    gravity_force = total_mass * physics_engine.gravity
    print(f"\nFORCE ANALYSIS:")
    print(f"Total robot mass: {total_mass:.1f} kg")
    print(f"Total gravity force: {gravity_force:.1f} N")
    print(f"Gravity force per node: {gravity_force / physics_engine.num_nodes:.1f} N")
    
    # Expected spring behavior
    avg_stiffness = np.mean(gpu_stiffness)
    force_per_node = gravity_force / physics_engine.num_nodes
    expected_extension = force_per_node / avg_stiffness
    print(f"Expected spring extension under gravity: {expected_extension:.4f} m ({expected_extension*100:.2f} cm)")
    
    if expected_extension > 0.1:
        print("❌ SPRINGS STILL TOO STIFF!")
    else:
        print("✅ Springs should allow falling")
    
    # Test a few physics steps manually
    print(f"\nMANUAL PHYSICS TEST:")
    initial_positions = cp.asnumpy(physics_engine.d_positions[:physics_engine.num_nodes].copy())
    initial_com = np.mean(initial_positions, axis=0)
    print(f"Initial COM: {initial_com}")
    
    # Run a few steps
    for step in range(100):
        physics_engine.step(0.001)
    
    final_positions = cp.asnumpy(physics_engine.d_positions[:physics_engine.num_nodes])
    final_com = np.mean(final_positions, axis=0)
    displacement = final_com - initial_com
    
    print(f"After 100 steps (0.1s):")
    print(f"Final COM: {final_com}")
    print(f"Displacement: {displacement}")
    print(f"Y displacement: {displacement[1]:.6f} m")
    
    if abs(displacement[1]) < 0.001:
        print("❌ BARELY MOVED: Physics problem!")
    else:
        print("✅ Movement detected")
    
    return robot, physics_engine

if __name__ == "__main__":
    debug_physics_engine_values()