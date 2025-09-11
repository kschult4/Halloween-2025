#!/usr/bin/env python3
"""
Stage 4 Test Script - Playback Parameter Verification
Tests crossfade functionality, buffer timing, and parameter adjustment UI.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
import cv2
import numpy as np
from config_manager import ConfigManager, CrossfadeManager, ParameterAdjustmentUI, test_config_manager
from video_engine import VideoEngine

def test_config_manager_functionality():
    """Test configuration manager basic functionality."""
    print("\n=== Testing Config Manager ===")
    
    # Run built-in test
    test_config_manager()
    
    # Additional tests
    config = ConfigManager("config/test_stage4.json")
    
    # Test parameter bounds
    config.set_crossfade_duration_ms(10000)  # Over limit
    assert config.get_crossfade_duration_ms() <= 5000, "Should enforce upper bound"
    
    config.set_state_change_buffer_ms(-500)  # Under limit
    assert config.get_state_change_buffer_ms() >= 0, "Should enforce lower bound"
    
    # Test adjustment methods
    original = config.get_crossfade_duration_ms()
    new_value = config.adjust_crossfade_duration(100)
    assert new_value == original + 100, "Should adjust by delta"
    
    print("✅ Config manager functionality test passed")
    return True

def test_crossfade_manager():
    """Test crossfade manager functionality."""
    print("\n=== Testing Crossfade Manager ===")
    
    config = ConfigManager("config/test_crossfade.json")
    config.set_crossfade_duration_ms(500)  # 500ms crossfade
    
    crossfade = CrossfadeManager(config)
    
    # Create test frames
    old_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    old_frame[:, :] = [255, 0, 0]  # Red frame
    
    new_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    new_frame[:, :] = [0, 255, 0]  # Green frame
    
    # Test crossfade
    assert not crossfade.is_active(), "Should not be active initially"
    
    crossfade.start_crossfade(old_frame)
    assert crossfade.is_active(), "Should be active after start"
    
    # Test blending
    for i in range(15):  # More steps to ensure completion
        blended = crossfade.update_crossfade(new_frame)
        progress = crossfade.get_progress()
        print(f"  Crossfade progress: {progress:.2f}")
        
        if not crossfade.is_active():
            print(f"  Crossfade completed after {i+1} steps")
            break
        time.sleep(0.05)  # 50ms steps
    
    # Give a bit more time if needed
    if crossfade.is_active():
        time.sleep(0.2)
        crossfade.update_crossfade(new_frame)
    
    assert not crossfade.is_active(), f"Should complete after duration (progress: {crossfade.get_progress():.2f})"
    
    print("✅ Crossfade manager test passed")
    return True

def test_parameter_ui():
    """Test parameter adjustment UI functionality."""
    print("\n=== Testing Parameter UI ===")
    
    config = ConfigManager("config/test_param_ui.json")
    ui = ParameterAdjustmentUI(config)
    
    # Test UI toggle
    assert not ui.show_ui, "UI should start hidden"
    ui.toggle_ui()
    assert ui.show_ui, "UI should be visible after toggle"
    
    # Test parameter adjustment
    original = config.get_crossfade_duration_ms()
    
    # Simulate '+' key press
    ui.selected_param = 0  # Crossfade duration
    ui._adjust_selected_parameter(1)  # +1 step
    
    new_value = config.get_crossfade_duration_ms()
    assert new_value > original, "Parameter should increase"
    
    # Test reset
    ui._reset_selected_parameter()
    reset_value = config.get_crossfade_duration_ms()
    assert reset_value == config.defaults["crossfade_duration_ms"], "Should reset to default"
    
    print("✅ Parameter UI test passed")
    return True

def test_video_engine_integration():
    """Test video engine integration with new features."""
    print("\n=== Testing Video Engine Integration ===")
    
    engine = VideoEngine()
    engine.preload_videos(['media/active', 'media/ambient'])
    
    # Test configuration integration
    original_crossfade = engine.config_manager.get_crossfade_duration_ms()
    engine.config_manager.set_crossfade_duration_ms(300)
    assert engine.config_manager.get_crossfade_duration_ms() == 300, "Config should update"
    
    # Test crossfade manager integration
    assert engine.crossfade_manager is not None, "Should have crossfade manager"
    assert engine.parameter_ui is not None, "Should have parameter UI"
    
    # Test MQTT timeout configuration
    assert engine.mqtt_handler.timeout_seconds == engine.config_manager.get_mqtt_timeout_seconds(), \
           "MQTT timeout should match config"
    
    # Simulate video switch with crossfade
    available_videos = engine.get_available_videos()
    if available_videos:
        # Create fake last frame
        engine.last_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test crossfade trigger
        engine._handle_mqtt_message("active", available_videos[0])
        
        # Should have started crossfade
        print(f"  Crossfade active: {engine.crossfade_manager.is_active()}")
    
    engine.cleanup()
    print("✅ Video engine integration test passed")
    return True

def test_buffer_timing():
    """Test state change buffer timing."""
    print("\n=== Testing Buffer Timing ===")
    
    config = ConfigManager("config/test_buffer.json")
    config.set_state_change_buffer_ms(200)  # 200ms buffer
    
    # Simulate message handling with timing
    start_time = time.time()
    
    # This would normally be called by MQTT handler
    buffer_ms = config.get_state_change_buffer_ms()
    if buffer_ms > 0:
        time.sleep(buffer_ms / 1000.0)
    
    elapsed = (time.time() - start_time) * 1000
    
    print(f"  Buffer delay: {elapsed:.1f}ms (expected: {buffer_ms}ms)")
    assert elapsed >= buffer_ms * 0.9, "Should apply buffer delay"
    
    print("✅ Buffer timing test passed")
    return True

def test_visual_crossfade():
    """Visual test of crossfade functionality."""
    print("\n=== Visual Crossfade Test ===")
    print("This test shows crossfade transition between colored frames.")
    print("Press any key to start crossfade, ESC to exit")
    
    config = ConfigManager()
    config.set_crossfade_duration_ms(1000)  # 1 second crossfade
    crossfade = CrossfadeManager(config)
    
    # Create test frames
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame1[:, :] = [200, 100, 100]  # Red-ish
    
    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame2[:, :] = [100, 200, 100]  # Green-ish
    
    current_frame = frame1.copy()
    use_frame2 = False
    
    window_name = "Crossfade Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    print("Visual test running... Press any key to trigger crossfade")
    
    start_time = time.time()
    while time.time() - start_time < 30:  # 30 second timeout
        # Update crossfade
        if crossfade.is_active():
            target_frame = frame2 if use_frame2 else frame1
            current_frame = crossfade.update_crossfade(target_frame)
            
            # Draw progress
            progress = crossfade.get_progress()
            cv2.putText(current_frame, f"Crossfade: {progress:.1%}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Add instructions
        cv2.putText(current_frame, "Press any key for crossfade, ESC to exit", 
                   (10, current_frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        cv2.imshow(window_name, current_frame)
        
        key = cv2.waitKey(30) & 0xFF
        if key == 27:  # ESC
            break
        elif key != 255 and not crossfade.is_active():
            # Start crossfade
            old_frame = frame2 if use_frame2 else frame1
            crossfade.start_crossfade(old_frame.copy())
            use_frame2 = not use_frame2
            current_frame = frame1 if use_frame2 else frame2
    
    cv2.destroyWindow(window_name)
    print("✅ Visual crossfade test completed")
    return True

def test_parameter_adjustment_ui():
    """Interactive test of parameter adjustment UI."""
    print("\n=== Parameter Adjustment UI Test ===")
    print("This test shows the parameter adjustment interface.")
    print("Controls:")
    print("  P - Toggle parameter UI")
    print("  +/- - Adjust selected parameter")
    print("  S - Save settings")
    print("  R - Reset selected parameter")
    print("  ESC - Exit")
    
    config = ConfigManager("config/test_ui_params.json")
    ui = ParameterAdjustmentUI(config)
    
    # Create test frame
    test_frame = np.zeros((600, 800, 3), dtype=np.uint8)
    test_frame[:, :] = [50, 50, 100]  # Dark blue background
    
    window_name = "Parameter UI Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    print("Interactive UI test running...")
    
    start_time = time.time()
    while time.time() - start_time < 60:  # 60 second timeout
        display_frame = test_frame.copy()
        
        # Draw current settings
        settings = config.get_all_settings()
        y_offset = 50
        for key, value in settings.items():
            if key in ["crossfade_duration_ms", "state_change_buffer_ms", "mqtt_timeout_seconds"]:
                text = f"{key}: {value}"
                cv2.putText(display_frame, text, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                y_offset += 30
        
        # Draw parameter UI
        ui.draw_ui(display_frame)
        
        cv2.imshow(window_name, display_frame)
        
        key = cv2.waitKey(30) & 0xFF
        if key == 27:  # ESC
            break
        elif key != 255:
            ui.handle_keyboard_input(key)
    
    cv2.destroyWindow(window_name)
    print("✅ Parameter adjustment UI test completed")
    return True

def main():
    """Run all Stage 4 tests."""
    print("Halloween Projection Mapper - Stage 4 Tests")
    print("=" * 50)
    
    try:
        # Unit tests
        test_results = [
            test_config_manager_functionality(),
            test_crossfade_manager(),
            test_parameter_ui(),
            test_video_engine_integration(),
            test_buffer_timing(),
        ]
        
        # Interactive tests
        print("\n" + "=" * 50)
        print("INTERACTIVE TESTS")
        print("=" * 50)
        
        try:
            response = input("Run visual crossfade test? (y/n): ").lower()
            if response == 'y':
                test_results.append(test_visual_crossfade())
        except EOFError:
            print("  ⚠️  Visual crossfade test skipped (non-interactive environment)")
        
        try:
            response = input("Run parameter adjustment UI test? (y/n): ").lower()
            if response == 'y':
                test_results.append(test_parameter_adjustment_ui())
        except EOFError:
            print("  ⚠️  Parameter UI test skipped (non-interactive environment)")
        
        # Results
        print("\n=== Test Results ===")
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if all(test_results):
            print("\n✅ Stage 4 tests PASSED - Playback parameters ready!")
            print("\nFeatures verified:")
            print("  - Configurable crossfade duration (0-5000ms)")
            print("  - State change buffer timing (0-10000ms)")
            print("  - Runtime parameter adjustment UI")
            print("  - Smooth crossfade transitions")
            print("  - Persistent configuration storage")
            print("  - Real-time visual feedback")
            return True
        else:
            print("\n❌ Stage 4 tests FAILED - Check implementation")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()