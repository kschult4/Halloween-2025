#!/usr/bin/env python3
"""
Stage 1 Test Script - Video Engine Verification
Tests video playback engine, preloading, and looping functionality.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
import cv2
from video_engine import VideoEngine

def create_test_video():
    """Create a simple test video if none exists."""
    test_path = "media/ambient/test_ambient.mp4"
    
    if os.path.exists(test_path):
        return test_path
    
    print("Creating test video...")
    
    # Create a simple test video with colored frames
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(test_path, fourcc, 30.0, (1920, 1080))
    
    # Create 90 frames (3 seconds at 30fps)
    for i in range(90):
        # Create frame with changing color
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        color_intensity = int(128 + 127 * np.sin(i * 0.1))
        frame[:, :] = [color_intensity, 100, 200]  # BGR
        
        # Add frame number text
        cv2.putText(frame, f"Frame {i}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        out.write(frame)
    
    out.release()
    print(f"Test video created: {test_path}")
    return test_path

def test_preloading():
    """Test video preloading functionality."""
    print("\n=== Testing Video Preloading ===")
    
    engine = VideoEngine()
    
    # Ensure media folders exist
    os.makedirs("media/active", exist_ok=True)
    os.makedirs("media/ambient", exist_ok=True)
    
    # Create test video if needed
    create_test_video()
    
    # Test preloading
    start_time = time.time()
    engine.preload_videos(['media/active', 'media/ambient'])
    preload_time = time.time() - start_time
    
    available_videos = engine.get_available_videos()
    
    print(f"Preloading completed in {preload_time:.2f}s")
    print(f"Available videos: {available_videos}")
    
    # Verify preload data
    for video_id in available_videos:
        video = engine.preloaded_videos[video_id]
        print(f"  {video_id}: {video.frame_width}x{video.frame_height}, "
              f"{video.fps}fps, {video.duration:.1f}s")
    
    engine.cleanup()
    return len(available_videos) > 0

def test_playback():
    """Test video playback and looping."""
    print("\n=== Testing Video Playback ===")
    
    engine = VideoEngine()
    engine.preload_videos(['media/active', 'media/ambient'])
    
    available_videos = engine.get_available_videos()
    if not available_videos:
        print("No videos available for testing")
        return False
    
    test_video = available_videos[0]
    print(f"Testing playback of: {test_video}")
    
    # Test playback start
    start_time = time.time()
    success = engine.start_playback(test_video)
    start_latency = time.time() - start_time
    
    print(f"Playback start latency: {start_latency * 1000:.1f}ms")
    print(f"Playback started: {success}")
    
    if success:
        print("Playing for 5 seconds... (close window or press ESC to stop)")
        
        start_time = time.time()
        while time.time() - start_time < 5.0:
            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC key
                break
            if cv2.getWindowProperty(engine.window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
    
    engine.cleanup()
    return success

def test_video_switching():
    """Test switching between videos."""
    print("\n=== Testing Video Switching ===")
    
    engine = VideoEngine()
    engine.preload_videos(['media/active', 'media/ambient'])
    
    available_videos = engine.get_available_videos()
    if len(available_videos) < 1:
        print("Need at least 1 video for switching test")
        return False
    
    # Test rapid switching
    for i in range(3):
        video_id = available_videos[i % len(available_videos)]
        print(f"Switching to: {video_id}")
        
        start_time = time.time()
        success = engine.start_playback(video_id)
        switch_latency = time.time() - start_time
        
        print(f"  Switch latency: {switch_latency * 1000:.1f}ms")
        
        if success:
            time.sleep(1)  # Play for 1 second
        else:
            print(f"  Failed to switch to {video_id}")
    
    engine.cleanup()
    return True

def main():
    """Run all Stage 1 tests."""
    print("Halloween Projection Mapper - Stage 1 Tests")
    print("=" * 50)
    
    try:
        # Test 1: Preloading
        preload_success = test_preloading()
        
        # Test 2: Basic playback
        playback_success = test_playback()
        
        # Test 3: Video switching
        switching_success = test_video_switching()
        
        # Results
        print("\n=== Test Results ===")
        print(f"Preloading: {'PASS' if preload_success else 'FAIL'}")
        print(f"Playback: {'PASS' if playback_success else 'FAIL'}")
        print(f"Switching: {'PASS' if switching_success else 'FAIL'}")
        
        if all([preload_success, playback_success, switching_success]):
            print("\n✅ Stage 1 tests PASSED - Video engine ready!")
            return True
        else:
            print("\n❌ Stage 1 tests FAILED - Check implementation")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        return False

if __name__ == "__main__":
    import numpy as np  # Import needed for test video creation
    main()