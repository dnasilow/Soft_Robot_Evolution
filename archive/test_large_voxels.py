import numpy as np
import sys
import os
import pygame

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot, MATERIALS
from src.visualization.viewer import RobotViewer

def create_simple_single_voxel():
    """Create a TRULY single 1x1x1 meter voxel at position (1,1,1)"""
    print("="*50)
    print("TRUE SINGLE VOXEL: 1m x 1m x 1m at (1,1,1)")
    print("="*50)
    
    # Create a minimal 3×3×3 grid (just enough for one voxel)
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    
    # Position: Center voxel in the small grid
    x, y, z = 1, 1, 1  # Center of 3x3x3 grid
    
    # Single soft passive voxel
    voxel_grid[x, y, z] = 3  # Light blue soft passive
    
    print(f"Created SINGLE 1×1×1 meter voxel")
    print(f"Grid size: 3×3×3 (minimal)")
    print(f"Grid position: [{x}, {y}, {z}] (center)")
    print(f"Expected nodes: 8 (cube corners only)")
    print(f"Material: Soft passive (light blue)")
    
    return voxel_grid

class PhysicsFixedVoxelRobot(VoxelRobot):
    """Robot with FIXED physics for realistic falling AND correct positioning"""
    
    def __init__(self, voxel_grid, voxel_size=1.0):
        super().__init__(voxel_grid, voxel_size)
        
        # VERIFY: Check that we have exactly 8 nodes for 1 voxel
        print(f"Robot created with {len(self.nodes)} nodes (should be 8 for single voxel)")
        print(f"Robot created with {len(self.springs)} springs")
        
        # ADJUST POSITION: Move robot to desired world coordinates (1,1,1)
        # The voxel grid was 3x3x3 with voxel at (1,1,1), so robot is centered at origin
        # We want to move it so the cube center is at world position (1, 1, 1)
        offset = np.array([1.0, 1.0, 1.0])  # Move to (1,1,1) world coordinates
        
        for node in self.nodes:
            node['position'] += offset
        
        print(f"Robot repositioned to world coordinates around (1, 1, 1)")
    
    def _distribute_voxel_mass_fast(self, corners, material):
        """Distribute voxel mass - keep normal mass distribution"""
        voxel_mass = material.density * (self.voxel_size ** 3)
        mass_per_corner = max(voxel_mass / 8.0, 0.001)
        
        for corner_idx in corners:
            self.nodes[corner_idx]['mass'] += mass_per_corner
    # Add this debug code to your test_balanced_physics() function
# Insert right after "robot = PhysicsFixedVoxelRobot(voxel_grid, voxel_size=1.0)"

