import numpy as np
import sys
import os

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.visualization.viewer import RobotViewer

def create_simple_test_cube():
    """Create a simple 2x2x2 cube for physics testing - NO ACTUATORS"""
    # Create a 10x10x10 grid (same as your system)
    voxel_grid = np.zeros((10, 10, 10), dtype=np.int8)
    
    # Create a 2x2x2 cube in the center, elevated
    center_x, center_y, center_z = 5, 7, 5  # Elevated in Y (will fall)
    
    # FIXED: Use material 3 (light blue soft passive) - NO actuators!
    for dx in range(2):
        for dy in range(2):
            for dz in range(2):
                x, y, z = center_x + dx, center_y + dy, center_z + dz
                voxel_grid[x, y, z] = 3  # Light blue passive material (not actuated!)
    
    print(f"Created test cube with {np.sum(voxel_grid > 0)} voxels")
    print(f"Cube materials: {np.bincount(voxel_grid.flatten())}")
    
    return voxel_grid

def create_mixed_test_cube():
    """Create a cube with mixed passive materials"""
    voxel_grid = np.zeros((10, 10, 10), dtype=np.int8)
    
    # Create 3x3x2 cube with mixed passive materials
    center_x, center_y, center_z = 4, 6, 4  # Elevated
    
    for dx in range(3):
        for dy in range(2):
            for dz in range(3):
                x, y, z = center_x + dx, center_y + dy, center_z + dz
                # Alternate between soft (3) and stiff (4) passive materials
                if (dx + dz) % 2 == 0:
                    voxel_grid[x, y, z] = 3  # Light blue soft passive
                else:
                    voxel_grid[x, y, z] = 4  # Dark blue stiff passive
    
    print(f"Created mixed cube with {np.sum(voxel_grid > 0)} voxels")
    print(f"Materials: {np.bincount(voxel_grid.flatten())}")
    
    return voxel_grid

def test_physics_simulation():
    """Test basic physics with a falling cube - FIXED VERSION"""
    print("="*50)
    print("PHYSICS TEST: Falling Cube (PASSIVE MATERIALS)")
    print("="*50)
    
    # Create test cube with PASSIVE materials only
    voxel_grid = create_simple_test_cube()
    robot = VoxelRobot(voxel_grid, voxel_size=0.02)  # Slightly larger voxels
    
    print(f"Robot created:")
    print(f"  Nodes: {len(robot.nodes)}")
    print(f"  Springs: {len(robot.springs)}")
    
    # Count actuators (should be ZERO for this test)
    actuator_count = len([s for s in robot.springs if s['is_actuator']])
    print(f"  Actuators: {actuator_count} (should be 0 for passive cube)")
    
    if actuator_count > 0:
        print("  WARNING: Cube has actuators - will not fall properly!")
    
    # Initialize physics engine
    physics_engine = CUDAPhysicsEngine(
        max_nodes=1000,
        max_springs=5000,
        actuation_frequency=1.0,
        default_timestep=0.0005  # Smaller timestep for stability
    )
    
    # Add robot to physics
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    # Initialize viewer
    viewer = RobotViewer()
    
    # Get initial position
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)
    print(f"Initial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")
    
    # Simulation parameters
    timestep = 0.0005  # Smaller timestep
    simulation_time = 8.0  # 8 seconds
    num_steps = int(simulation_time / timestep)
    
    print(f"\nRunning physics test for {simulation_time} seconds...")
    print("Controls: Left-drag to rotate, Scroll to zoom, Close window to stop")
    print("Expected: Passive cube should fall down and settle on ground")
    print("NOTE: If cube flies upward, there's a physics bug!")
    
    # Track trajectory
    trajectory = []
    
    for step in range(num_steps):
        # Get current state
        positions = physics_engine.get_positions()
        if len(positions) > 0:
            com = robot.get_center_of_mass(positions)
            trajectory.append(com.copy())
        
        # Physics step (no control, just gravity on passive materials)
        physics_engine.step(timestep)
        
        # Render every 5 steps (about 200 FPS -> 40 FPS display)
        if step % 5 == 0:
            positions = physics_engine.get_positions()
            springs = robot.get_springs()
            
            if not viewer.render(positions, springs):
                print("Visualization stopped by user")
                break
            
            # Print progress every 2 seconds
            if step % 4000 == 0:
                elapsed_time = step * timestep
                current_pos = robot.get_center_of_mass(positions)
                print(f"  Time: {elapsed_time:.1f}s, COM: [{current_pos[0]:.3f}, {current_pos[1]:.3f}, {current_pos[2]:.3f}]")
    
    # Final analysis
    if len(trajectory) > 1:
        trajectory = np.array(trajectory)
        final_com = trajectory[-1]
        
        print(f"\n" + "="*50)
        print("PHYSICS TEST RESULTS:")
        print("="*50)
        print(f"Initial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")
        print(f"Final COM:   [{final_com[0]:.3f}, {final_com[1]:.3f}, {final_com[2]:.3f}]")
        print(f"Y displacement: {final_com[1] - initial_com[1]:.3f} m")
        
        # Check if physics worked correctly
        y_change = final_com[1] - initial_com[1]
        if y_change < -0.05:  # Fell at least 5cm
            print("✓ PHYSICS WORKING: Cube fell due to gravity!")
        elif y_change > 0.05:  # Went up
            print("✗ PHYSICS BUG: Cube went UP instead of falling!")
            print("  This suggests actuators are active or gravity is inverted")
        else:
            print("? PHYSICS UNCLEAR: Cube barely moved")
        
        if abs(final_com[1]) < 0.05:  # Near ground level
            print("✓ GROUND COLLISION: Cube reached ground level")
        elif final_com[1] > 1.0:  # High in air
            print("✗ GROUND COLLISION: Cube is still high in air")
        else:
            print(f"? GROUND COLLISION: Cube at height: {final_com[1]:.3f}m")
        
        # Check if it settled
        if len(trajectory) > 2000:  # Last 1 second
            recent_motion = np.std(trajectory[-2000:], axis=0)
            if np.max(recent_motion) < 0.01:
                print("✓ STABILITY: Cube settled and stopped moving")
            else:
                print(f"? STABILITY: Cube still moving (std: {recent_motion})")
                
        # Trajectory analysis
        max_height = np.max(trajectory[:, 1])
        min_height = np.min(trajectory[:, 1])
        print(f"Max height reached: {max_height:.3f}m")
        print(f"Min height reached: {min_height:.3f}m")
    
    print("\nPhysics test complete!")

