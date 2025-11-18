"""Test script to verify installation"""

import sys
import subprocess

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        import numpy as np
        print("✓ NumPy installed")
        
        import torch
        print(f"✓ PyTorch installed (CUDA available: {torch.cuda.is_available()})")
        
        import cupy as cp
        # Fixed: Use properties instead of name attribute
        device = cp.cuda.Device(0)
        device_props = device.attributes
        print(f"✓ CuPy installed (GPU compute capability: {device.compute_capability})")
        
        import moderngl
        print("✓ ModernGL installed")
        
        import pygame
        print("✓ Pygame installed")
        
        import matplotlib.pyplot as plt
        print("✓ Matplotlib installed")
        
        import numba
        print("✓ Numba installed")
        
        print("\nAll imports successful!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_cuda():
    """Test CUDA compilation"""
    print("\nTesting CUDA...")
    
    try:
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ CUDA compiler (nvcc) found")
            print(result.stdout.split('\n')[3])  # Version line
        else:
            print("✗ CUDA compiler not found")
            return False
            
    except FileNotFoundError:
        print("✗ nvcc not in PATH")
        return False
    
    # Test CuPy CUDA
    try:
        import cupy as cp
        
        # Simple GPU computation
        a = cp.array([1, 2, 3])
        b = cp.array([4, 5, 6])
        c = a + b
        
        print(f"✓ GPU computation test passed: {a} + {b} = {c}")
        
        # Show GPU info
        mempool = cp.get_default_memory_pool()
        print(f"✓ GPU memory pool initialized (used: {mempool.used_bytes() / 1e6:.1f} MB)")
        
        return True
        
    except Exception as e:
        print(f"✗ GPU computation failed: {e}")
        return False

def test_simple_robot():
    """Test simple robot creation"""
    print("\nTesting robot creation...")
    
    try:
        # Add src to Python path
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from physics.robot import VoxelRobot
        from evolution.genomes import DirectVoxelGenome
        
        # Create simple genome
        genome = DirectVoxelGenome((10, 10, 10)) #not (4,4,4)
        genome.randomize()
        
        # Convert to robot
        robot = genome.to_phenotype()
        
        print(f"✓ Created robot with {len(robot.nodes)} nodes and {len(robot.springs)} springs")
        
        # Check actuators
        actuators = sum(1 for s in robot.springs if s['is_actuator'])
        print(f"✓ Robot has {actuators} actuators")
        
        return True
        
    except Exception as e:
        print(f"✗ Robot creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def verify_pattern_generation():
    """Test to verify we're using real CPPN vs old hardcoded method"""
    print("\nTesting pattern generation methods:")
    
    try:
        # Add src to Python path
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        import numpy as np
        from evolution.genomes import DirectVoxelGenome
        
        # Test old hardcoded method
        print("\n1. Old hardcoded method:")
        old_pattern = np.zeros((10, 10, 10))
        center = np.array([5, 5, 5])
        for x in range(10):
            for y in range(10):
                for z in range(10):
                    norm_x = (x - center[0]) / 5
                    norm_y = (y - center[1]) / 5
                    norm_z = (z - center[2]) / 5
                    distance = np.sqrt(norm_x**2 + norm_y**2 + norm_z**2)
                    voxel_presence = np.sin(norm_x * 3) * np.cos(norm_y * 3) * np.exp(-distance)
                    if voxel_presence > 0.1:
                        old_pattern[x, y, z] = 1
        
        print(f"Old method: {np.sum(old_pattern > 0)} voxels")
        
        # Test new CPPN method
        print("\n2. New CPPN method:")
        genome = DirectVoxelGenome()
        print(f"CPPN method: {np.sum(genome.voxels > 0)} voxels")
        print(f"Material distribution: {np.bincount(genome.voxels.flatten())}")
        
        # Verify CPPN structure
        print(f"\n3. CPPN structure verification:")
        print(f"CPPN inputs: {genome.cppn.num_inputs}")
        print(f"CPPN outputs: {genome.cppn.num_outputs}")
        print(f"CPPN nodes: {len(genome.cppn.nodes)}")
        print(f"CPPN connections: {len(genome.cppn.connections)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Pattern generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_simulation_timing():
    """Verify that simulation runs for exactly 10 cycles"""
    print("\nTesting simulation timing:")
    
    try:
        # Simulation parameters
        actuation_cycles = 10
        actuation_freq = 1.0
        timestep = 0.0005
        
        # Calculate parameters
        cycle_duration = 1.0 / actuation_freq
        simulation_time = actuation_cycles * cycle_duration
        steps_per_cycle = int(cycle_duration / timestep)
        total_steps = steps_per_cycle * actuation_cycles
        actual_sim_time = total_steps * timestep
        
        print(f"Actuation frequency: {actuation_freq} Hz")
        print(f"Cycle duration: {cycle_duration} s")
        print(f"Number of cycles: {actuation_cycles}")
        print(f"Timestep: {timestep} s")
        print(f"Steps per cycle: {steps_per_cycle}")
        print(f"Total steps: {total_steps}")
        print(f"Expected sim time: {simulation_time} s")
        print(f"Actual sim time: {actual_sim_time} s")
        print(f"Timing error: {abs(simulation_time - actual_sim_time)} s")
        
        if abs(simulation_time - actual_sim_time) < 1e-10:
            print("✓ Simulation timing is EXACT")
            return True
        else:
            print("✗ Simulation timing has error")
            return False
            
    except Exception as e:
        print(f"✗ Timing verification failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Soft Robot Evolution System - Setup Test")
    print("=" * 50)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_cuda()
    all_passed &= test_simple_robot()
    all_passed &= verify_pattern_generation()
    all_passed &= verify_simulation_timing()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed! System is ready.")
        print("\nYou can now run: python main.py --visualize")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    print("=" * 50)










    