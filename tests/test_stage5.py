#!/usr/bin/env python3
"""
Stage 5 Test Script - Video Encoding Helper Verification
Tests video encoding functionality and Pi optimization.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile
import subprocess
from pathlib import Path
import cv2
import numpy as np
from encode_video import VideoEncoder, VideoBatchProcessor

def create_test_video(output_path: str, duration_seconds: int = 3, 
                     width: int = 640, height: int = 480, fps: int = 25) -> bool:
    """Create a test video file for encoding tests."""
    try:
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print(f"❌ Could not create test video: {output_path}")
            return False
        
        # Generate frames
        total_frames = duration_seconds * fps
        for i in range(total_frames):
            # Create frame with changing pattern
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Rotating color pattern
            hue = int((i / total_frames) * 180)
            color_hsv = np.uint8([[[hue, 255, 200]]])
            color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
            
            frame[:, :] = color_bgr
            
            # Add frame number
            cv2.putText(frame, f"Frame {i}", (50, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            out.write(frame)
        
        out.release()
        
        # Verify file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ Created test video: {os.path.basename(output_path)} ({width}x{height}, {fps}fps)")
            return True
        else:
            print(f"❌ Test video creation failed: {output_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating test video: {e}")
        return False

def test_ffmpeg_availability():
    """Test if FFmpeg is available for encoding."""
    print("\n=== Testing FFmpeg Availability ===")
    
    encoder = VideoEncoder()
    
    if encoder.ffmpeg_available:
        print("✅ FFmpeg is available")
        
        # Test version info
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            version_line = result.stdout.split('\n')[0]
            print(f"   Version: {version_line}")
        except:
            print("   Could not get version info")
        
        return True
    else:
        print("❌ FFmpeg not available")
        print("   Install with: sudo apt install ffmpeg")
        return False

def test_video_info_extraction():
    """Test video information extraction."""
    print("\n=== Testing Video Info Extraction ===")
    
    encoder = VideoEncoder()
    
    if not encoder.ffmpeg_available:
        print("⚠️  Skipping (FFmpeg not available)")
        return True
    
    # Create test video
    with tempfile.TemporaryDirectory() as temp_dir:
        test_video = os.path.join(temp_dir, "test_info.mp4")
        
        if not create_test_video(test_video, duration_seconds=2, width=800, height=600, fps=25):
            print("❌ Could not create test video")
            return False
        
        # Extract info
        info = encoder.get_video_info(test_video)
        
        if not info:
            print("❌ Could not extract video info")
            return False
        
        print(f"   Duration: {info['duration']:.1f}s")
        print(f"   Resolution: {info['width']}x{info['height']}")
        print(f"   FPS: {info['fps']:.1f}")
        print(f"   Codec: {info['codec']}")
        print(f"   Format: {info['format']}")
        
        # Verify extracted info matches expectations
        assert abs(info['duration'] - 2.0) < 0.5, f"Duration should be ~2s, got {info['duration']}s"
        assert info['width'] == 800, f"Width should be 800, got {info['width']}"
        assert info['height'] == 600, f"Height should be 600, got {info['height']}"
        assert abs(info['fps'] - 25.0) < 2.0, f"FPS should be ~25, got {info['fps']}"
        
        print("✅ Video info extraction test passed")
        return True

def test_encoding_needs_detection():
    """Test detection of videos that need encoding."""
    print("\n=== Testing Encoding Needs Detection ===")
    
    encoder = VideoEncoder()
    
    if not encoder.ffmpeg_available:
        print("⚠️  Skipping (FFmpeg not available)")
        return True
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: Video that needs encoding (wrong resolution)
        test_video1 = os.path.join(temp_dir, "needs_encoding.mp4")
        create_test_video(test_video1, width=640, height=480)  # Not 1920x1080
        
        needs_encoding, reason = encoder.needs_encoding(test_video1)
        print(f"   640x480 video: {needs_encoding} ({reason})")
        assert needs_encoding, "Should need encoding for wrong resolution"
        
        # Test 2: Create a properly formatted video (if possible)
        test_video2 = os.path.join(temp_dir, "proper_format.mp4")
        create_test_video(test_video2, width=1920, height=1080, fps=30)
        
        needs_encoding2, reason2 = encoder.needs_encoding(test_video2)
        print(f"   1920x1080 video: {needs_encoding2} ({reason2})")
        
        print("✅ Encoding needs detection test passed")
        return True

def test_video_encoding():
    """Test actual video encoding functionality."""
    print("\n=== Testing Video Encoding ===")
    
    encoder = VideoEncoder()
    
    if not encoder.ffmpeg_available:
        print("⚠️  Skipping (FFmpeg not available)")
        return True
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create input video that needs encoding
        input_video = os.path.join(temp_dir, "input.mp4")
        output_video = os.path.join(temp_dir, "output_encoded.mp4")
        
        if not create_test_video(input_video, duration_seconds=2, width=640, height=480, fps=25):
            print("❌ Could not create test input video")
            return False
        
        print(f"   Input: {os.path.basename(input_video)}")
        print(f"   Output: {os.path.basename(output_video)}")
        
        # Track progress
        progress_values = []
        def progress_callback(progress):
            progress_values.append(progress)
            print(f"\r   Encoding progress: {progress:.1f}%", end='', flush=True)
        
        # Encode video
        success = encoder.encode_video(input_video, output_video, progress_callback)
        print()  # New line after progress
        
        if not success:
            print("❌ Encoding failed")
            return False
        
        # Verify output exists and has content
        if not os.path.exists(output_video):
            print("❌ Output video not created")
            return False
        
        if os.path.getsize(output_video) == 0:
            print("❌ Output video is empty")
            return False
        
        # Verify output specifications
        output_info = encoder.get_video_info(output_video)
        if output_info:
            print(f"   Output specs: {output_info['width']}x{output_info['height']}, "
                  f"{output_info['fps']:.1f}fps, {output_info['codec']}")
            
            # Check if Pi-optimized
            needs_encoding, reason = encoder.needs_encoding(output_video)
            if needs_encoding:
                print(f"   ⚠️  Still needs encoding: {reason}")
            else:
                print(f"   ✅ Pi-optimized: {reason}")
        
        # Check progress was reported
        assert len(progress_values) > 0, "Progress should have been reported"
        assert max(progress_values) > 0, "Progress should have increased"
        
        print("✅ Video encoding test passed")
        return True

def test_batch_processor():
    """Test batch processing functionality."""
    print("\n=== Testing Batch Processor ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock media directory structure
        media_dir = Path(temp_dir) / "media"
        active_dir = media_dir / "active"
        ambient_dir = media_dir / "ambient"
        
        active_dir.mkdir(parents=True)
        ambient_dir.mkdir(parents=True)
        
        # Create test videos
        test_videos = [
            active_dir / "active_01.mp4",
            ambient_dir / "ambient_01.mp4",
            active_dir / "active_02.avi",  # Different format
        ]
        
        for video_path in test_videos:
            create_test_video(str(video_path), duration_seconds=1, width=320, height=240)
        
        # Create batch processor
        processor = VideoBatchProcessor(str(media_dir))
        
        # Test video scanning
        found_videos = processor.scan_for_videos()
        print(f"   Found {len(found_videos)} videos")
        
        assert len(found_videos) == 3, f"Should find 3 videos, found {len(found_videos)}"
        
        # Test encoding check
        encoder = VideoEncoder()
        if encoder.ffmpeg_available:
            print("   Testing encoding needs:")
            for video in found_videos:
                needs_encoding, reason = encoder.needs_encoding(str(video))
                print(f"     {video.name}: {needs_encoding} ({reason})")
        
        print("✅ Batch processor test passed")
        return True

def test_command_line_interface():
    """Test command line interface functionality."""
    print("\n=== Testing Command Line Interface ===")
    
    try:
        # Test help
        result = subprocess.run([
            sys.executable, 'tools/encode_video.py', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, "Help command should succeed"
        assert "Halloween Projection Mapper" in result.stdout, "Should show app name"
        assert "--scan" in result.stdout, "Should show scan option"
        
        print("   ✅ Help command works")
        
        # Test scan with empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            media_dir = Path(temp_dir) / "media"
            media_dir.mkdir()
            
            result = subprocess.run([
                sys.executable, 'tools/encode_video.py', 
                '--scan', '--media-dir', str(media_dir)
            ], capture_output=True, text=True, timeout=30)
            
            # Should succeed even with no videos
            print(f"   Scan result: {result.stdout.strip()}")
        
        print("✅ Command line interface test passed")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Command line test timeout")
        return False
    except Exception as e:
        print(f"❌ Command line test error: {e}")
        return False

def test_pi_optimization_specs():
    """Test that encoding produces Pi-optimized specifications."""
    print("\n=== Testing Pi Optimization Specs ===")
    
    encoder = VideoEncoder()
    
    # Verify target specifications
    specs = encoder.target_specs
    
    print(f"   Target codec: {specs['codec']}")
    print(f"   Target resolution: {specs['resolution']}")
    print(f"   Target FPS: {specs['fps']}")
    print(f"   Target profile: {specs['profile']}")
    print(f"   Audio: {specs['audio']}")
    
    # Verify Pi-optimized settings
    assert specs['codec'] == 'libx264', "Should use H.264 codec"
    assert specs['resolution'] == '1920x1080', "Should target 1080p"
    assert specs['fps'] == 30, "Should target 30fps"
    assert specs['audio'] == False, "Should disable audio"
    assert specs['format'] == 'mp4', "Should use MP4 format"
    
    # Test FFmpeg command building
    if encoder.ffmpeg_available:
        cmd = encoder._build_ffmpeg_command('input.mp4', 'output.mp4')
        
        # Verify key parameters are present
        assert 'libx264' in cmd, "Should specify H.264 codec"
        assert '1920x1080' in cmd, "Should specify resolution"
        assert '30' in cmd, "Should specify FPS"
        assert '-an' in cmd, "Should disable audio"
        assert 'yuv420p' in cmd, "Should use Pi-compatible pixel format"
        
        print(f"   ✅ FFmpeg command: {' '.join(cmd[:10])}...")
    
    print("✅ Pi optimization specs test passed")
    return True

def main():
    """Run all Stage 5 tests."""
    print("Halloween Projection Mapper - Stage 5 Tests")
    print("=" * 50)
    
    try:
        # Core functionality tests
        test_results = [
            test_ffmpeg_availability(),
            test_pi_optimization_specs(),
            test_video_info_extraction(),
            test_encoding_needs_detection(),
            test_batch_processor(),
            test_command_line_interface(),
        ]
        
        # Optional encoding test (requires FFmpeg)
        encoder = VideoEncoder()
        if encoder.ffmpeg_available:
            print("\nFFmpeg is available - running encoding test...")
            test_results.append(test_video_encoding())
        else:
            print("\n⚠️  FFmpeg not available - skipping encoding test")
            print("Install FFmpeg to test actual encoding functionality")
        
        # Results
        print("\n=== Test Results ===")
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if all(test_results):
            print("\n✅ Stage 5 tests PASSED - Video encoding helper ready!")
            print("\nFeatures verified:")
            print("  - FFmpeg integration and availability checking")
            print("  - Video information extraction (resolution, fps, codec)")
            print("  - Pi optimization detection (needs encoding analysis)")
            print("  - H.264 encoding with Pi-optimized settings")
            print("  - Batch processing for media folders")
            print("  - Command line interface with multiple modes")
            print("  - Progress tracking and error handling")
            return True
        else:
            print("\n❌ Stage 5 tests FAILED - Check implementation")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()