def test_mixed_materials():
    """Test with mixed passive materials"""
    print("\n" + "="*50)
    print("MIXED MATERIALS TEST: Soft + Stiff Passive")
    print("="*50)
    
    voxel_grid = create_mixed_test_cube()
    robot = VoxelRobot(voxel_grid, voxel_size=0.02)
    
    actuator_count = len([s for s in robot.springs if s['is_actuator']])
    print(f"Robot: {len(robot.nodes)} nodes, {len(robot.springs)} springs, {actuator_count} actuators")
    
    if actuator_count > 0:
        print("ERROR: Mixed passive materials shouldn't have actuators!")
        return
    
    # Quick physics test
    physics_engine = CUDAPhysicsEngine(max_nodes=1000, max_springs=5000)
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    viewer = RobotViewer()
    
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)
    print(f"Initial COM: [{initial_com[0]:.3f}, {initial_com[1]:.3f}, {initial_com[2]:.3f}]")
    
    timestep = 0.0005
    for step in range(8000):  # 4 seconds
        positions = physics_engine.get_positions()
        physics_engine.step(timestep)
        
        if step % 10 == 0:
            positions = physics_engine.get_positions()
            springs = robot.get_springs()
            if not viewer.render(positions, springs):
                break
    
    final_positions = physics_engine.get_positions()
    final_com = robot.get_center_of_mass(final_positions)
    print(f"Final COM: [{final_com[0]:.3f}, {final_com[1]:.3f}, {final_com[2]:.3f}]")
    print(f"Y change: {final_com[1] - initial_com[1]:.3f}m")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Physics Simulation - FIXED')
    parser.add_argument('--test', choices=['fall', 'mixed', 'both'], default='fall',
                       help='Which test to run')
    
    args = parser.parse_args()
    
    if args.test in ['fall', 'both']:
        test_physics_simulation()
        
    if args.test in ['mixed', 'both']:
        if args.test == 'both':
            input("Press Enter to start mixed materials test...")
        test_mixed_materials()