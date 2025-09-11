# Halloween Projection Mapper - Product Requirements Document (PRD)

**Product Name:** Halloween Projection Mapper (working title)  
**Prepared For:** Claude Code Development  
**Date:** September 11, 2025

## 1. Overview / Vision

Develop a lightweight projection-mapping playback application for a Halloween display. The application will run on a Raspberry Pi 4 or newer connected to a projector and will display short videos on a segmented surface (6 horizontal bars corresponding to stairs). The app will respond to motion detection via MQTT signals sent from an ESP32, which also drives a paired LED panel. Each video has a corresponding LED animation that must stay in sync with the projection. The app allows field adjustment of projection alignment and basic playback parameters.

## 2. Target Users / Personas

Home hobbyists or small-scale decorators using projection mapping for seasonal displays.

Users who want minimal setup, instant visual feedback, and motion-triggered interactions.

Users who want to coordinate projections and LED animations seamlessly.

## 3. Problem Statement

Existing projection-mapping software is either overkill, unstable on Raspberry Pi, or not designed for small, motion-triggered interactive displays. Users need a lightweight, reliable application that:

- Plays pre-defined videos mapped to physical steps or surfaces.
- Responds instantly to motion detection.
- Plays videos synchronized with LED animations controlled by an ESP32.
- Allows field adjustment of projection alignment.

## 4. Goals

- Stable, low-latency playback on Raspberry Pi 4+.
- Enable motion-triggered, ESP32-driven interaction using MQTT.
- Provide intuitive mask/geometry adjustment in the field.
- Ensure seamless video looping and state-based playback for engaging displays.
- Support quick visual transitions (200 ms crossfade) between ambient and active states.
- Allow users to edit basic playback parameters (crossfade, buffer before state change).
- Enable Pi-friendly video encoding via helper script for easy media preparation.

## 5. Features / Functionality

### 5.1 Core Playback

- Load a library of videos stored locally on the Pi. Each video has a corresponding LED animation.
- One video at a time, split into 6 horizontal bars, projected onto stairs.
- Loop selected video continuously until a new state/media message is received via MQTT.
- Smooth 200 ms crossfade between videos or states.
- Playback ignores audio; all videos are silent.

### 5.2 Triggering / Interaction

Subscribe to MQTT topic: `halloween/playback`.

Payload format (JSON):
```json
{
  "state": "active",        // "active" or "ambient"
  "media": "active_07"      // unique ID or filename stem
}
```

**Behavior:**
- If media exists: start playback immediately (<250 ms latency).
- If media does not exist: fallback to looping an ambient video.
- If MQTT messages are missing (ESP32 offline or comms lost): loop an ambient video.
- Pi does not randomly select videos; all randomness is handled by ESP32.

### 5.3 Masking / Alignment

- Global mask applies to all videos.
- Drag-and-drop corner controls for each bar.
- Field fine-tuning saved to a JSON file, persists across restarts.

### 5.4 Video Management

All videos stored in structured folders:
```
media/
  active/
    active_01.mp4
  ambient/
    ambient_01.mp4
```

- Number of videos is flexible; Pi plays whatever is available.
- Helper script automatically encodes uploaded videos to H.264 MP4, 1080p, 30 fps, progressive, ready for Pi hardware acceleration. Original files retained.

### 5.5 System / Performance Requirements

- Target platform: Raspberry Pi 4 or newer only.
- Playback: smooth 1080p video, one video at a time across 6 bars.
- CPU/GPU usage: low; use hardware-accelerated decoding.
- Auto-start on boot; gracefully recover from failures.

### 5.6 Deployment to Raspberry Pi

- Method: Git clone the project folder.
- Install dependencies: opencv-python, ffpyplayer, numpy, python-osc, paho-mqtt.
- Verify media folder exists with properly encoded videos.
- Launch application; optional systemd service for auto-start.

### 5.7 User Interface (UI)

- Keyboard toggle (E) for edit/playback mode. No touchscreen.
- Edit mode allows:
  - Dragging corners to align masks
  - Adjusting basic playback parameters: crossfade length, buffer before state change (global settings)
  - Preview changes instantly; save to JSON for persistence.
  - Reload media library without losing mask configuration.

### 5.8 MQTT Synchronization Notes

- Pi subscribes to `halloween/playback`.
- Expects exact media instructions from ESP32.
- Response time: <250 ms to start playback.
- Ensures projection and LED animation stay in sync.

## 6. Technical Notes

- Language/framework: Python or lightweight alternative.
- Video playback: ffpyplayer for hardware-accelerated H.264.
- Masking: quadrilateral masks (4 corner points) per horizontal bar.
- MQTT client: paho-mqtt.
- Data persistence: JSON for masks and parameters.
- Preloading: video headers and first frames preloaded for near-instant playback.

## 7. User Stories

- As a user, I want ambient video to play when no motion is detected.
- As a user, I want an active video to play when motion is detected.
- As a user, I want the video to loop until the state changes again.
- As a user, I want to adjust the projection mask by dragging corners.
- As a user, I want to pre-load videos and save masks for quick setup.
- As a user, I want the projection and LEDs to stay in sync.
- As a developer, I want the Pi to play exactly the media instructed via MQTT.
- As a user, I want a simple edit UI to adjust crossfade length and buffer time.
- As a user, I want an easy way to encode uploaded videos for Pi playback.

## 8. Success Metrics / KPIs

- Smooth 1080p playback on Raspberry Pi 4.
- Sub-250 ms response to MQTT messages.
- Projection and LED playback remain synchronized.
- Field mask adjustments possible in under 5 minutes.
- No crashes during 4+ hours of continuous playback.
- Ability to swap in new videos via helper script without reconfiguring masks.

## 9. Collaboration Guidelines

- Claude Code should review all requirements for feasibility and clarity.
- Raise concerns or questions proactively.
- Reference the full PRD context before proposing solutions.
- Highlight any choices or risks that might violate requirements or compromise stability.
- Use this PRD as the authoritative reference for implementation decisions.
- Follow user stories, technical notes, and success metrics to guide coding, testing, and design.

## 10. Developer Guidelines & Expectations

Unit and integration tests for:
- Video playback engine
- Mask UI
- MQTT triggers

Stress-test continuous playback at 1080p.
Validate state transitions and fallback behavior.
Clear, readable, maintainable code; proper logging; no leftover dev artifacts.

## 11. Deliverables

**Raspberry Pi-compatible app with:**
- Video playback engine
- 6 horizontal bar masking
- Drag-and-drop corner adjustment UI
- Keyboard toggle for edit/playback mode
- Adjustable crossfade and buffer parameters (global settings)
- MQTT-triggered video switching (Pi follows ESP32 instructions)
- Config/mask persistence
- Helper script for video encoding

**Documentation:**
- Installation instructions on Pi
- Folder structure for media
- Mask adjustment and playback parameter guide

## Implementation Clarifications

Based on Q&A session:

- **Video Rendering**: Single video file split into 6 horizontal strips for stair projection
- **Masking**: 4-corner quadrilateral masks per stair for keystone correction
- **Hardware Acceleration**: Pi 4 boot config optimization (gpu_mem=128+, vc4-kms-v3d)
- **LED Sync**: Simultaneous start only, no Pi→ESP32 communication required
- **MQTT Reliability**: 60-second timeout-based fallback detection
- **Video Preloading**: Smart preloading (headers + first frames) for <250ms response
- **Settings Scope**: Global crossfade length and buffer times
- **Mask Configuration**: Global mask settings across all videos