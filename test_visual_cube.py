#!/usr/bin/env python
"""Visual test - Watch a cube fall and bounce!"""

import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.physics.cuda_physics import CUDAPhysicsEngine
from src.physics.robot import VoxelRobot
from src.visualization.viewer import RobotViewer

def test_visual_falling_cube():
    """Visual test - watch the cube fall!"""
    print("="*60)
    print("VISUAL FALLING CUBE TEST")
    print("="*60)
    print("\nCreating a single 1×1×1 meter voxel cube...")
    print("Starting at Y = 2.5 meters (2.5m above ground)")
    print("\nControls:")
    print("  - Left-drag mouse: Rotate view")
    print("  - Scroll wheel: Zoom in/out")
    print("  - R key: Reset camera view")
    print("  - ESC or close window: Exit")
    print("\nThe cube should:")
    print("  1. Fall due to gravity (9.81 m/s²)")
    print("  2. Compress springs as it falls")
    print("  3. Bounce on ground (Y = 0)")
    print("  4. Eventually settle to equilibrium")
    print("\n" + "="*60)

    # Create a single voxel robot (1×1×1 meter cube)
    voxel_grid = np.zeros((3, 3, 3), dtype=np.int8)
    voxel_grid[1, 1, 1] = 3  # Material 3 = soft passive (light blue)

    robot = VoxelRobot(voxel_grid, voxel_size=1.0)

    print(f"\nRobot created:")
    print(f"  Nodes: {len(robot.nodes)}")
    print(f"  Springs: {len(robot.springs)}")
    print(f"  Mass: {np.sum([n['mass'] for n in robot.nodes]):.1f} kg")

    # Initialize physics
    physics_engine = CUDAPhysicsEngine(max_nodes=100, max_springs=100)
    physics_engine.reset()
    physics_engine.add_robot(robot)

    # Get initial position
    initial_positions = physics_engine.get_positions()
    initial_com = robot.get_center_of_mass(initial_positions)
    print(f"\nInitial center of mass: [{initial_com[0]:.2f}, {initial_com[1]:.2f}, {initial_com[2]:.2f}]")

    # Create viewer
    viewer = RobotViewer(width=1280, height=720)

    # Simulation parameters
    timestep = 0.001  # 1ms per step (good balance of accuracy and speed)
    sim_time = 0.0
    max_sim_time = 10.0  # Run for 10 seconds
    physics_steps_per_frame = 10  # Run 10 physics steps per visual frame for smoother physics

    # Stats tracking
    last_print_time = 0.0
    print_interval = 0.5  # Print stats every 0.5 seconds

    # Track for oscillation detection
    y_history = []
    velocity_history = []

    print(f"\nStarting simulation (timestep={timestep}s)...")
    print("Close window or press ESC to stop\n")

    running = True
    frame_count = 0
    while running and sim_time < max_sim_time:
        # Run multiple physics steps per frame for stability
        for _ in range(physics_steps_per_frame):
            physics_engine.step(timestep)
            sim_time += timestep

        # Get current state
        positions = physics_engine.get_positions()
        springs = robot.get_springs()
        com = robot.get_center_of_mass(positions)

        # Track history
        y_history.append(com[1])
        import cupy as cp
        vel = cp.asnumpy(physics_engine.d_velocities[:physics_engine.num_nodes])
        avg_vel = np.mean(np.abs(vel))
        velocity_history.append(avg_vel)

        # Print stats periodically
        if sim_time - last_print_time >= print_interval:
            fall_distance = initial_com[1] - com[1]

            # Check for settling
            if len(y_history) > 100:
                recent_y_change = max(y_history[-100:]) - min(y_history[-100:])
                is_settling = recent_y_change < 0.01  # Less than 1cm variation
            else:
                is_settling = False

            status = "✓ SETTLED" if is_settling else "oscillating"
            print(f"t={sim_time:.2f}s: Y={com[1]:.3f}m, fall={fall_distance:.3f}m, vel={avg_vel:.3f}m/s [{status}]")
            last_print_time = sim_time

        # Render (every frame)
        if not viewer.render(positions, springs):
            print("\nViewer closed by user")
            running = False
            break

        # Limit frame rate
        viewer.clock.tick(60)  # 60 FPS
        frame_count += 1

    # Final stats
    final_positions = physics_engine.get_positions()
    final_com = robot.get_center_of_mass(final_positions)
    total_fall = initial_com[1] - final_com[1]

    print(f"\n{'='*60}")
    print("SIMULATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total simulation time: {sim_time:.2f} seconds")
    print(f"Initial Y position: {initial_com[1]:.3f} m")
    print(f"Final Y position: {final_com[1]:.3f} m")
    print(f"Total fall distance: {total_fall:.3f} m")
    print(f"\nExpected free fall (10s): {0.5 * 9.81 * 10**2:.1f} m")
    print(f"Actual fall: {total_fall:.3f} m")

    if total_fall < 0.2:
        print("\n✅ SUCCESS: Springs are working! Cube barely fell.")
    elif total_fall < 1.0:
        print("\n✅ GOOD: Cube fell some but springs resisted significantly.")
    elif total_fall > 4.0:
        print("\n❌ PROBLEM: Cube fell too much - springs may not be working.")
    else:
        print("\n⚠️ MODERATE: Some spring resistance but could be better.")

if __name__ == "__main__":
    test_visual_falling_cube()
