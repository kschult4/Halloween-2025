import sys, os, json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_mqtt_alias_and_heartbeat():
    from mqtt_handler import MQTTHandler
    received = []
    handler = MQTTHandler(timeout_seconds=5)
    handler.set_message_callback(lambda s,m: received.append((s,m)))

    class Mock:
        def __init__(self, payload):
            self.payload = payload.encode()

    # Heartbeat (no state) should be ignored
    handler._on_message(None, None, Mock(json.dumps({"status":"online","timestamp": 12345})))

    # Valid control with media
    handler._on_message(None, None, Mock(json.dumps({"state":"active","media":"active_01"})))

    # Valid control with animation alias
    handler._on_message(None, None, Mock(json.dumps({"state":"ambient","animation":"ambient_01"})))

    print('Received callbacks:', received)
    assert received[0] == ('active','active_01'), 'media field handling failed'
    assert received[1] == ('ambient','ambient_01'), 'animation alias handling failed'
    print('✅ MQTT smoke test passed')

def test_config_defaults():
    from config_manager import ConfigManager
    cfg = ConfigManager(config_path='config/test_smoke_config.json')
    print('Defaults:', cfg.get_all_settings())
    assert cfg.get('crossfade_duration_ms') == 200
    assert cfg.get('state_change_buffer_ms') == 0
    print('✅ Config defaults smoke test passed')

if __name__ == '__main__':
    test_mqtt_alias_and_heartbeat()
    test_config_defaults()
    print('\nAll smoke tests passed')

