# Add this new class to your src/visualization/ directory as video_recorder.py

import numpy as np
import pygame
import os
from pygame.locals import *
import math

class HeadlessVideoRecorder:
    """Record robot visualization to video files without displaying windows"""
    
    def __init__(self, width=1280, height=720, fps=30):
        # Initialize pygame in headless mode
        os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Headless mode
        pygame.init()
        
        self.width = width
        self.height = height
        self.fps = fps
        self.screen = pygame.Surface((width, height))  # Off-screen surface
        
        # Camera parameters
        self.camera_distance = 0.5
        self.camera_angle_x = 30.0
        self.camera_angle_y = 45.0
        self.zoom = 40.0
        
        # Colors
        self.bg_color = (20, 20, 20)
        self.ground_color = (80, 80, 80)
        self.node_color = (100, 150, 200)
        self.spring_color = (50, 200, 50)
        self.actuator_color = (200, 50, 50)
        self.text_color = (255, 255, 255)
        
        # Font
        self.font = pygame.font.Font(None, 24)
        
        # Recording state
        self.frames = []
        self.recording = False
    
    def start_recording(self):
        """Start recording frames"""
        self.frames = []
        self.recording = True
        print("Started video recording...")
    
    def stop_recording(self):
        """Stop recording"""
        self.recording = False
        print(f"Stopped recording. Captured {len(self.frames)} frames.")
    
    def project_3d_to_2d(self, point3d):
        """Simple 3D to 2D projection (same as viewer.py)"""
        # Rotate around Y axis
        cos_y = math.cos(math.radians(self.camera_angle_y))
        sin_y = math.sin(math.radians(self.camera_angle_y))
        
        x = point3d[0] * cos_y - point3d[2] * sin_y
        z = point3d[0] * sin_y + point3d[2] * cos_y
        y = point3d[1]
        
        # Rotate around X axis
        cos_x = math.cos(math.radians(self.camera_angle_x))
        sin_x = math.sin(math.radians(self.camera_angle_x))
        
        y_rot = y * cos_x - z * sin_x
        z_rot = y * sin_x + z * cos_x
        
        # Perspective projection
        if z_rot < 0.1:
            z_rot = 0.1
            
        perspective_scale = self.camera_distance / (self.camera_distance + z_rot)
        
        screen_x = self.width / 2 + x * self.zoom * perspective_scale
        screen_y = self.height / 2 - y_rot * self.zoom * perspective_scale
        
        return (int(screen_x), int(screen_y)), z_rot
    
    def draw_ground(self):
        """Draw ground grid"""
        grid_size = 10
        grid_step = 0.1
        
        for i in range(-grid_size, grid_size + 1):
            # X-direction lines
            start, _ = self.project_3d_to_2d((i * grid_step, 0, -grid_size * grid_step))
            end, _ = self.project_3d_to_2d((i * grid_step, 0, grid_size * grid_step))
            pygame.draw.line(self.screen, self.ground_color, start, end, 1)
            
            # Z-direction lines
            start, _ = self.project_3d_to_2d((-grid_size * grid_step, 0, i * grid_step))
            end, _ = self.project_3d_to_2d((grid_size * grid_step, 0, i * grid_step))
            pygame.draw.line(self.screen, self.ground_color, start, end, 1)
    
    def render_frame(self, positions, springs, time_info="", robot_info=""):
        """Render a single frame to memory"""
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Draw ground
        self.draw_ground()
        
        if positions is not None and len(positions) > 0:
            # Adjust positions for better view
            robot_center = np.mean(positions, axis=0)
            adjusted_positions = positions - robot_center + np.array([0, 0.1, 0])
            
            # Draw springs
            if springs is not None and isinstance(springs, dict) and 'indices' in springs:
                num_springs = len(springs['indices'])
                for i in range(num_springs):
                    idx1, idx2 = springs['indices'][i]
                    if idx1 < len(adjusted_positions) and idx2 < len(adjusted_positions):
                        pos1 = adjusted_positions[idx1]
                        pos2 = adjusted_positions[idx2]
                        
                        screen_pos1, _ = self.project_3d_to_2d(pos1)
                        screen_pos2, _ = self.project_3d_to_2d(pos2)
                        
                        # Color based on spring type
                        is_actuator = springs['is_actuator'][i] if 'is_actuator' in springs else False
                        color = self.actuator_color if is_actuator else self.spring_color
                        
                        pygame.draw.line(self.screen, color, screen_pos1, screen_pos2, 2)
            
            # Draw nodes
            for i, pos in enumerate(adjusted_positions):
                screen_pos, depth = self.project_3d_to_2d(pos)
                
                # Node size based on height
                size = int(4 + pos[1] * 10)
                size = max(3, min(8, size))
                
                # Color based on height
                height_factor = min(1.0, max(0.0, pos[1] * 2))
                color = (
                    int(self.node_color[0] * (1 - height_factor) + 200 * height_factor),
                    int(self.node_color[1]),
                    int(self.node_color[2] * (1 - height_factor) + 100 * height_factor)
                )
                
                pygame.draw.circle(self.screen, color, screen_pos, size)
                pygame.draw.circle(self.screen, (255, 255, 255), screen_pos, size, 1)
        
        # Draw info text
        info_texts = [
            f"BEST ROBOT EVOLUTION RECORDING",
            robot_info,
            time_info,
            f"Nodes: {len(positions) if positions is not None else 0}",
            f"Springs: {len(springs['indices']) if springs is not None and isinstance(springs, dict) else 0}",
        ]
        
        y_offset = 10
        for text in info_texts:
            if text:  # Skip empty strings
                text_surface = self.font.render(text, True, self.text_color)
                self.screen.blit(text_surface, (10, y_offset))
                y_offset += 25
        
        # Capture frame if recording
        if self.recording:
            # Convert pygame surface to numpy array
            frame = pygame.surfarray.array3d(self.screen)
            frame = np.transpose(frame, (1, 0, 2))  # Correct orientation
            self.frames.append(frame.copy())
    
    def save_video(self, output_path, robot_stats=""):
        """Save recorded frames to video file"""
        if len(self.frames) == 0:
            print("No frames to save!")
            return
        
        try:
            import cv2
            
            # Video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))
            
            print(f"Saving {len(self.frames)} frames to {output_path}...")
            
            for i, frame in enumerate(self.frames):
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
                
                if i % 30 == 0:  # Progress every second
                    print(f"  Saved {i}/{len(self.frames)} frames...")
            
            out.release()
            print(f"✓ Video saved successfully to {output_path}")
            
            # Also save a text file with robot stats
            if robot_stats:
                stats_path = output_path.replace('.mp4', '_stats.txt')
                with open(stats_path, 'w') as f:
                    f.write(robot_stats)
                print(f"✓ Robot stats saved to {stats_path}")
            
        except ImportError:
            print("OpenCV not available. Saving as image sequence instead...")
            self.save_image_sequence(output_path.replace('.mp4', ''))
    
    def save_image_sequence(self, output_dir):
        """Save frames as image sequence (fallback if no OpenCV)"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for i, frame in enumerate(self.frames):
            frame_path = os.path.join(output_dir, f'frame_{i:04d}.png')
            pygame.image.save(pygame.surfarray.make_surface(frame.transpose(1, 0, 2)), frame_path)
        
        print(f"✓ Saved {len(self.frames)} frames to {output_dir}/")

# Modified main.py visualization function
def record_final_robot_video(best_individual, physics_engine, output_dir, simulation_time=10.0):
    """Record the final best robot to video file"""
    
    # Create recorder
    recorder = HeadlessVideoRecorder(width=1280, height=720, fps=30)
    
    # Get robot and controller
    robot = best_individual.genome.to_phenotype()
    controller = best_individual.controller
    
    robot_info = (f"Fitness: {best_individual.fitness:.4f} | "
                 f"Nodes: {len(robot.nodes)} | "
                 f"Springs: {len(robot.springs)} | "
                 f"Actuators: {len([s for s in robot.springs if s['is_actuator']])}")
    
    # Reset physics
    physics_engine.reset()
    physics_engine.add_robot(robot)
    
    timestep = 0.005
    num_steps = int(simulation_time / timestep)
    
    print(f"Recording best robot video ({simulation_time}s @ 30fps)...")
    
    # Start recording
    recorder.start_recording()
    
    # Track trajectory
    trajectory = []
    
    for step in range(num_steps):
        # Get sensor data and run physics
        positions = physics_engine.get_positions()
        if len(positions) > 0:
            com = robot.get_center_of_mass(positions)
            trajectory.append(com.copy())
            sensor_data = np.concatenate([com, np.zeros(9)])
            
            if controller:
                control = controller.step(timestep, sensor_data)
                physics_engine.set_actuator_signals(control)
        
        physics_engine.step(timestep)
        
        # Record frame every few steps (30 FPS from 200 FPS simulation)
        if step % (200 // 30) == 0:  # Record every ~7 steps for 30 FPS
            positions = physics_engine.get_positions()
            springs = robot.get_springs()
            
            elapsed_time = step * timestep
            time_info = f"Time: {elapsed_time:.2f}s / {simulation_time:.1f}s"
            
            recorder.render_frame(positions, springs, time_info, robot_info)
        
        # Progress
        if step % 400 == 0:
            print(f"  Recording progress: {step/num_steps*100:.1f}%")
    
    # Stop recording and save
    recorder.stop_recording()
    
    # Generate stats
    if len(trajectory) > 1:
        trajectory = np.array(trajectory)
        total_distance = np.linalg.norm(trajectory[-1] - trajectory[0])
        path_length = np.sum(np.linalg.norm(np.diff(trajectory, axis=0), axis=1))
        
        robot_stats = f"""Best Robot Performance Report
=================================

Robot Statistics:
  Fitness: {best_individual.fitness:.4f}
  Age: {best_individual.age} generations
  Nodes: {len(robot.nodes)}
  Springs: {len(robot.springs)}
  Actuators: {len([s for s in robot.springs if s['is_actuator']])}

Movement Analysis:
  Starting position: [{trajectory[0][0]:.3f}, {trajectory[0][1]:.3f}, {trajectory[0][2]:.3f}]
  Final position: [{trajectory[-1][0]:.3f}, {trajectory[-1][1]:.3f}, {trajectory[-1][2]:.3f}]
  Total displacement: {total_distance:.4f} m
  Path length: {path_length:.4f} m
  Average speed: {path_length/simulation_time:.4f} m/s
  Efficiency: {total_distance/path_length:.3f}

Simulation Parameters:
  Duration: {simulation_time:.1f} seconds
  Timestep: {timestep:.3f} seconds
  Total steps: {num_steps}
"""
    else:
        robot_stats = f"Robot Statistics:\nFitness: {best_individual.fitness:.4f}\nNo movement recorded."
    
    # Save video
    video_path = os.path.join(output_dir, 'best_robot_video.mp4')
    recorder.save_video(video_path, robot_stats)
    
    return video_path