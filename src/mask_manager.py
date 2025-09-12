"""
Mask management system for Halloween Projection Mapper.
Handles 6 quadrilateral masks for stair projection with drag-and-drop corner adjustment.
"""
import json
import os
import logging
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Corner:
    """Represents a draggable corner point of a mask."""
    def __init__(self, x: int, y: int, radius: int = 10):
        self.x = x
        self.y = y
        self.radius = radius
        self.is_dragging = False
        
    @property
    def position(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this corner's drag area."""
        dx = x - self.x
        dy = y - self.y
        return (dx * dx + dy * dy) <= (self.radius * self.radius)
    
    def move_to(self, x: int, y: int):
        """Move corner to new position."""
        self.x = x
        self.y = y

class StripMask:
    """Represents a quadrilateral mask for one horizontal strip (stair)."""
    def __init__(self, strip_index: int, corners: List[Tuple[int, int]]):
        self.strip_index = strip_index
        self.corners = [Corner(x, y) for x, y in corners]
        self.color = self._get_strip_color(strip_index)
        
    def _get_strip_color(self, index: int) -> Tuple[int, int, int]:
        """Get a unique color for each strip for visualization."""
        colors = [
            (255, 100, 100),  # Light red
            (100, 255, 100),  # Light green
            (100, 100, 255),  # Light blue
            (255, 255, 100),  # Light yellow
            (255, 100, 255),  # Light magenta
            (100, 255, 255),  # Light cyan
        ]
        return colors[index % len(colors)]
    
    def get_corner_positions(self) -> List[Tuple[int, int]]:
        """Get current corner positions."""
        return [corner.position for corner in self.corners]
    
    def find_corner_at_point(self, x: int, y: int) -> Optional[Corner]:
        """Find corner that contains the given point."""
        for corner in self.corners:
            if corner.contains_point(x, y):
                return corner
        return None
    
    def get_mask_points(self) -> np.ndarray:
        """Get mask points as numpy array for OpenCV."""
        points = np.array(self.get_corner_positions(), dtype=np.int32)
        return points.reshape((-1, 1, 2))
    
    def draw_mask(self, image: np.ndarray, alpha: float = 0.3):
        """Draw mask overlay on image."""
        # Create mask overlay
        overlay = image.copy()
        points = self.get_mask_points()
        cv2.fillPoly(overlay, [points], self.color)
        
        # Blend with original image
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)
        
        # Draw outline
        cv2.polylines(image, [points], True, self.color, 2)
        
        # Draw corners
        for i, corner in enumerate(self.corners):
            color = (255, 255, 255) if corner.is_dragging else (200, 200, 200)
            cv2.circle(image, corner.position, corner.radius, color, -1)
            cv2.circle(image, corner.position, corner.radius, (0, 0, 0), 2)
            
            # Corner number
            cv2.putText(image, str(i), 
                       (corner.x - 5, corner.y + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

class MaskManager:
    """Manages all strip masks and provides editing interface."""
    
    def __init__(self, config_path: str = "config/masks.json"):
        self.config_path = config_path
        self.masks: List[StripMask] = []
        self.selected_corner: Optional[Corner] = None
        self.is_editing = False
        
        # Mouse state
        self.mouse_dragging = False
        self.last_mouse_pos = (0, 0)
        
        # Default mask configuration for 1920x1080 divided into 6 strips
        self.default_masks = self._create_default_masks()
        
        # Load existing masks or create defaults
        self.load_masks()
    
    def _create_default_masks(self) -> List[Dict]:
        """Create default mask configuration for 6 horizontal strips."""
        strip_height = 1080 // 6  # 180 pixels per strip
        masks = []
        
        for i in range(6):
            y_top = i * strip_height
            y_bottom = min((i + 1) * strip_height, 1080)
            
            # Default quadrilateral (rectangle)
            corners = [
                [0, y_top],           # Top-left
                [1920, y_top],        # Top-right
                [1920, y_bottom],     # Bottom-right
                [0, y_bottom]         # Bottom-left
            ]
            
            masks.append({"corners": corners})
        
        return masks
    
    def load_masks(self):
        """Load mask configuration from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    mask_data = data.get('strips', self.default_masks)
            else:
                logger.info(f"No mask config found at {self.config_path}, using defaults")
                mask_data = self.default_masks
            
            # Create StripMask objects
            self.masks = []
            for i, mask_info in enumerate(mask_data):
                corners = mask_info.get('corners', self.default_masks[i]['corners'])
                self.masks.append(StripMask(i, corners))
            
            logger.info(f"Loaded {len(self.masks)} masks from configuration")
            
        except Exception as e:
            logger.error(f"Failed to load masks: {e}")
            # Fallback to defaults
            self.masks = [StripMask(i, mask['corners']) for i, mask in enumerate(self.default_masks)]
    
    def save_masks(self):
        """Save current mask configuration to JSON file."""
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Prepare data for saving
            data = {
                "strips": [
                    {"corners": mask.get_corner_positions()}
                    for mask in self.masks
                ]
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved masks to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save masks: {e}")
    
    def get_mask_for_strip(self, strip_index: int) -> Optional[StripMask]:
        """Get mask for specific strip."""
        if 0 <= strip_index < len(self.masks):
            return self.masks[strip_index]
        return None
    
    def apply_masks_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply all masks to create masked output for projection."""
        if not self.masks:
            return frame
        try:
            h, w = frame.shape[:2]
            output = np.zeros_like(frame)
            transforms = self.get_projection_transforms()
            
            for i, transform in enumerate(transforms):
                # Warp the full frame using the strip-specific transform
                warped = cv2.warpPerspective(frame, transform, (w, h))
                
                # Create mask for destination quadrilateral
                dst_points = np.array(self.masks[i].get_corner_positions(), dtype=np.int32).reshape((-1, 1, 2))
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(mask, [dst_points], 255)
                
                # Composite warped strip into output using the mask
                roi = output.copy()
                roi[mask == 255] = warped[mask == 255]
                output = roi
            
            return output
        except Exception as e:
            logger.error(f"Error applying masks to frame: {e}")
            return frame
    
    def draw_edit_overlay(self, image: np.ndarray):
        """Draw editing overlay with all masks and controls."""
        if not self.is_editing:
            return
        
        # Draw all masks
        for mask in self.masks:
            mask.draw_mask(image, alpha=0.2)
        
        # Draw strip labels
        for i, mask in enumerate(self.masks):
            # Calculate center of mask for label
            corners = mask.get_corner_positions()
            center_x = sum(x for x, y in corners) // len(corners)
            center_y = sum(y for x, y in corners) // len(corners)
            
            # Strip label
            label = f"Stair {i + 1}"
            cv2.putText(image, label, (center_x - 30, center_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Instructions
        instructions = [
            "EDIT MODE - Press 'E' to toggle",
            "Drag corners to adjust masks",
            "Press 'S' to save configuration",
            "Press 'R' to reset to defaults"
        ]
        
        for i, instruction in enumerate(instructions):
            cv2.putText(image, instruction, (10, 30 + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    def handle_mouse_event(self, event: int, x: int, y: int, flags: int, param):
        """Handle mouse events for drag-and-drop corner adjustment."""
        if not self.is_editing:
            return
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # Find corner under mouse
            self.selected_corner = None
            for mask in self.masks:
                corner = mask.find_corner_at_point(x, y)
                if corner:
                    self.selected_corner = corner
                    corner.is_dragging = True
                    self.mouse_dragging = True
                    break
        
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.mouse_dragging and self.selected_corner:
                # Move selected corner
                self.selected_corner.move_to(x, y)
        
        elif event == cv2.EVENT_LBUTTONUP:
            if self.selected_corner:
                self.selected_corner.is_dragging = False
                self.selected_corner = None
            self.mouse_dragging = False
        
        self.last_mouse_pos = (x, y)
    
    def handle_keyboard_event(self, key: int) -> bool:
        """Handle keyboard events. Returns True if event was handled."""
        key_char = chr(key & 0xFF).lower()
        
        if key_char == 'e':
            # Toggle edit mode
            self.is_editing = not self.is_editing
            logger.info(f"Edit mode: {'ON' if self.is_editing else 'OFF'}")
            return True
        
        elif key_char == 's' and self.is_editing:
            # Save masks
            self.save_masks()
            return True
        
        elif key_char == 'r' and self.is_editing:
            # Reset to defaults
            self.masks = [StripMask(i, mask['corners']) for i, mask in enumerate(self.default_masks)]
            logger.info("Reset masks to defaults")
            return True
        
        return False
    
    def get_projection_transforms(self) -> List[np.ndarray]:
        """Get perspective transformation matrices for each strip."""
        transforms = []
        
        for i, mask in enumerate(self.masks):
            # Source rectangle (original strip area)
            strip_height = 1080 // 6
            y_top = i * strip_height
            y_bottom = min((i + 1) * strip_height, 1080)
            
            src_points = np.float32([
                [0, y_top],
                [1920, y_top],
                [1920, y_bottom],
                [0, y_bottom]
            ])
            
            # Destination points (mask corners)
            dst_points = np.float32(mask.get_corner_positions())
            
            # Calculate perspective transform
            transform = cv2.getPerspectiveTransform(src_points, dst_points)
            transforms.append(transform)
        
        return transforms

# Test functions for Stage 2 verification
def test_mask_manager():
    """Test mask manager functionality."""
    print("Testing MaskManager...")
    
    # Create test mask manager
    manager = MaskManager("config/test_masks.json")
    
    # Test default masks
    assert len(manager.masks) == 6, "Should have 6 masks"
    
    # Test mask access
    mask = manager.get_mask_for_strip(0)
    assert mask is not None, "Should get mask for strip 0"
    assert len(mask.corners) == 4, "Mask should have 4 corners"
    
    # Test save/load
    manager.save_masks()
    
    manager2 = MaskManager("config/test_masks.json")
    assert len(manager2.masks) == 6, "Loaded masks should match"
    
    print("✅ MaskManager tests passed")

if __name__ == "__main__":
    test_mask_manager()
