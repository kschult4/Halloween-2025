# Halloween Projection Mapper – Master Product Requirements Document (PRD)

Product Name: Halloween Projection Mapper (working title)
Prepared For: Claude Code Development
Date: September 11, 2025

1. Overview / Vision

Develop a lightweight projection-mapping playback application for a Halloween display. The system consists of:

- A Raspberry Pi 4 or newer running a projection mapping app for 6 horizontal bars (stairs).
- An ESP32 running WLED, controlling a 3×3 grid of 16×16 LED panels as a single 48×48 matrix.

WLED handles LED effects and preset management on the ESP32. A PIR sensor connected to the ESP32 (via WLED GPIO/usermod) triggers preset changes. The Pi listens for preset/state changes via MQTT and plays the corresponding videos, ensuring projection and LEDs remain synchronized. The Pi app allows field adjustment of projection alignment and basic playback parameters.

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

- Subscribes to MQTT control topic: halloween/playback.

Payload format:

{
  "state": "active",      // "active" or "ambient"
  "media": "active_07"    // unique ID or filename stem (alias: "animation")
}

Behavior:

- If media exists: start playback immediately (<250 ms latency).
- If media does not exist: fallback to looping an ambient video.
- If MQTT messages are missing (ESP32 offline): loop an ambient video.
- Pi does not randomly select videos; selection is done by WLED presets on the ESP32.

WLED integration options:
- Direct: Pi subscribes to WLED's MQTT JSON state topic (e.g., wled/<device>/state) and maps preset changes (by preset ID or name) to `media` IDs.
- Bridged: A small MQTT bridge (broker rule or helper script) republishes WLED preset changes to `halloween/playback` with the payload above for maximal compatibility with the Pi app.

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

- Pi subscribes to `halloween/playback` (or maps from WLED state topic).
- Plays exactly the media instructed by WLED preset selection.
- Ensures LEDs and projection remain synchronized.
- Target: start playback <250 ms after receiving message.
- To align with the Pi’s 200 ms crossfade, Pi applies a configurable start buffer (e.g., 250 ms) after detecting a WLED preset change before switching videos.

6. ESP32 / LED System Requirements (WLED workflow)

6.1 Hardware & Peripherals

- ESP32 microcontroller running WLED (current stable release).
- Single PIR presence sensor wired to a WLED-supported GPIO (via built-in `Sensor/PIR` option or a usermod/automation).
- 3×3 LED grid (16×16 panels), treated as one contiguous 48×48 surface using WLED’s 2D matrix/segment configuration (tile orientation/serpentine handled in WLED).

6.2 Presets & Playlists (Animations)

- Animations are WLED presets (parameterized built-in effects and palettes) optionally organized into playlists.
- Presets are the source of truth for LED content; no custom LED firmware.

Categories and naming:
- Ambient presets (~3): names/prefix `ambient_01`, `ambient_02`, ...
- Active presets (~12): names/prefix `active_01`, `active_02`, ...

Mapping to Pi videos:
- The Pi maps incoming preset identifier to a video by matching the preset name or a configured mapping table to the `media` ID (e.g., `active_07`).
- Presets loop in WLED until state changes.

6.3 Motion Detection & State

- PIR sensor triggers preset changes in WLED (via WLED sensor integration/usermod/automation).
- Debounce/cooldowns configured in WLED or via simple automation logic:
  - Minimum active duration (e.g., 5–10 s)
  - Retrigger cooldown (e.g., ignore motion for 2–3 s)
  - Ambient return delay (e.g., 10–20 s after last motion)
- Fully automatic; no manual overrides required in the field.
- On power cycle: WLED resumes; default preset is an ambient preset.
- Fail silently on sensor or animation errors.

6.4 MQTT Communication

- WLED MQTT is enabled. Two integration approaches are supported:
  1) Pi subscribes to WLED’s JSON state topic (e.g., `wled/<device>/state`) and reacts to preset changes.
  2) A lightweight bridge republishes preset changes to `halloween/playback` with payload `{ "state": "active|ambient", "media": "<preset_name>" }` (alias: `animation`).
- Single publish/notification per state change is sufficient; Pi tolerates duplicates.
- Optional ESP32 heartbeat/status can be forwarded to a status topic (e.g., `halloween/esp32/status`): `{ "status":"online", "timestamp":<unix_epoch> }`.
- Open local Wi‑Fi; no encryption/auth for this project scope.
- Automatic Wi‑Fi & MQTT reconnection per WLED.

6.5 Synchronization

- Pi applies a configurable start buffer (default 250 ms) after detecting a preset change before switching videos to align with the Pi’s 200 ms crossfade and WLED effect onset.
- If Pi connection is lost, WLED continues its own presets/playlists.
- Preset selection strategy: random initial ambient; active presets cycle sequentially or randomly per WLED playlist/automation.

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

ESP32 (WLED) configuration:

- WLED configured for a 48×48 matrix (3×3 of 16×16 panels) with correct tiling/orientation.
- Presets/playlists created and named to match Pi `media` IDs (e.g., `ambient_01`, `active_07`).
- PIR integration (sensor/usermod/automation) to trigger preset changes.
- MQTT enabled; either Pi subscribes to WLED state or a simple bridge republishes to `halloween/playback`.
- Optional heartbeat/status forwarding.

Documentation:

- Installation guide (Pi + WLED)
- Media folder structure and preset naming conventions
- Mask adjustment & playback parameter guide
- WLED-to-Pi mapping/bridge instructions (topics, payloads, examples)
