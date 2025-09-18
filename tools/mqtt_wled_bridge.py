#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import signal
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    print("This tool requires paho-mqtt. Install with: pip install paho-mqtt", file=sys.stderr)
    sys.exit(1)

try:
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
except ImportError:  # pragma: no cover
    urlopen = None  # type: ignore


LOG = logging.getLogger("mqtt_wled_bridge")


def load_mapping(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Expected format:
            # {
            #   "by_slot": {"1": {"media": "active_01", "state": "active"}, ...},
            #   "by_name": {"ambient_01": {"media": "ambient_01", "state": "ambient"}, ...}
            # }
            return data or {}
    except FileNotFoundError:
        LOG.warning("Mapping file not found: %s", path)
        return {}
    except json.JSONDecodeError as e:
        LOG.error("Failed to parse mapping JSON %s: %s", path, e)
        return {}


def fetch_wled_presets(wled_host: Optional[str], timeout: float = 3.0) -> Dict[str, Any]:
    if not wled_host or not urlopen:
        return {}
    # WLED exposes presets at /presets.json
    # Example response: { "1": {"n":"preset_name", ...}, ... }
    url = f"http://{wled_host}/presets.json"
    try:
        with urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                LOG.warning("Non-200 from WLED presets: %s", resp.status)
                return {}
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (URLError, HTTPError) as e:
        LOG.warning("Could not fetch WLED presets from %s: %s", url, e)
        return {}
    except Exception as e:  # pragma: no cover
        LOG.warning("Unexpected error fetching presets: %s", e)
        return {}


def resolve_media_state(
    ps_value: Optional[int],
    presets: Dict[str, Any],
    mapping: Dict[str, Dict[str, Any]],
    default_prefix_active: str = "active_",
    default_prefix_ambient: str = "ambient_",
) -> Optional[Tuple[str, str]]:
    if ps_value is None or ps_value < 0:
        return None

    # 1) mapping by slot number takes precedence
    by_slot = mapping.get("by_slot", {})
    slot_key = str(ps_value)
    if slot_key in by_slot:
        entry = by_slot[slot_key]
        media = entry.get("media")
        state = entry.get("state")
        if media and state in ("active", "ambient"):
            return media, state

    # 2) try to resolve preset name from WLED presets.json
    name = None
    if presets:
        # WLED presets keys are strings of slot numbers
        slot = presets.get(slot_key)
        if isinstance(slot, dict):
            name = slot.get("n") or slot.get("name")

    # 3) mapping by name if available
    by_name = mapping.get("by_name", {})
    if name and name in by_name:
        entry = by_name[name]
        media = entry.get("media") or name
        state = entry.get("state")
        if media and state in ("active", "ambient"):
            return media, state

    # 4) default naming convention
    if name:
        if name.startswith(default_prefix_ambient):
            return name, "ambient"
        # treat everything else as active by default
        return name, "active"

    # 5) fallback to generic media id by slot
    media = f"preset_{ps_value:03d}"
    return media, "active"


class Bridge:
    def __init__(
        self,
        broker: str,
        port: int,
        wled_device: str,
        publish_topic: str,
        username: Optional[str],
        password: Optional[str],
        wled_host: Optional[str],
        mapping_path: Optional[str],
        start_after_ms: Optional[int],
        verbose: bool,
        dedupe_seconds: float,
    ) -> None:
        self.broker = broker
        self.port = port
        self.wled_state_topic = f"wled/{wled_device}/state"
        self.publish_topic = publish_topic
        self.username = username
        self.password = password
        self.wled_host = wled_host
        self.mapping = load_mapping(mapping_path)
        self.presets = fetch_wled_presets(wled_host)
        self.start_after_ms = start_after_ms
        self.verbose = verbose
        self.dedupe_seconds = dedupe_seconds
        self._last_ps_sent: Optional[int] = None
        self._last_sent_ts: float = 0.0

        self.client = mqtt.Client()
        if username:
            self.client.username_pw_set(username, password or "")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self._stop = threading.Event()

    def _on_connect(self, client, userdata, flags, rc):  # noqa: D401
        if rc == 0:
            LOG.info("Connected to MQTT broker %s:%s", self.broker, self.port)
            client.subscribe(self.wled_state_topic, qos=0)
            LOG.info("Subscribed to %s", self.wled_state_topic)
        else:
            LOG.error("MQTT connection failed with code %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            LOG.warning("Unexpected MQTT disconnect (rc=%s). Reconnecting...", rc)

    def _publish_playback(self, media: str, state: str):
        payload: Dict[str, Any] = {"state": state, "media": media}
        if self.start_after_ms is not None:
            payload["start_after_ms"] = int(self.start_after_ms)
        data = json.dumps(payload, separators=(",", ":"))
        if self.verbose:
            LOG.info("Publish %s => %s", self.publish_topic, data)
        self.client.publish(self.publish_topic, data, qos=0, retain=False)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            LOG.debug("Non-JSON payload on %s; ignoring", msg.topic)
            return

        # WLED state JSON includes "ps" for current preset slot
        ps_value = None
        if isinstance(payload, dict):
            ps_value = payload.get("ps")
            # Some payloads may embed state under keys; ignore if missing
            if not isinstance(ps_value, int):
                # If no preset present, ignore
                return

        # Dedupe identical preset reports within a small window
        now = time.time()
        if self._last_ps_sent == ps_value and (now - self._last_sent_ts) < self.dedupe_seconds:
            return

        resolved = resolve_media_state(ps_value, self.presets, self.mapping)
        if not resolved:
            return
        media, state = resolved
        self._publish_playback(media, state)
        self._last_ps_sent = ps_value
        self._last_sent_ts = now

    def run(self):
        self.client.connect(self.broker, self.port, keepalive=30)
        try:
            self.client.loop_start()
            while not self._stop.is_set():
                time.sleep(0.2)
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def stop(self):
        self._stop.set()


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge WLED preset changes to Halloween playback MQTT payloads",
    )
    parser.add_argument("--broker", default=os.environ.get("MQTT_BROKER", "localhost"), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", 1883)), help="MQTT broker port")
    parser.add_argument("--username", default=os.environ.get("MQTT_USERNAME"), help="MQTT username")
    parser.add_argument("--password", default=os.environ.get("MQTT_PASSWORD"), help="MQTT password")
    parser.add_argument("--wled-device", required=True, help="WLED device name used in MQTT topic: wled/<device>/state")
    parser.add_argument("--wled-host", default=os.environ.get("WLED_HOST"), help="Optional WLED host/IP to fetch presets.json for name mapping")
    parser.add_argument("--publish-topic", default=os.environ.get("PLAYBACK_TOPIC", "halloween/playback"), help="Playback control topic to publish to")
    parser.add_argument("--mapping", help="Optional JSON mapping file for preset slot/name to media/state")
    parser.add_argument("--start-after-ms", type=int, default=None, help="Optional start-after buffer to include in payload (e.g., 250)")
    parser.add_argument("--dedupe-seconds", type=float, default=1.0, help="Suppress duplicate publishes for the same preset within this window")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    bridge = Bridge(
        broker=args.broker,
        port=args.port,
        wled_device=args.wled_device,
        publish_topic=args.publish_topic,
        username=args.username,
        password=args.password,
        wled_host=args.wled_host,
        mapping_path=args.mapping,
        start_after_ms=args.start_after_ms,
        verbose=args.verbose,
        dedupe_seconds=args.dedupe_seconds,
    )

    stop_event = threading.Event()

    def handle_sig(signum, frame):  # noqa: ANN001
        LOG.info("Received signal %s, shutting down...", signum)
        stop_event.set()
        bridge.stop()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        bridge.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
