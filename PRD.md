# Halloween Projection Mapper – Master Product Requirements Document (PRD)

Product Name: Halloween Projection Mapper (working title)
Prepared For: Claude Code Development
Date: September 11, 2025

1. Overview / Vision

Develop a lightweight projection-mapping playback application for a Halloween display. The system consists of:

- A Raspberry Pi 4 or newer running a projection mapping app for 6 horizontal bars (stairs).
- A dedicated LED animation controller (custom firmware or automation service) driving a 3×3 grid of 16×16 LED panels as a single 48×48 matrix.

The animation controller publishes playback states via MQTT. A PIR sensor or other trigger connected to that controller drives state transitions. The Pi listens for state/media selections over MQTT and plays the corresponding videos, ensuring projection and LEDs remain synchronized. The Pi app allows field adjustment of projection alignment and basic playback parameters.

2. Target Users / Personas

- Home hobbyists or small-scale decorators using projection + LED displays.
- Users wanting minimal setup and instant visual feedback.
- Users wanting seamless coordination of projection and LED animations.

3. Problem Statement

Existing projection-mapping software is either overkill, unstable on Raspberry Pi, or not designed for small, motion-triggered interactive displays. Users need a lightweight, reliable system that:

- Plays pre-defined videos mapped to physical steps or surfaces.
- Responds instantly to motion detection.
- Plays videos synchronized with LED animations controlled by an external animation controller.
- Allows field adjustment of projection alignment.

4. Goals

- Stable, low-latency playback on Raspberry Pi 4+.
- Motion-triggered interaction using MQTT from an external controller.
- Intuitive mask/geometry adjustment in the field.
- Seamless video looping and state-based playback for engaging displays.
- Quick visual transitions (200 ms crossfade) between ambient and active states.
- Adjustable basic playback parameters (crossfade length, buffer before state change).
- Pi-friendly video encoding via helper script.
- Controller fully automated; LEDs and Pi synchronized.

5. Features / Functionality

5.1 Core Playback (Pi)

- Load a library of videos stored locally on the Pi; each video has a corresponding LED animation.
- One video at a time, split into 6 horizontal bars for stair projection.
- Loop selected video continuously until a new MQTT message is received.
- Smooth 200 ms crossfade between videos or states.
- Playback ignores audio.

5.2 Triggering / Interaction (Pi)

- Subscribes to MQTT control topic: halloween/playback.

Payload format:

{
  "state": "active",      // "active" or "ambient"
  "media": "active_07"    // unique ID or filename stem (alias: "animation")
}

Behavior:

- If media exists: start playback immediately (<250 ms latency).
- If media does not exist: fallback to looping an ambient video.
- If MQTT messages are missing (controller offline): loop an ambient video.
- By default, the Pi follows explicit media selections from the controller; optional local selection can be enabled when the controller only publishes state.

Controller integration options:
- Direct: controller publishes playback commands to `halloween/playback` using the standard payload.
- Bridged: a lightweight adapter (broker rule or helper script) can translate third-party topics (e.g., legacy WLED preset updates) into the standardized payload for maximal compatibility.

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

- Pi subscribes to `halloween/playback` (or uses a bridge to adapt controller-specific topics).
- Plays exactly the media instructed by the external controller when provided.
- Ensures LEDs and projection remain synchronized.
- Target: start playback <250 ms after receiving message.
- To align with the Pi’s 200 ms crossfade, Pi applies a configurable start buffer (e.g., 250 ms) after detecting a controller state change before switching videos.

6. LED System Requirements (external controller workflow)

6.1 Hardware & Peripherals

- A microcontroller or server-based animation controller capable of driving the LED matrix.
- Single PIR presence sensor (or equivalent trigger) wired to the controller.
- 3×3 LED grid (16×16 panels) addressed as one contiguous 48×48 surface by the controller (tile orientation/serpentine handled upstream).

6.2 Animation Library

- Animations are stored on/served by the controller (custom renderer, DMX server, etc.). WLED can still be used as a prototyping tool, but production playback is handled elsewhere.
- Recommended naming convention mirrors video IDs so the Pi and controller stay aligned (`ambient_01`, `active_07`, etc.).

Categories and naming:
- Ambient presets (~3): names/prefix `ambient_01`, `ambient_02`, ...
- Active presets (~12): names/prefix `active_01`, `active_02`, ...

Mapping to Pi videos:
- The Pi maps incoming animation identifiers to video IDs (e.g., `active_07`). The LED animation controller plays the matching effect based on the shared identifier and palette information.
- Animations loop on the controller until state changes.

6.3 Motion Detection & State

- PIR sensor (or equivalent trigger) initiates state changes on the controller.
- Debounce/cooldowns configured in the controller or automation layer:
  - Minimum active duration (e.g., 5–10 s)
  - Retrigger cooldown (e.g., ignore motion for 2–3 s)
  - Ambient return delay (e.g., 10–20 s after last motion)
- Fully automatic; no manual overrides required in the field.
- On power cycle: controller resumes in a safe ambient state.
- Fail silently on sensor or animation errors.

6.4 MQTT Communication

- Controller publishes MQTT messages directly to `halloween/playback`, or a lightweight bridge adapts the controller’s native format to the standard payload `{ "state": "active|ambient", "media": "<id>" }` (alias: `animation`).
- Single publish/notification per state change is sufficient; Pi tolerates duplicates.
- Optional controller heartbeat/status can be forwarded to a status topic (e.g., `halloween/controller/status`): `{ "status":"online", "timestamp":<unix_epoch> }`.
- Open local Wi‑Fi; no encryption/auth for this project scope.
- Automatic Wi‑Fi & MQTT reconnection handled by the controller platform.

6.5 Synchronization

- Pi applies a configurable start buffer (default 250 ms) after detecting a controller state change before switching videos to align with the Pi’s 200 ms crossfade and LED effect onset.
- If Pi connection is lost, the controller continues its own animation playlists.
- Selection strategy: random initial ambient; active animations cycle sequentially or randomly per controller logic.

7. User Stories

- Ambient video plays when no motion detected.
- Active video plays when motion detected.
- Video/LED loops until state changes.
- Projection mask adjustable via corner dragging.
- Projection and LEDs stay synchronized.
- External controller handles animation selection and Pi follows.
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
- MQTT-triggered video switching (Pi follows controller)
- Config/mask persistence
- Helper script for video encoding

Controller integration:

- Controller configured for a 48×48 matrix (3×3 of 16×16 panels) with correct tiling/orientation.
- Animation identifiers aligned with Pi `media` IDs (e.g., `ambient_01`, `active_07`).
- Sensor integration (PIR or equivalent) to trigger state changes.
- MQTT publishing directly to `halloween/playback` or via a bridge.
- Optional heartbeat/status forwarding.

Documentation:

- Installation guide (Pi + controller)
- Media folder structure and preset naming conventions
- Mask adjustment & playback parameter guide
- Bridge instructions for adapting third-party controllers (e.g., legacy WLED topics)
