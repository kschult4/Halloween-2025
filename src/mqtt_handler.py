"""
MQTT handler for Halloween Projection Mapper.
Manages ESP32 communication and state-based video switching.
"""
import json
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTHandler:
    """Handles MQTT communication with ESP32 for state and media control."""
    
    def __init__(self, 
                 broker_host: str = "localhost",
                 broker_port: int = 1883,
                 topic: str = "halloween/playback",
                 timeout_seconds: int = 60):
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.timeout_seconds = timeout_seconds
        
        # MQTT client
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        
        # Message handling
        self.message_callback: Optional[Callable[[str, str], None]] = None
        self.last_message_time = 0
        self.current_state = "ambient"
        self.current_media = None
        
        # Timeout monitoring
        self.timeout_thread: Optional[threading.Thread] = None
        self.should_monitor_timeout = False
        
    def set_message_callback(self, callback: Callable[[str, str], None]):
        """Set callback function for handling state/media messages.
        
        Args:
            callback: Function that takes (state, media) parameters
        """
        self.message_callback = callback
    
    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            # Create MQTT client
            self.client = mqtt.Client(
                client_id="halloween_projection_mapper",
                protocol=mqtt.MQTTv311
            )
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            # Configure automatic reconnect backoff if available
            try:
                self.client.reconnect_delay_set(min_delay=1, max_delay=30)
            except Exception:
                pass
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # Start networking loop
            self.client.loop_start()
            
            # Wait for connection
            connect_timeout = 10  # seconds
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < connect_timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                logger.info("MQTT connection established")
                self._start_timeout_monitoring()
                return True
            else:
                logger.error("MQTT connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self._stop_timeout_monitoring()
        
        if self.client:
            logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        
        self.is_connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.is_connected = True
            logger.info(f"Connected to MQTT broker, subscribing to {self.topic}")
            
            # Subscribe to Halloween playback topic
            client.subscribe(self.topic)
            
            # Update last message time to prevent immediate timeout
            self.last_message_time = time.time()
            
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection."""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code {rc})")
        else:
            logger.info("MQTT disconnected")
        # Start background reconnect attempts
        if self.client:
            try:
                try:
                    self.client.reconnect_delay_set(min_delay=1, max_delay=30)
                except Exception:
                    pass
                t = threading.Thread(target=self._attempt_reconnect_loop, daemon=True)
                t.start()
            except Exception as e:
                logger.debug(f"Failed to start reconnect loop: {e}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for received MQTT messages."""
        try:
            # Decode message
            payload = msg.payload.decode('utf-8')
            logger.debug(f"Received MQTT message: {payload}")
            
            # Parse JSON payload
            data = json.loads(payload)
            
            # Ignore status/heartbeat-only messages (no control state)
            if 'state' not in data:
                logger.debug("Ignoring MQTT payload without 'state' field")
                return
            
            # Extract state and media (support 'animation' alias)
            state = data.get('state')
            media = data.get('media') or data.get('animation')
            
            # Validate state
            if state not in ['active', 'ambient']:
                logger.warning(f"Invalid state received: {state}, defaulting to ambient")
                state = 'ambient'
            
            # Update tracking
            self.current_state = state
            self.current_media = media
            self.last_message_time = time.time()
            
            logger.info(f"MQTT message: state={state}, media={media}")
            
            # Call message handler
            if self.message_callback:
                self.message_callback(state, media)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _attempt_reconnect_loop(self):
        """Attempt reconnect with exponential backoff until connected or client cleared."""
        delay = 1
        max_delay = 30
        while self.client and not self.is_connected:
            try:
                logger.info("Attempting MQTT reconnect...")
                self.client.reconnect()
            except Exception as e:
                logger.debug(f"Reconnect failed: {e}")
            time.sleep(delay)
            delay = min(max_delay, delay * 2)
    
    def _start_timeout_monitoring(self):
        """Start thread to monitor MQTT message timeout."""
        self.should_monitor_timeout = True
        self.timeout_thread = threading.Thread(target=self._timeout_monitor_loop, daemon=True)
        self.timeout_thread.start()
        logger.debug("MQTT timeout monitoring started")
    
    def _stop_timeout_monitoring(self):
        """Stop timeout monitoring thread."""
        self.should_monitor_timeout = False
        if self.timeout_thread and self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=1.0)
        logger.debug("MQTT timeout monitoring stopped")
    
    def _timeout_monitor_loop(self):
        """Monitor for MQTT message timeout and trigger fallback."""
        while self.should_monitor_timeout:
            try:
                current_time = time.time()
                time_since_last_message = current_time - self.last_message_time
                
                # Check for timeout
                if time_since_last_message > self.timeout_seconds:
                    logger.warning(f"MQTT timeout: no messages for {time_since_last_message:.1f}s")
                    
                    # Trigger fallback to ambient
                    if self.message_callback:
                        logger.info("Triggering fallback to ambient due to MQTT timeout")
                        self.current_state = 'ambient'
                        self.current_media = None
                        self.message_callback('ambient', None)
                    
                    # Reset timer to prevent repeated triggers
                    self.last_message_time = current_time
                
                # Check every 5 seconds
                time.sleep(5.0)
                
            except Exception as e:
                logger.error(f"Error in timeout monitoring: {e}")
                time.sleep(5.0)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection and message status."""
        current_time = time.time()
        time_since_last_message = current_time - self.last_message_time
        
        return {
            "connected": self.is_connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "topic": self.topic,
            "current_state": self.current_state,
            "current_media": self.current_media,
            "last_message_age": time_since_last_message,
            "timeout_threshold": self.timeout_seconds,
            "is_timeout": time_since_last_message > self.timeout_seconds
        }
    
    def publish_status(self, status_data: Dict[str, Any]):
        """Publish status back to MQTT (optional feature for debugging)."""
        if not self.is_connected or not self.client:
            return False
        
        try:
            status_topic = f"{self.topic}/status"
            payload = json.dumps(status_data)
            self.client.publish(status_topic, payload)
            logger.debug(f"Published status: {status_data}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")
            return False

class MQTTSimulator:
    """Simulates ESP32 MQTT messages for testing."""
    
    def __init__(self, 
                 broker_host: str = "localhost",
                 broker_port: int = 1883,
                 topic: str = "halloween/playback"):
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """Connect simulator to MQTT broker."""
        try:
            self.client = mqtt.Client(
                client_id="halloween_esp32_simulator",
                protocol=mqtt.MQTTv311
            )
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            logger.info(f"Simulator connecting to {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < 5:
                time.sleep(0.1)
            
            return self.is_connected
            
        except Exception as e:
            logger.error(f"Simulator connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect simulator."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        self.is_connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Simulator connection callback."""
        if rc == 0:
            self.is_connected = True
            logger.info("ESP32 simulator connected")
        else:
            logger.error(f"Simulator connection failed: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Simulator disconnection callback."""
        self.is_connected = False
        logger.info("ESP32 simulator disconnected")
    
    def send_message(self, state: str, media: Optional[str] = None) -> bool:
        """Send a message as ESP32 would."""
        if not self.is_connected or not self.client:
            logger.error("Simulator not connected")
            return False
        
        try:
            payload = {
                "state": state,
                "media": media
            }
            
            message = json.dumps(payload)
            self.client.publish(self.topic, message)
            logger.info(f"Simulator sent: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send simulator message: {e}")
            return False
    
    def simulate_motion_sequence(self, active_media: str = "active_01"):
        """Simulate a typical motion detection sequence."""
        logger.info("Starting motion simulation sequence...")
        
        # Motion detected - switch to active
        self.send_message("active", active_media)
        time.sleep(3)  # Active video plays for 3 seconds
        
        # Motion stops - back to ambient
        self.send_message("ambient", "ambient_01")
        logger.info("Motion simulation complete")

# Test functions for Stage 3 verification
def test_mqtt_handler():
    """Test MQTT handler functionality."""
    print("Testing MQTT Handler...")
    
    # Test message parsing
    handler = MQTTHandler(timeout_seconds=5)
    
    messages_received = []
    
    def test_callback(state, media):
        messages_received.append((state, media))
    
    handler.set_message_callback(test_callback)
    
    # Simulate message processing
    test_payload = json.dumps({"state": "active", "media": "active_01"})
    
    # Create mock message
    class MockMessage:
        def __init__(self, payload):
            self.payload = payload
    
    handler._on_message(None, None, MockMessage(test_payload.encode()))
    
    # Verify callback was called
    assert len(messages_received) == 1, "Should receive one message"
    assert messages_received[0] == ("active", "active_01"), "Should parse message correctly"
    
    print("✅ MQTT Handler tests passed")

if __name__ == "__main__":
    test_mqtt_handler()
