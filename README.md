# Halloween Projection Mapper

A lightweight projection-mapping application for Halloween displays on Raspberry Pi 4+.

## 🎃 Project Status: **COMPLETE** ✅

All 6 development stages have been implemented and tested, providing a fully functional projection mapping system ready for Halloween displays.

## Quick Start

1. **Setup:**
   ```bash
   python setup.py
   ```

2. **Add Videos:**
   - Copy MP4 files to `media/active/` (motion-triggered videos)
   - Copy MP4 files to `media/ambient/` (default/fallback videos)

3. **Test Stage 1:**
   ```bash
   python tests/test_stage1.py
   ```

## Project Status

### ✅ Stage 1: Video Playback Engine (COMPLETED)
- Hardware-accelerated H.264 playback
- Video preloading for <250ms response time
- 6-strip horizontal video processing
- Continuous looping support
- Thread-safe video switching

### ✅ Stage 2: Mask UI (COMPLETED)
- Drag-and-drop corner adjustment for precise alignment
- 6 quadrilateral masks for individual stair projection
- Real-time visual overlay and editing
- Persistent mask configuration (JSON storage)
- Keyboard controls (E: edit mode, S: save, R: reset)

### ✅ Stage 3: MQTT Integration (COMPLETED)
- ESP32 communication via `halloween/playback` topic
- State-based video switching (active/ambient)
- 60-second timeout fallback to ambient
- Sub-250ms response time to MQTT messages
- Robust error handling and media resolution

### ✅ Stage 4: Playback Parameters (COMPLETED)
- Configurable crossfade duration (0-5000ms)
- State change buffer timing (0-10000ms)
- Runtime parameter adjustment UI
- Smooth alpha-blended crossfade transitions
- Persistent configuration storage

### ✅ Stage 5: Video Encoding Helper (COMPLETED)
- Pi-optimized H.264 encoding with hardware acceleration support
- Automatic video analysis and optimization detection
- Batch processing for media folders
- Progress tracking and error handling
- Command line interface with multiple modes

### ✅ Stage 6: Error Handling (COMPLETED)
- Comprehensive error classification and recovery
- Circuit breaker pattern for repeated failures
- Component-specific fallback strategies
- System health monitoring and alerting
- Automatic recovery and state management
- Long-term stability for 4+ hour operation

## Requirements

- Raspberry Pi 4+ (4GB RAM recommended)
- Python 3.7+
- OpenCV 4.5+
- Hardware-accelerated H.264 support

## Media Folder Structure

```
media/
├── active/          # Motion-triggered videos
│   ├── active_01.mp4
│   ├── active_02.mp4
│   └── ...
└── ambient/         # Default/fallback videos
    ├── ambient_01.mp4
    ├── ambient_02.mp4
    └── ...
```

## Configuration

- `config/settings.json` - Global playback parameters
- `config/masks.json` - Projection mask coordinates

### Keyboard Controls

**Main Application:**
- `E` - Toggle mask edit mode
- `P` - Toggle parameter adjustment UI
- `C` - Test crossfade transition
- `I` - Show system info in logs
- `ESC` - Exit application

**Edit Mode:**
- `S` - Save mask configuration
- `R` - Reset masks to defaults
- Drag corners to adjust mask shapes

**Parameter UI Mode:**
- `+/-` - Adjust selected parameter
- `S` - Save parameter settings
- `R` - Reset selected parameter to default

## Testing

Run stage-specific tests:
```bash
python tests/test_stage1.py    # Video engine tests
python tests/test_stage2.py    # Mask system tests
python tests/test_stage3.py    # MQTT integration tests
python tests/test_stage4.py    # Playback parameters tests
python tests/test_stage5.py    # Video encoding tests
python tests/test_stage6.py    # Error handling tests
```

### Tools

**Mask Editor:**
```bash
python tools/mask_editor.py   # Interactive mask adjustment tool
```

**MQTT Tester:**
```bash
python tools/mqtt_tester.py   # Test ESP32 communication
```

**Video Encoder:**
```bash
python tools/encode_video.py --scan       # Scan media folder
python tools/encode_video.py --batch      # Encode all videos
python tools/encode_video.py --info video.mp4  # Show video details
```

## Raspberry Pi Setup

Add to `/boot/config.txt`:
```
gpu_mem=128
dtoverlay=vc4-kms-v3d
max_framebuffers=2
```

Install system dependencies:
```bash
sudo apt update
sudo apt install python3-opencv libavcodec-dev libavformat-dev libswscale-dev ffmpeg
```

**Note**: FFmpeg is required for video encoding. The encoder will check for availability and provide installation instructions if missing.