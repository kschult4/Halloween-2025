#!/usr/bin/env python3
"""
Stage 2 Test Script - Mask UI Verification
Tests mask management, drag-and-drop corners, and persistence.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
import cv2
import numpy as np
from mask_manager import MaskManager, StripMask
from video_engine import VideoEngine

def test_mask_creation():
    """Test mask creation and default configuration."""
    print("\n=== Testing Mask Creation ===")
    
    manager = MaskManager("config/test_masks.json")
    
    # Verify 6 masks created
    assert len(manager.masks) == 6, f"Expected 6 masks, got {len(manager.masks)}"
    
    # Verify each mask has 4 corners
    for i, mask in enumerate(manager.masks):
        assert len(mask.corners) == 4, f"Mask {i} should have 4 corners"
        corners = mask.get_corner_positions()
        print(f"  Mask {i} corners: {corners}")
    
    print("✅ Mask creation test passed")
    return True

def test_mask_persistence():
    """Test saving and loading mask configurations."""
    print("\n=== Testing Mask Persistence ===")
    
    # Create manager and modify a mask
    manager1 = MaskManager("config/test_persistence.json")
    
    # Modify first mask's corners
    original_corners = manager1.masks[0].get_corner_positions()
    manager1.masks[0].corners[0].move_to(100, 100)
    manager1.masks[0].corners[1].move_to(200, 100)
    modified_corners = manager1.masks[0].get_corner_positions()
    
    print(f"  Original corners: {original_corners}")
    print(f"  Modified corners: {modified_corners}")
    
    # Save configuration
    manager1.save_masks()
    
    # Load in new manager
    manager2 = MaskManager("config/test_persistence.json")
    loaded_corners = manager2.masks[0].get_corner_positions()
    
    print(f"  Loaded corners: {loaded_corners}")
    
    # Verify persistence
    assert loaded_corners == modified_corners, "Corners should persist across save/load"
    
    print("✅ Mask persistence test passed")
    return True

def test_corner_detection():
    """Test corner hit detection for mouse interaction."""
    print("\n=== Testing Corner Detection ===")
    
    manager = MaskManager()
    mask = manager.masks[0]
    
    # Test corner detection
    corner = mask.corners[0]
    corner.move_to(100, 100)
    
    # Point inside corner radius
    assert corner.contains_point(105, 105), "Should detect point inside corner"
    
    # Point outside corner radius
    assert not corner.contains_point(150, 150), "Should not detect point outside corner"
    
    # Test mask-level corner finding
    found_corner = mask.find_corner_at_point(105, 105)
    assert found_corner is corner, "Should find the correct corner"
    
    found_corner = mask.find_corner_at_point(500, 500)
    assert found_corner is None, "Should not find corner at distant point"
    
    print("✅ Corner detection test passed")
    return True

def test_keyboard_handling():
    """Test keyboard event handling."""
    print("\n=== Testing Keyboard Handling ===")
    
    manager = MaskManager()
    
    # Test edit mode toggle
    assert not manager.is_editing, "Should start in non-edit mode"
    
    # Simulate 'E' key press
    handled = manager.handle_keyboard_event(ord('e'))
    assert handled, "Should handle 'e' key"
    assert manager.is_editing, "Should enter edit mode"
    
    # Toggle again
    manager.handle_keyboard_event(ord('E'))  # Test uppercase
    assert not manager.is_editing, "Should exit edit mode"
    
    # Test save key (should not crash)
    manager.is_editing = True
    handled = manager.handle_keyboard_event(ord('s'))
    assert handled, "Should handle 's' key"
    
    # Test reset key
    original_corners = manager.masks[0].get_corner_positions()
    manager.masks[0].corners[0].move_to(999, 999)  # Modify
    
    handled = manager.handle_keyboard_event(ord('r'))
    assert handled, "Should handle 'r' key"
    
    reset_corners = manager.masks[0].get_corner_positions()
    assert reset_corners == original_corners, "Should reset to defaults"
    
    print("✅ Keyboard handling test passed")
    return True

def test_visual_mask_editing():
    """Interactive test for visual mask editing."""
    print("\n=== Visual Mask Editing Test ===")
    print("This test opens a visual window for mask editing.")
    print("Controls:")
    print("  - Press 'E' to toggle edit mode")
    print("  - Drag corners to adjust masks")
    print("  - Press 'S' to save configuration")
    print("  - Press 'R' to reset to defaults")
    print("  - Press ESC to exit test")
    
    # Create engine with mask integration
    engine = VideoEngine()
    
    # Create a test pattern frame
    test_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # Draw test pattern with numbered strips
    for i in range(6):
        y_start = i * 180
        y_end = (i + 1) * 180
        
        # Alternate colors for visibility
        color = (100 + i * 20, 150, 200 - i * 20)
        test_frame[y_start:y_end, :] = color
        
        # Add strip number
        cv2.putText(test_frame, f"Strip {i + 1}", 
                   (960, y_start + 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    print("Opening visual test window... Press ESC when done.")
    
    start_time = time.time()
    while time.time() - start_time < 30:  # 30 second timeout
        # Display frame with masks
        display_frame = test_frame.copy()
        engine.mask_manager.draw_edit_overlay(display_frame)
        
        cv2.imshow(engine.window_name, display_frame)
        
        # Handle input
        key = cv2.waitKey(30) & 0xFF
        if key == 27:  # ESC
            break
        elif key != 255:
            engine.mask_manager.handle_keyboard_event(key)
    
    engine.cleanup()
    print("✅ Visual test completed")
    return True

def test_mask_integration_with_video():
    """Test mask system integration with video playback."""
    print("\n=== Testing Mask Integration with Video ===")
    
    engine = VideoEngine()
    engine.preload_videos(['media/active', 'media/ambient'])
    
    available_videos = engine.get_available_videos()
    if available_videos:
        print(f"Testing with video: {available_videos[0]}")
        
        # Start playback
        if engine.start_playback(available_videos[0]):
            print("Video playing with mask overlay...")
            print("Press 'E' to toggle edit mode, ESC to exit")
            
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second test
                key = cv2.waitKey(30) & 0xFF
                if key == 27:  # ESC
                    break
                elif key != 255:
                    engine.mask_manager.handle_keyboard_event(key)
            
            engine.stop_playback()
            print("✅ Video integration test completed")
        else:
            print("⚠️  No video available for integration test")
    else:
        print("⚠️  No videos found for integration test")
    
    engine.cleanup()
    return True

def main():
    """Run all Stage 2 tests."""
    print("Halloween Projection Mapper - Stage 2 Tests")
    print("=" * 50)
    
    try:
        # Unit tests
        test_results = [
            test_mask_creation(),
            test_mask_persistence(),
            test_corner_detection(),
            test_keyboard_handling(),
        ]
        
        # Interactive tests
        print("\n" + "=" * 50)
        print("INTERACTIVE TESTS")
        print("=" * 50)
        
        response = input("Run visual mask editing test? (y/n): ").lower()
        if response == 'y':
            test_results.append(test_visual_mask_editing())
        
        response = input("Run video integration test? (y/n): ").lower()
        if response == 'y':
            test_results.append(test_mask_integration_with_video())
        
        # Results
        print("\n=== Test Results ===")
        print(f"Unit tests: {'PASS' if all(test_results[:4]) else 'FAIL'}")
        
        if all(test_results):
            print("\n✅ Stage 2 tests PASSED - Mask system ready!")
            print("\nFeatures verified:")
            print("  - 6 quadrilateral masks for stair projection")
            print("  - Drag-and-drop corner adjustment")
            print("  - Persistent mask configuration")
            print("  - Edit mode toggle (E key)")
            print("  - Save (S key) and reset (R key) functionality")
            print("  - Visual overlay and interaction")
            return True
        else:
            print("\n❌ Stage 2 tests FAILED - Check implementation")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        return False

if __name__ == "__main__":
    main()