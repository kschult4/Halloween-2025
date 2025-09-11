#!/usr/bin/env python3
"""
Standalone Mask Editor for Halloween Projection Mapper
Interactive tool for adjusting projection masks without video playback.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import cv2
import numpy as np
from mask_manager import MaskManager

class MaskEditor:
    """Standalone mask editing application."""
    
    def __init__(self):
        self.mask_manager = MaskManager()
        self.window_name = "Halloween Projection - Mask Editor"
        
        # Create test pattern
        self.test_pattern = self._create_test_pattern()
        
        # Setup window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 720)  # Scaled down for editing
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        
        # Start in edit mode
        self.mask_manager.is_editing = True
    
    def _create_test_pattern(self) -> np.ndarray:
        """Create a test pattern to help visualize mask alignment."""
        pattern = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # Create grid pattern
        grid_size = 100
        for y in range(0, 1080, grid_size):
            cv2.line(pattern, (0, y), (1920, y), (100, 100, 100), 1)
        for x in range(0, 1920, grid_size):
            cv2.line(pattern, (x, 0), (x, 1080), (100, 100, 100), 1)
        
        # Draw stair outlines
        for i in range(6):
            y_start = i * 180
            y_end = (i + 1) * 180
            
            # Different color for each stair
            hue = int(i * 180 / 6)
            color_hsv = np.uint8([[[hue, 255, 200]]])
            color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
            color = (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))
            
            # Fill with semi-transparent color
            cv2.rectangle(pattern, (0, y_start), (1920, y_end), color, -1)
            
            # Add stair number
            cv2.putText(pattern, f"STAIR {i + 1}", 
                       (960 - 100, y_start + 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            
            # Draw border
            cv2.rectangle(pattern, (0, y_start), (1920, y_end), (255, 255, 255), 3)
        
        return pattern
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Scale mouse coordinates and pass to mask manager."""
        # Scale coordinates from display to full resolution
        scale_x = 1920 / 1280
        scale_y = 1080 / 720
        
        full_x = int(x * scale_x)
        full_y = int(y * scale_y)
        
        self.mask_manager.handle_mouse_event(event, full_x, full_y, flags, param)
    
    def run(self):
        """Run the mask editor."""
        print("Halloween Projection Mapper - Mask Editor")
        print("=" * 50)
        print("Controls:")
        print("  - Drag corners to adjust masks")
        print("  - Press 'S' to save configuration")
        print("  - Press 'R' to reset to defaults")
        print("  - Press 'H' to toggle help")
        print("  - Press ESC or 'Q' to quit")
        print("\nAdjust masks to match your physical stair layout.")
        print("Each colored rectangle represents one stair.")
        
        show_help = True
        
        while True:
            # Create display frame
            display_frame = self.test_pattern.copy()
            
            # Apply mask overlay
            self.mask_manager.draw_edit_overlay(display_frame)
            
            # Add help text
            if show_help:
                help_text = [
                    "MASK EDITOR - Adjust corners to match physical stairs",
                    "S: Save | R: Reset | H: Toggle help | ESC/Q: Quit"
                ]
                
                for i, text in enumerate(help_text):
                    cv2.putText(display_frame, text, (10, display_frame.shape[0] - 60 + i * 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Scale down for display
            display_scaled = cv2.resize(display_frame, (1280, 720))
            cv2.imshow(self.window_name, display_scaled)
            
            # Handle keyboard input
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27 or key == ord('q'):  # ESC or Q
                break
            elif key == ord('h'):
                show_help = not show_help
            elif key != 255:
                handled = self.mask_manager.handle_keyboard_event(key)
                if handled and key == ord('s'):
                    print("✅ Mask configuration saved!")
                elif handled and key == ord('r'):
                    print("🔄 Masks reset to defaults")
        
        cv2.destroyAllWindows()
        print("\nMask editor closed.")
        
        # Print final mask positions
        print("\nFinal mask configuration:")
        for i, mask in enumerate(self.mask_manager.masks):
            corners = mask.get_corner_positions()
            print(f"  Stair {i + 1}: {corners}")

def main():
    """Run the mask editor."""
    try:
        editor = MaskEditor()
        editor.run()
    except KeyboardInterrupt:
        print("\nMask editor interrupted by user")
    except Exception as e:
        print(f"Error running mask editor: {e}")

if __name__ == "__main__":
    main()