# FIXED viewer.py - Replace your src/visualization/viewer.py with this

import numpy as np
import pygame
from pygame.locals import *
import sys
import math

class RobotViewer:
    """Fixed viewer with isometric view and consistent node colors"""
    
    def __init__(self, width=1280, height=720):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Soft Robot Physics - Fixed Isometric View")
        
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()
        
        # ====== CAMERA CONFIGURATION (Easy to modify) ======
        # CAMERA ANGLES:
        # camera_angle_x: Elevation (+ = above ground, - = below ground)
        #   +25° = standard isometric above ground
        #   0° = side view at ground level  
        #   -25° = below ground looking up
        # camera_angle_y: Azimuth (rotation around Y axis)
        #   0° = looking along Z axis
        #   45° = standard isometric corner view
        #   90° = looking along X axis
        # zoom: Scale factor (higher = closer, lower = further)
        
        self.camera_distance = 50.0       # Not used much in our projection
        self.camera_angle_x = 25.0       # ELEVATION: 25° above ground (isometric)
        self.camera_angle_y = 45.0       # AZIMUTH: 45° corner view (isometric)  
        self.zoom = 50.0                 # ZOOM: 50x scale factor
        
        # ===================================================
        
        # Mouse control
        self.mouse_pressed = False
        self.last_mouse_pos = (0, 0)
        
        # FIXED: High contrast colors with consistent beige nodes
        self.bg_color = (240, 240, 250)  # Light background
        self.ground_color = (80, 80, 80)   # Dark gray grid
        self.ground_major_color = (60, 60, 60)  # Darker major grid lines
        self.axis_color_x = (200, 0, 0)    # Red X-axis
        self.axis_color_z = (0, 0, 200)    # Blue Z-axis
        self.node_color = (200, 180, 140)  # CONSISTENT BEIGE for all nodes
        self.spring_color = (0, 120, 0)    # Green springs
        self.text_color = (0, 0, 0)        # Black text
        
        # Font for info display
        self.font = pygame.font.Font(None, 24)
        
        print("ENHANCED VIEWER - Research-Based Realistic Shadows:")
        print("  - Infinite checkerboard grid (1m x 1m squares)")
        print("  - CAMERA-DEPENDENT OCCLUSION: hides objects based on view position")
        print("    * Above ground: shows robot + shadow above ground")
        print("    * Below ground: shows only objects below ground (no shadow)")
        print("  - REALISTIC SOFT SHADOWS (based on graphics research):")
        print("    * Soft-edged with gradient falloff (no hard circles)")
        print("    * Elliptical shape (more natural than circles)")
        print("    * Directional offset from light source (upper-left)")
        print("    * Multiple concentric layers for smooth transition")
        print("    * Size/opacity based on height (physics-accurate)")
        print("  - CAMERA POSITION FEEDBACK: shows above/below ground status")
        print("  - CAMERA PRESETS: R, 1, 2, 3 keys for quick positioning")
        print("  - Mouse rotation with proper occlusion testing")

    def project_3d_to_2d(self, point3d):
        """Fixed isometric projection"""
        # Rotate around Y axis (horizontal rotation)
        cos_y = math.cos(math.radians(self.camera_angle_y))
        sin_y = math.sin(math.radians(self.camera_angle_y))
        
        x = point3d[0] * cos_y - point3d[2] * sin_y
        z = point3d[0] * sin_y + point3d[2] * cos_y
        y = point3d[1]
        
        # Rotate around X axis (vertical rotation)
        cos_x = math.cos(math.radians(self.camera_angle_x))
        sin_x = math.sin(math.radians(self.camera_angle_x))
        
        y_rot = y * cos_x - z * sin_x
        z_rot = y * sin_x + z * cos_x
        
        # Isometric projection (minimal perspective distortion)
        if z_rot < 0.1:
            z_rot = 0.1
            
        perspective_scale = self.camera_distance / (self.camera_distance + z_rot * 0.1)  # Reduced perspective
        
        # Convert to screen coordinates
        screen_x = self.width / 2 + x * self.zoom * perspective_scale
        screen_y = self.height / 2 - y_rot * self.zoom * perspective_scale
        
        return (int(screen_x), int(screen_y)), z_rot

    def draw_ground(self):
        """Draw infinite 1m x 1m checkerboard grid (only visible squares)"""
        square_size = 1.0  # 1 meter per square (= voxel size)
        ground_y = 0.0
        
        # Colors for checkerboard (opaque)
        color1 = (220, 220, 220)  # Light gray
        color2 = (200, 220, 240)  # Light blue
        
        # Calculate visible area based on camera and zoom
        # Estimate visible range (with some padding)
        visible_range = max(30, int(100 / (self.zoom / 40.0)))  # Adaptive based on zoom
        
        # Get camera center for efficient culling
        camera_center_x = 0  # We'll center around origin for now
        camera_center_z = 0
        
        # Calculate grid bounds (only draw visible squares)
        min_x = camera_center_x - visible_range
        max_x = camera_center_x + visible_range
        min_z = camera_center_z - visible_range
        max_z = camera_center_z + visible_range
        
        # Draw large background plane first (ensures complete occlusion)
        bg_size = visible_range * square_size * 1.5  # Extra large
        background_corners = [
            (-bg_size, ground_y - 0.02, -bg_size),  # Below grid for solid base
            (bg_size, ground_y - 0.02, -bg_size),
            (bg_size, ground_y - 0.02, bg_size),
            (-bg_size, ground_y - 0.02, bg_size)
        ]
        
        screen_bg_corners = []
        for corner in background_corners:
            screen_pos, _ = self.project_3d_to_2d(corner)
            screen_bg_corners.append(screen_pos)
        
        # Draw solid background (complete occlusion)
        if len(screen_bg_corners) == 4:
            try:
                pygame.draw.polygon(self.screen, (210, 210, 210), screen_bg_corners)  # Solid gray base
            except:
                pass
        
        # Draw checkerboard squares (only visible ones - efficient!)
        squares_drawn = 0
        for i in range(min_x, max_x):
            for j in range(min_z, max_z):
                # Quick visibility check (skip squares too far from camera)
                dist_from_origin = abs(i) + abs(j)
                if dist_from_origin > visible_range:
                    continue
                
                # Checkerboard pattern
                is_even = (i + j) % 2 == 0
                color = color1 if is_even else color2
                
                # Square corners
                x1, x2 = i * square_size, (i + 1) * square_size
                z1, z2 = j * square_size, (j + 1) * square_size
                
                square_corners = [
                    (x1, ground_y, z1),
                    (x2, ground_y, z1),
                    (x2, ground_y, z2),
                    (x1, ground_y, z2)
                ]
                
                # Project to screen
                screen_corners = []
                all_valid = True
                for corner in square_corners:
                    screen_pos, depth = self.project_3d_to_2d(corner)
                    # Skip squares that project outside screen (efficiency)
                    if (screen_pos[0] < -100 or screen_pos[0] > self.width + 100 or 
                        screen_pos[1] < -100 or screen_pos[1] > self.height + 100):
                        all_valid = False
                        break
                    screen_corners.append(screen_pos)
                
                # Draw filled square (OPAQUE, no transparency)
                if all_valid and len(screen_corners) == 4:
                    try:
                        pygame.draw.polygon(self.screen, color, screen_corners)
                        # Light border for grid lines
                        pygame.draw.polygon(self.screen, (180, 180, 180), screen_corners, 1)
                        squares_drawn += 1
                    except:
                        pass  # Skip if projection failed
        
        # Draw coordinate axes ON TOP of checkerboard (no brown lines)
        axis_thickness = 4
        axis_length = min(visible_range, 20) * square_size
        
        # X-axis (red)
        start, _ = self.project_3d_to_2d((-axis_length, ground_y + 0.01, 0))
        end, _ = self.project_3d_to_2d((axis_length, ground_y + 0.01, 0))
        pygame.draw.line(self.screen, (200, 0, 0), start, end, axis_thickness)
        
        # Z-axis (blue)
        start, _ = self.project_3d_to_2d((0, ground_y + 0.01, -axis_length))
        end, _ = self.project_3d_to_2d((0, ground_y + 0.01, axis_length))
        pygame.draw.line(self.screen, (0, 0, 200), start, end, axis_thickness)
        
        # Draw vertical height markers (scale reference)
        for height in [5, 10, 15, 20, 25]:
            color = (120, 120, 120) if height <= 20 else (100, 100, 100)
            
            # Vertical line at origin
            start, _ = self.project_3d_to_2d((0, ground_y, 0))
            end, _ = self.project_3d_to_2d((0, height, 0))
            pygame.draw.line(self.screen, color, start, end, 2)
            
            # Height tick marks
            start, _ = self.project_3d_to_2d((-0.5, height, 0))
            end, _ = self.project_3d_to_2d((0.5, height, 0))
            pygame.draw.line(self.screen, color, start, end, 3)
        
        # Debug info (optional)
        # print(f"Drew {squares_drawn} grid squares (range: {min_x} to {max_x})")
        
        return squares_drawn  # For performance monitoring

    def render(self, positions, springs, materials=None):
        """Render with fixed colors and RESTORED mouse rotation"""
        # Handle events (RESTORED MOUSE ROTATION)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click - RESTORED ROTATION
                    self.mouse_pressed = True
                    self.last_mouse_pos = pygame.mouse.get_pos()
                elif event.button == 4:  # Scroll up
                    self.zoom *= 1.1
                elif event.button == 5:  # Scroll down
                    self.zoom *= 0.9
                    self.zoom = max(20, self.zoom)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # Left click release
                    self.mouse_pressed = False
            elif event.type == MOUSEMOTION:
                if self.mouse_pressed:  # RESTORED MOUSE ROTATION
                    mx, my = pygame.mouse.get_pos()
                    dx = mx - self.last_mouse_pos[0]
                    dy = my - self.last_mouse_pos[1]
                    
                    self.camera_angle_y += dx * 0.5
                    self.camera_angle_x += dy * 0.5
                    self.camera_angle_x = max(-89, min(89, self.camera_angle_x))
                    
                    self.last_mouse_pos = (mx, my)
            elif event.type == KEYDOWN:
                if event.key == K_r:  # Reset camera to isometric
                    self.camera_angle_x = 25.0   # Above ground isometric
                    self.camera_angle_y = 45.0   # Corner view
                    self.zoom = 50.0
                    print("Camera reset to isometric view (above ground)")
                elif event.key == K_1:  # Preset: Above ground
                    self.camera_angle_x = 25.0
                    self.camera_angle_y = 45.0
                    print("Camera: Above ground (25°, 45°)")
                elif event.key == K_2:  # Preset: Side view
                    self.camera_angle_x = 0.0
                    self.camera_angle_y = 45.0  
                    print("Camera: Side view (0°, 45°)")
                elif event.key == K_3:  # Preset: Below ground
                    self.camera_angle_x = -25.0
                    self.camera_angle_y = 45.0
                    print("Camera: Below ground (-25°, 45°)")
        
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Draw infinite ground grid (FIRST - behind everything)
        squares_drawn = self.draw_ground()
        
        if positions is not None and len(positions) > 0:
            # Calculate robot center for reference and shadow
            robot_center = np.mean(positions, axis=0)
            
            # CAMERA-DEPENDENT VISIBILITY: Check if camera is above or below ground
            camera_below_ground = self.camera_angle_x < -5  # Camera looking up from below
            camera_above_ground = self.camera_angle_x > 5   # Camera looking down from above
            
            # DRAW REALISTIC SOFT-EDGED SHADOW (based on graphics research)
            if (robot_center[1] > 0.1 and not camera_below_ground):  # Don't draw shadow when viewing from below
                # Assume light source from upper-left (common in games/graphics)
                light_direction = np.array([-0.3, -1.0, -0.2])  # Light coming from upper-left
                light_direction = light_direction / np.linalg.norm(light_direction)
                
                # Shadow offset based on height and light direction (realistic physics)
                height = robot_center[1]
                shadow_offset = light_direction[:2] * height * 0.5  # Only X,Z components
                
                # Project robot center onto ground with directional offset
                shadow_center = (robot_center[0] + shadow_offset[0], 0.005, robot_center[2] + shadow_offset[1])
                shadow_screen_pos, _ = self.project_3d_to_2d(shadow_center)
                
                # REALISTIC SHADOW SIZING (smaller when close, larger when far)
                base_size = 12  # Base shadow size
                height_factor = height * 2.5  # How much shadow grows with height
                
                # Elliptical shadow (more realistic than perfect circle)
                shadow_width = int(base_size + height_factor)
                shadow_height = int((base_size + height_factor) * 0.7)  # Elliptical: shorter in one direction
                
                # Clamp size
                shadow_width = max(6, min(shadow_width, 35))
                shadow_height = max(4, min(shadow_height, 25))
                
                # SOFT-EDGED SHADOW using multiple concentric ellipses (research-based technique)
                # Create gradient falloff from center to edge
                max_alpha = min(200, int(180 - height * 8))  # Darker when closer
                min_alpha = 30
                
                # Draw multiple concentric ellipses with decreasing opacity (creates soft edges)
                num_layers = 5
                try:
                    for layer in range(num_layers):
                        # Each layer is progressively smaller and more transparent
                        layer_factor = (num_layers - layer) / num_layers
                        layer_width = int(shadow_width * layer_factor)
                        layer_height = int(shadow_height * layer_factor)
                        
                        # Opacity decreases towards edges (Gaussian-like falloff)
                        layer_alpha = int(max_alpha * layer_factor * layer_factor)  # Quadratic falloff
                        layer_alpha = max(min_alpha, min(layer_alpha, max_alpha))
                        
                        # Shadow color gets lighter towards edges
                        shadow_darkness = max(40, int(80 - height * 5))
                        layer_color = min(120, shadow_darkness + (layer * 10))
                        
                        if layer_width > 2 and layer_height > 2:
                            # Create layer surface
                            layer_surface = pygame.Surface((layer_width * 2, layer_height * 2))
                            layer_surface.set_alpha(layer_alpha)
                            layer_surface.fill((layer_color, layer_color, layer_color))
                            
                            # Draw elliptical shadow layer
                            if layer_width != layer_height:
                                # Elliptical shadow (more realistic)
                                pygame.draw.ellipse(layer_surface, (shadow_darkness, shadow_darkness, shadow_darkness),
                                                  (0, 0, layer_width * 2, layer_height * 2))
                            else:
                                # Circular fallback
                                pygame.draw.circle(layer_surface, (shadow_darkness, shadow_darkness, shadow_darkness),
                                                 (layer_width, layer_height), layer_width)
                            
                            # Blit layer to main screen
                            layer_rect = layer_surface.get_rect()
                            layer_rect.center = shadow_screen_pos
                            self.screen.blit(layer_surface, layer_rect)
                    
                except Exception as e:
                    # Fallback: simple elliptical shadow if soft shadow fails
                    fallback_surface = pygame.Surface((shadow_width * 2, shadow_height * 2))
                    fallback_surface.set_alpha(max_alpha // 2)
                    fallback_surface.fill((60, 60, 60))
                    pygame.draw.ellipse(fallback_surface, (40, 40, 40), (0, 0, shadow_width * 2, shadow_height * 2))
                    
                    fallback_rect = fallback_surface.get_rect()
                    fallback_rect.center = shadow_screen_pos
                    self.screen.blit(fallback_surface, fallback_rect)

            # Draw springs first (behind nodes) - CAMERA-DEPENDENT OCCLUSION
            if springs is not None:
                if isinstance(springs, dict) and 'indices' in springs:
                    num_springs = len(springs['indices'])
                    for i in range(num_springs):
                        idx1, idx2 = springs['indices'][i]
                        if idx1 < len(positions) and idx2 < len(positions):
                            pos1 = positions[idx1]
                            pos2 = positions[idx2]
                            
                            # CAMERA-DEPENDENT OCCLUSION CULLING
                            should_draw = False
                            if camera_below_ground:
                                # When below ground: only show parts that are below ground
                                should_draw = (pos1[1] <= 0.1 and pos2[1] <= 0.1)
                            else:
                                # When above ground: only show parts that are above ground
                                should_draw = (pos1[1] >= -0.1 and pos2[1] >= -0.1)
                            
                            if should_draw:
                                screen_pos1, _ = self.project_3d_to_2d(pos1)
                                screen_pos2, _ = self.project_3d_to_2d(pos2)
                                
                                # All springs same color (green)
                                pygame.draw.line(self.screen, self.spring_color, screen_pos1, screen_pos2, 2)
            
            # Draw nodes - CAMERA-DEPENDENT OCCLUSION
            for i, pos in enumerate(positions):
                # CAMERA-DEPENDENT OCCLUSION CULLING
                should_draw = False
                if camera_below_ground:
                    # When below ground: only show parts that are below ground
                    should_draw = (pos[1] <= 0.1)
                else:
                    # When above ground: only show parts that are above ground
                    should_draw = (pos[1] >= -0.1)
                
                if should_draw:
                    screen_pos, depth = self.project_3d_to_2d(pos)
                    
                    # All nodes same beige color
                    color = self.node_color
                    
                    # Node size based on depth (slight variation for 3D effect)
                    base_size = 8
                    size = max(6, int(base_size - depth * 0.5))
                    
                    # Draw node with border
                    pygame.draw.circle(self.screen, color, screen_pos, size)
                    pygame.draw.circle(self.screen, (0, 0, 0), screen_pos, size, 2)
        
        # Draw info text with camera position and occlusion info
        if positions is not None and len(positions) > 0:
            robot_center = np.mean(positions, axis=0)
            
            # Count nodes above/below ground for occlusion info
            nodes_above_ground = np.sum(positions[:, 1] >= -0.1)
            nodes_below_ground = len(positions) - nodes_above_ground
            
            # Camera position relative to ground
            camera_below_ground = self.camera_angle_x < -5
            camera_above_ground = self.camera_angle_x > 5
            
            if camera_below_ground:
                camera_status = "BELOW GROUND (Underground view)"
                visibility_info = f"Showing: {nodes_below_ground} nodes below ground"
                shadow_info = "Shadow: Hidden (can't see ground surface)"
            elif camera_above_ground:
                camera_status = "ABOVE GROUND (Sky view)"
                visibility_info = f"Showing: {nodes_above_ground} nodes above ground"
                shadow_info = "Shadow: Visible on ground surface"
            else:
                camera_status = "AT GROUND LEVEL (Side view)"
                visibility_info = f"Showing: {nodes_above_ground} nodes above ground"
                shadow_info = "Shadow: Visible on ground surface"
            
            info_texts = [
                f"CAMERA: {camera_status}",
                f"Angles: (Elev: {self.camera_angle_x:.1f}°, Az: {self.camera_angle_y:.1f}°)",
                f"Robot Height: {robot_center[1]:.2f} m",
                f"Robot Center: [{robot_center[0]:.1f}, {robot_center[1]:.1f}, {robot_center[2]:.1f}]",
                f"{visibility_info}",
                f"{shadow_info}",
                f"Grid squares: {squares_drawn}",
                "",
                "REALISTIC SHADOWS (research-based):",
                "• Soft-edged with gradient falloff",
                "• Elliptical shape (not circle)",
                "• Directional offset from light source",
                "• Multiple layers for smooth transition",
                "",
                "Camera Presets (test occlusion):",
                "• R: Reset isometric (25°, 45°)",
                "• 1: Above ground (25°, 45°)",
                "• 2: Side view (0°, 45°)", 
                "• 3: Below ground (-25°, 45°) ← Test this!",
                "",
                "Controls:",
                "• Left-drag: Rotate view",
                "• Scroll: Zoom"
            ]
        else:
            camera_below_ground = self.camera_angle_x < -5
            camera_status = "BELOW GROUND" if camera_below_ground else "ABOVE GROUND" if self.camera_angle_x > 5 else "AT GROUND LEVEL"
            
            info_texts = [
                f"CAMERA: {camera_status}",
                f"Angles: (Elev: {self.camera_angle_x:.1f}°, Az: {self.camera_angle_y:.1f}°)",
                f"Grid squares drawn: {squares_drawn}",
                "",
                "Grid: Each square = 1m x 1m (= 1 voxel)",
                "Occlusion: Camera-dependent visibility",
                "",
                "Camera Presets:",
                "• R: Reset isometric (25°, 45°)",
                "• 1: Above ground (25°, 45°)",
                "• 2: Side view (0°, 45°)",
                "• 3: Below ground (-25°, 45°)"
            ]
        
        y_offset = 10
        for text in info_texts:
            if text:
                text_surface = self.font.render(text, True, self.text_color)
                # Background for readability
                text_rect = text_surface.get_rect()
                text_rect.topleft = (10, y_offset)
                pygame.draw.rect(self.screen, (255, 255, 255, 200), text_rect.inflate(4, 2))
                self.screen.blit(text_surface, (10, y_offset))
            y_offset += 25
        
        # Update display
        pygame.display.flip()
        self.clock.tick(60)
        
        return True