def debug_actual_stiffness(robot):
    """Debug what spring stiffness is actually being used"""
    
    print("\n" + "="*50)
    print("DEBUGGING ACTUAL SPRING STIFFNESS")
    print("="*50)
    
    # Check material properties
    from src.physics.robot import MATERIALS
    material_3 = MATERIALS[3]  # Light blue soft passive
    
    print(f"Material 3 (Light Blue) properties:")
    print(f"  Young's modulus: {material_3.young_modulus:.1e} Pa")
    print(f"  Density: {material_3.density} kg/m³")
    print(f"  Expected: Young's modulus should be ~1.25e5 Pa (if updated)")
    
    # Check actual spring stiffness in robot
    springs = robot.get_springs()
    actual_stiffness = springs['stiffness']
    
    print(f"\nActual robot spring stiffness:")
    print(f"  Min stiffness: {np.min(actual_stiffness):.1e} N/m")
    print(f"  Max stiffness: {np.max(actual_stiffness):.1e} N/m")
    print(f"  Avg stiffness: {np.mean(actual_stiffness):.1e} N/m")
    
    # Calculate what it should be with updated materials
    voxel_size = 1.0
    cross_section = voxel_size ** 2
    spring_length = voxel_size  # Approximate
    expected_stiffness = material_3.young_modulus * cross_section / spring_length
    
    print(f"  Expected with current material: {expected_stiffness:.1e} N/m")
    
    # Compare
    ratio = np.mean(actual_stiffness) / expected_stiffness
    print(f"  Actual vs Expected ratio: {ratio:.3f}")
    
    if ratio < 0.1:
        print(f"  ❌ MATERIALS NOT UPDATED: Still using old soft values!")
        print(f"  🔧 ACTION: Update MATERIALS dict in src/physics/robot.py")
    elif ratio > 0.8:
        print(f"  ✅ MATERIALS UPDATED: Using new stiff values")
    else:
        print(f"  ⚠️  PARTIAL UPDATE: Some springs updated, some not")
    
    # Calculate compression with actual stiffness
    nodes = robot.get_nodes()
    total_mass = np.sum(nodes['mass'])
    gravity_force_per_node = (total_mass / 8) * 9.81
    actual_compression = gravity_force_per_node / np.mean(actual_stiffness)
    
    print(f"\nCompression analysis:")
    print(f"  Gravity force per node: {gravity_force_per_node:.1f} N")
    print(f"  Actual compression: {actual_compression:.4f} m ({actual_compression*100:.1f}%)")
    
    if actual_compression > 0.1:  # More than 10cm
        print(f"  ❌ WILL FLATTEN: {actual_compression*100:.0f}% compression = pancake!")
    elif actual_compression > 0.05:  # More than 5cm  
        print(f"  ⚠️  WILL DEFORM: {actual_compression*100:.0f}% compression = noticeable squishing")
    else:
        print(f"  ✅ WILL MAINTAIN SHAPE: {actual_compression*100:.1f}% compression = realistic")

# Add this line to your test_balanced_physics() function right after creating the robot:
# debug_actual_stiffness(robot)


