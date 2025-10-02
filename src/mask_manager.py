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
    
    def draw_mask(self, image: np.ndarray, alpha: float = 0.3, *, show_corners: bool = True):
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
        if show_corners:
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
        self.edit_mode = 'corners'  # 'corners' or 'width'
        
        # Mouse state
        self.mouse_dragging = False
        self.last_mouse_pos = (0, 0)
        self.active_width_handle: Optional[str] = None  # 'left', 'right'
        self.last_overlay_height = 1080
        
        # Default mask configuration for 1920x1080 divided into 6 strips
        self.default_masks = self._create_default_masks()
        
        # Load existing masks or create defaults
        self.load_masks()

        # Width mode configuration
        self.width_mode_center = None
        self.width_mode_half_width = None
        self.width_mode_min_width = 200  # pixels
        self.width_mode_handle_radius = 25
        self.canvas_width = self._compute_canvas_width()
    
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

        self.last_overlay_height = image.shape[0]

        # Draw all masks
        for mask in self.masks:
            mask.draw_mask(image, alpha=0.2, show_corners=self.edit_mode == 'corners')

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
            "Press 'W' to switch corner/width mode",
            "Press 'S' to save configuration",
            "Press 'R' to reset to defaults"
        ]
        
        mode_line = "Mode: Four Corners"
        if self.edit_mode == 'width':
            mode_line = "Mode: Width Crop (drag handles to adjust)"
        else:
            instructions.insert(1, "Drag corners to adjust masks")
        instructions.insert(1, mode_line)

        for i, instruction in enumerate(instructions):
            cv2.putText(image, instruction, (10, 30 + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        if self.edit_mode == 'width':
            self._draw_width_mode_controls(image)

    def handle_mouse_event(self, event: int, x: int, y: int, flags: int, param):
        """Handle mouse events for drag-and-drop corner adjustment."""
        if not self.is_editing:
            return

        if self.edit_mode == 'corners':
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
        else:
            if event == cv2.EVENT_LBUTTONDOWN:
                handle = self._find_width_handle_at_point(x, y)
                if handle:
                    self.active_width_handle = handle
                    self.mouse_dragging = True
            elif event == cv2.EVENT_MOUSEMOVE:
                if self.mouse_dragging and self.active_width_handle:
                    self._update_width_crop_from_drag(x)
            elif event == cv2.EVENT_LBUTTONUP:
                self.active_width_handle = None
                self.mouse_dragging = False

        self.last_mouse_pos = (x, y)

    def handle_keyboard_event(self, key: int) -> bool:
        """Handle keyboard events. Returns True if event was handled."""
        key_char = chr(key & 0xFF).lower()
        
        if key_char == 'e':
            # Toggle edit mode
            self.is_editing = not self.is_editing
            if not self.is_editing:
                self.active_width_handle = None
                self.selected_corner = None
            logger.info(f"Edit mode: {'ON' if self.is_editing else 'OFF'}")
            return True

        elif key_char == 'w' and self.is_editing:
            self._toggle_edit_mode()
            return True

        elif key_char == 's' and self.is_editing:
            # Save masks
            self.save_masks()
            return True

        elif key_char == 'r' and self.is_editing:
            # Reset to defaults
            self.masks = [StripMask(i, mask['corners']) for i, mask in enumerate(self.default_masks)]
            self.canvas_width = self._compute_canvas_width()
            if self.edit_mode == 'width':
                self._initialize_width_mode()
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

    def _compute_canvas_width(self) -> int:
        """Compute the maximum X extent across all masks or defaults."""
        try:
            mask_x = [corner[0]
                      for mask in (self.masks or [])
                      for corner in mask.get_corner_positions()]
            default_x = [corner[0]
                         for mask in self.default_masks
                         for corner in mask['corners']]
            candidates = mask_x + default_x
            width = max(candidates) if candidates else 1920
            return max(int(width), 1)
        except Exception:
            return 1920

    def _toggle_edit_mode(self):
        """Switch between corner and width editing modes."""
        if self.edit_mode == 'corners':
            self._initialize_width_mode()
            self.edit_mode = 'width'
            self.selected_corner = None
            logger.info("Mask edit mode: WIDTH")
        else:
            self.edit_mode = 'corners'
            self.active_width_handle = None
            self.selected_corner = None
            logger.info("Mask edit mode: CORNERS")

    def _initialize_width_mode(self):
        """Prepare width mode parameters based on current mask geometry."""
        self.canvas_width = self._compute_canvas_width()
        center, half_width = self._compute_width_params_from_masks()
        self.width_mode_center = center
        self.width_mode_half_width = half_width
        self._apply_width_crop_to_masks()

    def _compute_width_params_from_masks(self) -> Tuple[float, float]:
        """Determine center and half-width from current masks."""
        if not self.masks:
            default_center = self._compute_canvas_width() / 2.0
            default_half = default_center
            return default_center, default_half

        first_corners = self.masks[0].get_corner_positions()
        left_avg = (first_corners[0][0] + first_corners[3][0]) / 2.0
        right_avg = (first_corners[1][0] + first_corners[2][0]) / 2.0

        center = (left_avg + right_avg) / 2.0
        half_width = max((right_avg - left_avg) / 2.0, 1.0)

        max_half = min(center, self.canvas_width - center)
        min_half = min(self.width_mode_min_width / 2.0, max_half)
        if max_half <= 0:
            return center, 1.0
        half_width = max(min(half_width, max_half), min_half)

        return center, half_width

    def _apply_width_crop_to_masks(self):
        """Apply the current width crop symmetrically to all masks."""
        if self.width_mode_center is None or self.width_mode_half_width is None:
            return

        max_half = min(self.width_mode_center, self.canvas_width - self.width_mode_center)
        if max_half <= 0:
            return
        min_half = min(self.width_mode_min_width / 2.0, max_half)
        half_width = max(min(self.width_mode_half_width, max_half), min_half)
        self.width_mode_half_width = half_width

        left_x = int(round(self.width_mode_center - half_width))
        right_x = int(round(self.width_mode_center + half_width))

        left_x = max(0, left_x)
        right_x = min(self.canvas_width, right_x)

        if right_x <= left_x:
            right_x = min(self.canvas_width, left_x + 1)
            left_x = max(0, right_x - 1)

        # Recompute stored center/half-width based on actual values after clamping
        self.width_mode_center = (left_x + right_x) / 2.0
        self.width_mode_half_width = (right_x - left_x) / 2.0

        for mask in self.masks:
            if len(mask.corners) != 4:
                continue
            mask.corners[0].move_to(left_x, mask.corners[0].y)
            mask.corners[3].move_to(left_x, mask.corners[3].y)
            mask.corners[1].move_to(right_x, mask.corners[1].y)
            mask.corners[2].move_to(right_x, mask.corners[2].y)

    def _get_width_handle_positions(self, image_height: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Return the current screen positions of the width handles."""
        if self.width_mode_center is None or self.width_mode_half_width is None:
            center = self._compute_canvas_width() / 2.0
            half_width = center
        else:
            center = self.width_mode_center
            half_width = self.width_mode_half_width

        mid_y = image_height // 2
        left_x = int(round(center - half_width))
        right_x = int(round(center + half_width))
        return (left_x, mid_y), (right_x, mid_y)

    def _draw_width_mode_controls(self, image: np.ndarray):
        """Render width crop handles and helper visuals."""
        h, w = image.shape[:2]
        left_pos, right_pos = self._get_width_handle_positions(h)

        # Vertical markers
        cv2.line(image, (left_pos[0], 0), (left_pos[0], h), (255, 255, 255), 1)
        cv2.line(image, (right_pos[0], 0), (right_pos[0], h), (255, 255, 255), 1)

        # Handle circles
        for pos in (left_pos, right_pos):
            cv2.circle(image, pos, self.width_mode_handle_radius, (255, 255, 255), -1)
            cv2.circle(image, pos, self.width_mode_handle_radius, (0, 0, 0), 2)

        width_px = int(round(self.width_mode_half_width * 2)) if self.width_mode_half_width else 0
        label = f"Width: {width_px}px"
        cv2.putText(image, label, (left_pos[0] + 10, max(40, left_pos[1] - 40)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def _find_width_handle_at_point(self, x: int, y: int) -> Optional[str]:
        """Determine if a width handle was clicked."""
        if self.width_mode_center is None or self.width_mode_half_width is None:
            self._initialize_width_mode()

        left_pos, right_pos = self._get_width_handle_positions(self.last_overlay_height)
        # Use actual mouse coordinate for y; handles drawn at mid-screen so the
        # approximation is acceptable for hit-testing.
        if self._point_within_radius(x, y, left_pos):
            return 'left'
        if self._point_within_radius(x, y, right_pos):
            return 'right'
        return None

    def _point_within_radius(self, x: int, y: int, center: Tuple[int, int]) -> bool:
        dx = x - center[0]
        dy = y - center[1]
        return (dx * dx + dy * dy) <= (self.width_mode_handle_radius ** 2)

    def _update_width_crop_from_drag(self, x: int):
        """Update width crop while dragging one of the handles."""
        if self.width_mode_center is None or self.active_width_handle is None:
            return

        x = max(0, min(x, self.canvas_width))
        if self.active_width_handle == 'left':
            new_half = self.width_mode_center - x
        else:
            new_half = x - self.width_mode_center

        max_half = min(self.width_mode_center, self.canvas_width - self.width_mode_center)
        if max_half <= 0:
            return
        min_half = min(self.width_mode_min_width / 2.0, max_half)
        new_half = max(min(new_half, max_half), min_half)

        self.width_mode_half_width = new_half
        self._apply_width_crop_to_masks()

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
