"""Visualize a saved robot from evolution - WITH 3D GRAPHICS"""
import numpy as np
import pickle
import sys
from src.physics.robot import VoxelRobot
from src.physics.cuda_physics import OptimizedCUDAPhysicsEngine
from src.visualization.viewer import RobotViewer
import cupy as cp

def load_and_visualize(robot_file='best_robot.pkl', simulation_time=5.0, use_graphics=True):
    """Load and simulate a saved robot with optional 3D visualization"""

    print("="*70)
    print("ROBOT VISUALIZATION" + (" - 3D GRAPHICS MODE" if use_graphics else ""))
    print("="*70)

    # Load robot genome
    print(f"\nLoading robot from: {robot_file}")
    try:
        with open(robot_file, 'rb') as f:
            voxel_grid = pickle.load(f)
        print(f"  Loaded successfully!")
    except FileNotFoundError:
        print(f"  ERROR: File not found!")
        print(f"  Run evolution first to generate best_robot.pkl")
        return

    # Create robot
    robot = VoxelRobot(voxel_grid, voxel_size=0.01)

    print(f"\nRobot structure:")
    print(f"  Nodes: {len(robot.nodes)}")
    print(f"  Springs: {len(robot.springs)}")

    actuator_count = len([s for s in robot.springs if s['is_actuator']])
    print(f"  Actuators: {actuator_count}")

    # Count materials
    material_names = {
        1: "Active 0° (green)",
        2: "Active 180° (red)",
        3: "Soft passive (cyan)",
        4: "Stiff passive (blue)"
    }

    print(f"\n  Materials:")
    for i in range(1, 5):
        count = np.sum(voxel_grid == i)
        if count > 0:
            print(f"    {material_names[i]}: {count} voxels")

    # Initialize physics
    print(f"\nInitializing physics...")
    physics = OptimizedCUDAPhysicsEngine(default_timestep=0.001)
    physics.add_robot(robot)

    # Set initial position (on ground, centered)
    initial_pos = physics.get_positions()
    initial_pos[:, 0] -= np.mean(initial_pos[:, 0])  # Center X
    initial_pos[:, 2] -= np.mean(initial_pos[:, 2])  # Center Z
    initial_pos[:, 1] -= np.min(initial_pos[:, 1]) - 0.005  # On ground
    physics.d_positions[:len(initial_pos)] = cp.array(initial_pos)

    initial_com = robot.get_center_of_mass(initial_pos)

    print(f"  Initial COM: ({initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f})")

    # Create 3D viewer if graphics enabled
    viewer = None
    if use_graphics:
        print(f"\nLaunching 3D viewer...")
        print(f"\nControls:")
        print(f"  - Left-drag mouse: Rotate view")
        print(f"  - Scroll wheel: Zoom in/out")
        print(f"  - R key: Reset camera to isometric view")
        print(f"  - 1 key: Above ground view")
        print(f"  - 2 key: Side view")
        print(f"  - 3 key: Below ground view")
        print(f"  - ESC: Exit")
        print(f"\n" + "="*70 + "\n")

        try:
            viewer = RobotViewer(width=1280, height=720)
        except Exception as e:
            print(f"Warning: Could not initialize 3D viewer: {e}")
            print(f"Falling back to text-only mode\n")
            use_graphics = False

    # Run simulation
    print(f"Running {simulation_time:.1f}s simulation...")

    if not use_graphics:
        print(f"\nTime  | X-pos   | Y-pos   | Z-pos   | XZ-Displacement")
        print("-" * 60)

    steps = int(simulation_time / 0.001)
    physics_steps_per_frame = 5  # Run 5 physics steps per frame for smooth 60fps rendering

    for step in range(steps):
        physics.step(0.001)

        # Update 3D viewer
        if use_graphics and viewer and step % physics_steps_per_frame == 0:
            positions = physics.get_positions()

            # Convert springs to format expected by viewer
            spring_data = {
                'indices': [],
                'is_actuator': [],
                'material': []
            }
            for spring in robot.springs:
                spring_data['indices'].append(spring['indices'])
                spring_data['is_actuator'].append(spring['is_actuator'])
                spring_data['material'].append(spring['material'])

            # Render (returns False if window closed)
            if not viewer.render(positions, spring_data):
                print("\nViewer window closed by user")
                break

        # Print every 0.5 seconds (text mode or alongside graphics)
        if step % 500 == 0:
            pos = physics.get_positions()
            com = robot.get_center_of_mass(pos)
            xz_disp = np.sqrt((com[0]-initial_com[0])**2 + (com[2]-initial_com[2])**2)
            time = step * 0.001

            if use_graphics:
                print(f"t={time:4.1f}s: COM=({com[0]:7.4f}, {com[1]:7.4f}, {com[2]:7.4f}), Disp={xz_disp:7.4f}m")
            else:
                print(f"{time:4.1f}s | {com[0]:7.4f} | {com[1]:7.4f} | {com[2]:7.4f} | {xz_disp:7.4f}m")

    # Cleanup viewer
    if viewer:
        import pygame
        pygame.quit()

    # Final results
    final_pos = physics.get_positions()
    final_com = robot.get_center_of_mass(final_pos)
    total_displacement = np.sqrt((final_com[0]-initial_com[0])**2 + (final_com[2]-initial_com[2])**2)

    body_size = robot.get_bounding_box_size()
    body_length = max(body_size[0], 0.001)
    fitness = total_displacement / (body_length * simulation_time)

    print(f"\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"\nInitial COM: ({initial_com[0]:.4f}, {initial_com[1]:.4f}, {initial_com[2]:.4f})")
    print(f"Final COM:   ({final_com[0]:.4f}, {final_com[1]:.4f}, {final_com[2]:.4f})")
    print(f"\nXZ Displacement: {total_displacement:.4f}m")
    print(f"Body length: {body_length:.4f}m")
    print(f"Fitness: {fitness:.2f}")

    if total_displacement > 0.01:
        print(f"\nRobot successfully moved {total_displacement*100:.1f}cm!")
    else:
        print(f"\nRobot barely moved (may be passive or unstable)")

    print("="*70)

    return fitness

if __name__ == "__main__":
    # Parse command line arguments
    use_graphics = True
    robot_file = 'best_robot.pkl'

    for arg in sys.argv[1:]:
        if arg == '--no-graphics':
            use_graphics = False
            print("Running in text-only mode (--no-graphics flag)\n")
        elif not arg.startswith('--'):
            robot_file = arg

    load_and_visualize(robot_file, simulation_time=5.0, use_graphics=use_graphics)