def test_balanced_physics():
    """Test with BALANCED materials (1% spring extension)"""
    
    print("="*60)
    print("TESTING BALANCED MATERIALS (1% spring extension)")
    print("="*60)
    
    # Create robot with single voxel
    voxel_grid = create_simple_single_voxel()
    robot = PhysicsFixedVoxelRobot(voxel_grid, voxel_size=1.0)
    debug_actual_stiffness(robot)

    # Analyze expected physics
    springs = robot.get_springs()
    nodes = robot.get_nodes()
    
    total_mass = np.sum(nodes['mass'])
    avg_stiffness = np.mean(springs['stiffness'])
    gravity_force_per_node = (total_mass / 8) * 9.81
    spring_extension = gravity_force_per_node / avg_stiffness
    
    print(f"BALANCED MATERIALS ANALYSIS:")
    print(f"  Total robot mass: {total_mass:.1f} kg")
    print(f"  Average spring stiffness: {avg_stiffness:.1e} N/m")
    print(f"  Expected spring extension: {spring_extension:.4f} m ({spring_extension*100:.1f}%)")
    
    if spring_extension < 0.02:  # Less than 2cm
        print(f"  ✅ PHYSICS SHOULD WORK: {spring_extension*100:.1f}% extension is realistic!")
    else:
        print(f"  ⚠️  STILL TOO SOFT: {spring_extension*100:.1f}% extension")
    
    # Initialize physics
    physics_engine = CUDAPhysicsEngine(
        max_nodes=2000,
        max_springs=10000,
        default_timestep=0.0001
    )
    
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    # Initialize viewer
    viewer = RobotViewer()
    
    # Get initial position
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)
    
    print(f"\nSTARTING SIMULATION:")
    print(f"  Initial COM: [{initial_com[0]:.2f}, {initial_com[1]:.2f}, {initial_com[2]:.2f}] m")
    print(f"  Expected behavior: Natural falling with ~1cm spring compression")
    
    # Simulation parameters
    timestep = 0.0001  # ✅ FIXED: Define timestep properly
    simulation_time = 2.0  # 2 seconds
    num_steps = int(simulation_time / timestep)
    
    print(f"  Duration: {simulation_time}s, Timestep: {timestep}s, Steps: {num_steps}")
    
    # Track trajectory
    trajectory = []
    max_speed = 0
    hit_ground_time = None
    settled_time = None
    
    for step in range(num_steps):
        # Get current state
        positions = physics_engine.get_positions()
        if len(positions) > 0:
            com = robot.get_center_of_mass(positions)
            trajectory.append(com.copy())
            
            # Track speed
            if len(trajectory) > 5:
                recent_pos = trajectory[-5:]
                speeds = np.linalg.norm(np.diff(recent_pos, axis=0), axis=1) / timestep
                current_speed = np.max(speeds) if len(speeds) > 0 else 0
                max_speed = max(max_speed, current_speed)
            
            # Check events
            if hit_ground_time is None and com[1] < 0.6:  # Near ground
                hit_ground_time = step * timestep
                print(f"  ⬇️  Hit ground at {hit_ground_time:.2f}s, speed: {current_speed:.2f} m/s")
            
            if (hit_ground_time is not None and settled_time is None and 
                step > hit_ground_time * 1000 + 500):  # 0.5s after ground hit
                if len(trajectory) > 100:
                    recent_motion = np.std(trajectory[-100:], axis=0)
                    if np.max(recent_motion) < 0.01:  # Very little movement
                        settled_time = step * timestep
                        print(f"  🛑 Settled at {settled_time:.2f}s")
        
        # Physics step
        physics_engine.step(timestep)
        
        # Render (every 20 steps for smooth visualization)
        if step % 20 == 0:
            positions = physics_engine.get_positions()
            springs = robot.get_springs()
            
            if not viewer.render(positions, springs):
                print("  🔴 Visualization stopped by user")
                break
            
            # Progress update
            if step % 500 == 0:  # Every 0.5s
                elapsed = step * timestep
                current_pos = robot.get_center_of_mass(positions)
                print(f"  📊 {elapsed:.1f}s: Y={current_pos[1]:.2f}m, Speed={max_speed:.2f}m/s")
    
    # Final analysis
    if len(trajectory) > 1:
        trajectory = np.array(trajectory)
        final_com = trajectory[-1]
        fall_distance = initial_com[1] - final_com[1]
        
        print(f"\n" + "="*60)
        print("BALANCED PHYSICS RESULTS:")
        print("="*60)
        print(f"Fall distance: {fall_distance:.3f} m")
        print(f"Max speed: {max_speed:.2f} m/s")
        print(f"Final height: {final_com[1]:.3f} m")
        
        # Expected values for free fall
        expected_time = np.sqrt(2 * 1.0 / 9.81)  # ~0.45s
        expected_speed = np.sqrt(2 * 9.81 * 1.0)  # ~4.4 m/s
        
        print(f"Expected free fall: {expected_time:.2f}s, {expected_speed:.1f} m/s")
        
        if hit_ground_time:
            time_ratio = hit_ground_time / expected_time
            speed_ratio = max_speed / expected_speed if expected_speed > 0 else 0
            
            print(f"Actual performance:")
            print(f"  Time ratio: {time_ratio:.2f} (1.0 = perfect free fall)")
            print(f"  Speed ratio: {speed_ratio:.2f} (1.0 = perfect free fall)")
            
            if 0.3 < time_ratio < 3.0 and speed_ratio > 0.2:
                print(f"  ✅ REALISTIC PHYSICS: Soft body behaves naturally!")
            elif 0.1 < time_ratio < 5.0:
                print(f"  ✅ ACCEPTABLE PHYSICS: Reasonable soft body behavior")
            else:
                print(f"  ⚠️  PHYSICS NEEDS TUNING: Unusual behavior")
        else:
            print(f"  ❌ DIDN'T REACH GROUND: Physics may be broken")
        
        if settled_time:
            settling_duration = settled_time - (hit_ground_time or 0)
            print(f"  🛑 Settling time: {settling_duration:.2f}s after ground contact")
        
        print(f"\n🎯 PHYSICS VERDICT:")
        if spring_extension < 0.02 and hit_ground_time and max_speed > 1.0:
            print(f"   ✅ EXCELLENT: Balanced materials work perfectly!")
            print(f"   🚀 Ready for Lipson integration (Step 2)!")
        else:
            print(f"   ⚠️  NEEDS MINOR TUNING: Close but not optimal")

if __name__ == "__main__":
    test_balanced_physics()  # Use the new balanced test