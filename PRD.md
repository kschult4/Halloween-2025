# Halloween Projection Mapper – Master Product Requirements Document (PRD)

Product Name: Halloween Projection Mapper (working title)
Prepared For: Claude Code Development
Date: September 11, 2025

1. Overview / Vision

Develop a lightweight projection-mapping playback application for a Halloween display. The system consists of:

- A Raspberry Pi 4 or newer running a projection mapping app for 6 horizontal bars (stairs).
- An ESP32 controlling a 3×3 grid of 16×16 LED panels.

The ESP32 detects motion via a PIR sensor, selects animations, and publishes its state via MQTT. The Pi receives the MQTT instructions and plays corresponding videos, ensuring the projection and LEDs remain synchronized. The Pi app allows field adjustment of projection alignment and basic playback parameters.

2. Target Users / Personas

- Home hobbyists or small-scale decorators using projection + LED displays.
- Users wanting minimal setup and instant visual feedback.
- Users wanting seamless coordination of projection and LED animations.

3. Problem Statement

Existing projection-mapping software is either overkill, unstable on Raspberry Pi, or not designed for small, motion-triggered interactive displays. Users need a lightweight, reliable system that:

- Plays pre-defined videos mapped to physical steps or surfaces.
- Responds instantly to motion detection.
- Plays videos synchronized with LED animations controlled by an ESP32.
- Allows field adjustment of projection alignment.

4. Goals

- Stable, low-latency playback on Raspberry Pi 4+.
- Motion-triggered, ESP32-driven interaction using MQTT.
- Intuitive mask/geometry adjustment in the field.
- Seamless video looping and state-based playback for engaging displays.
- Quick visual transitions (200 ms crossfade) between ambient and active states.
- Adjustable basic playback parameters (crossfade length, buffer before state change).
- Pi-friendly video encoding via helper script.
- ESP32 fully automated; LEDs and Pi synchronized.

5. Features / Functionality

5.1 Core Playback (Pi)

- Load a library of videos stored locally on the Pi; each video has a corresponding LED animation.
- One video at a time, split into 6 horizontal bars for stair projection.
- Loop selected video continuously until a new MQTT message is received.
- Smooth 200 ms crossfade between videos or states.
- Playback ignores audio.

5.2 Triggering / Interaction (Pi)

- Subscribes to MQTT topic: halloween/playback.

Payload format:

{
  "state": "active",      // "active" or "ambient"
  "media": "active_07"    // unique ID or filename stem
}

Behavior:

- If media exists: start playback immediately (<250 ms latency).
- If media does not exist: fallback to looping an ambient video.
- If MQTT messages are missing (ESP32 offline): loop an ambient video.
- Pi does not randomly select videos; all selection is done by ESP32.

5.3 Masking / Alignment

- Global mask applies to all videos.
- Drag-and-drop corner controls per bar for field alignment.
- Saved to JSON; persists across restarts.

5.4 Video Management

Folder structure:

media/
  active/
    active_01.mp4
  ambient/
    ambient_01.mp4

Pi plays whatever videos are available.

Helper script auto-encodes uploaded videos to H.264 MP4, 1080p, 30 fps, progressive.

5.5 System / Performance

- Smooth 1080p playback on Pi 4+.
- One video at a time across 6 bars.
- Low CPU/GPU usage; hardware-accelerated decoding.
- Auto-start on boot; recover gracefully from failures.

5.6 Deployment

- Git clone project folder.
- Install dependencies: opencv-python, ffpyplayer, numpy, python-osc, paho-mqtt.
- Verify media folder exists; launch app; optional systemd auto-start.

5.7 User Interface

- Keyboard toggle (E) for edit/playback mode; no touchscreen.

Edit mode:

- Drag corners to align masks.
- Adjust basic playback parameters (crossfade length, buffer time).
- Preview instantly; save to JSON.
- Reload media library without losing masks.

5.8 MQTT Synchronization

- Pi subscribes to halloween/playback.
- Plays exactly the media instructed by ESP32.
- Ensures LEDs and projection remain synchronized.
- Start playback <250 ms after receiving message.
- ESP32 adds 250 ms buffer to synchronize with Pi’s 200 ms crossfade.

6. ESP32 / LED System Requirements

6.1 Hardware & Peripherals

- ESP32 microcontroller.
- Single PIR presence sensor.
- 3×3 LED grid (16×16 panels), treated as one contiguous 48×48 surface.

6.2 Animation Library

- Preloaded in firmware; fixed set of animations.

Categories:

- Ambient (~3)
- Active (~12)

- Fixed frame rate.
- Loop indefinitely until state changes.

6.3 Motion Detection & State

- Single PIR sensor triggers state changes.
- Ignore rapid/repeated motion events.
- Fully automatic; no buttons or manual overrides.
- All motion and state ephemeral; nothing stored.
- On power cycle: restart; random ambient animation chosen; normal operation resumes.
- Fail silently on sensor or animation errors.

6.4 MQTT Communication

- Publish topic: halloween/playback.

Payload:

{
  "state": "active",
  "animation": "active_04"
}

- Single publish per state change.
- Optional heartbeat messages every 5–10 s for monitoring: {"status":"online","timestamp":<unix_epoch>}.
- Open local Wi-Fi; no encryption/authentication.
- Automatic Wi-Fi & MQTT reconnection; retry every 1–2 s.

6.5 Synchronization

- ESP32 adds 250 ms buffer to align LED animation with Pi video crossfade.
- If Pi connection lost, ESP32 continues its own animations.
- Animation sequence: random initial selection, then sequential cycling on subsequent state changes.

7. User Stories

- Ambient video plays when no motion detected.
- Active video plays when motion detected.
- Video/LED loops until state changes.
- Projection mask adjustable via corner dragging.
- Projection and LEDs stay synchronized.
- ESP32 handles animation selection and Pi follows.
- Edit UI allows crossfade/buffer adjustments.
- Easy video encoding for Pi playback.

8. Success Metrics / KPIs

- Smooth 1080p playback on Pi 4+.
- Sub-250 ms response to MQTT messages.
- Projection and LED playback synchronized.
- Field mask adjustments <5 min.
- No crashes during 4+ hours.
- New videos can be added via helper script without mask reconfiguration.

9. Collaboration & Developer Guidelines

- Claude Code reviews requirements, flags feasibility issues.
- Unit/integration tests: video playback, mask UI, MQTT triggers.
- Stress-test continuous 1080p playback.
- Validate state transitions, fallback behavior, and sync buffer.
- Clear, readable, maintainable code; proper logging; no leftover dev artifacts.

10. Deliverables

Raspberry Pi-compatible app:

- Video playback engine, 6 horizontal bar masking
- Drag-and-drop corner adjustment UI
- Keyboard toggle for edit/playback mode
- Adjustable crossfade & buffer (global)
- MQTT-triggered video switching (Pi follows ESP32)
- Config/mask persistence
- Helper script for video encoding

ESP32 firmware:

- PIR-controlled animation selection
- Ambient and active animations looping indefinitely
- MQTT communication with ESP32→Pi sync messages
- Automatic Wi-Fi/MQTT reconnection
- Optional heartbeat messages

Documentation:

- Installation guide (Pi + ESP32)
- Media folder structure
- Mask adjustment & playback parameter guide
