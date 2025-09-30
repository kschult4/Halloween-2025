"""
Configuration manager for Halloween Projection Mapper.
Handles loading, saving, and runtime adjustment of playback parameters.
"""
import json
import os
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration settings for playback parameters."""
    
    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self.settings: Dict[str, Any] = {}
        
        # Default settings
        self.defaults = {
            "crossfade_duration_ms": 200,
            "state_change_buffer_ms": 250,
            "mqtt_timeout_seconds": 60,
            "video_preload_seconds": 2.0,
            "loop_enabled": True,
            "hardware_acceleration": True,
            "display_fps": 30,
        }
        
        # Load existing settings or create defaults
        self.load_settings()
    
    def load_settings(self):
        """Load settings from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    file_settings = json.load(f)
                
                # Merge with defaults (file settings override defaults)
                self.settings = self.defaults.copy()
                self.settings.update(file_settings)
                
                logger.info(f"Loaded settings from {self.config_path}")
            else:
                logger.info(f"No settings file found, using defaults")
                self.settings = self.defaults.copy()
                self.save_settings()  # Create default file
                
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self.settings = self.defaults.copy()
    
    def save_settings(self):
        """Save current settings to JSON file."""
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info(f"Saved settings to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value
        logger.debug(f"Setting updated: {key} = {value}")
    
    def get_crossfade_duration_ms(self) -> int:
        """Get crossfade duration in milliseconds."""
        return self.get("crossfade_duration_ms", 200)
    
    def set_crossfade_duration_ms(self, value: int):
        """Set crossfade duration in milliseconds."""
        value = max(0, min(value, 5000))  # Clamp between 0-5000ms
        self.set("crossfade_duration_ms", value)
    
    def get_state_change_buffer_ms(self) -> int:
        """Get state change buffer in milliseconds."""
        return self.get("state_change_buffer_ms", 250)
    
    def set_state_change_buffer_ms(self, value: int):
        """Set state change buffer in milliseconds."""
        value = max(0, min(value, 10000))  # Clamp between 0-10000ms
        self.set("state_change_buffer_ms", value)
    
    def get_mqtt_timeout_seconds(self) -> int:
        """Get MQTT timeout in seconds."""
        return self.get("mqtt_timeout_seconds", 60)
    
    def set_mqtt_timeout_seconds(self, value: int):
        """Set MQTT timeout in seconds."""
        value = max(10, min(value, 300))  # Clamp between 10-300 seconds
        self.set("mqtt_timeout_seconds", value)
    
    def adjust_crossfade_duration(self, delta_ms: int):
        """Adjust crossfade duration by delta amount."""
        current = self.get_crossfade_duration_ms()
        new_value = current + delta_ms
        self.set_crossfade_duration_ms(new_value)
        return new_value
    
    def adjust_state_change_buffer(self, delta_ms: int):
        """Adjust state change buffer by delta amount."""
        current = self.get_state_change_buffer_ms()
        new_value = current + delta_ms
        self.set_state_change_buffer_ms(new_value)
        return new_value
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self.settings = self.defaults.copy()
        logger.info("Settings reset to defaults")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self.settings.copy()
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update multiple settings at once."""
        for key, value in new_settings.items():
            if key in self.defaults:  # Only allow known settings
                self.set(key, value)
        logger.info(f"Updated {len(new_settings)} settings")

class CrossfadeManager:
    """Manages crossfade transitions between videos."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.is_crossfading = False
        self.crossfade_start_time = 0
        self.old_frame: Optional[Any] = None
        self.crossfade_alpha = 0.0
    
    def start_crossfade(self, old_frame: Any):
        """Start a crossfade transition."""
        duration_ms = self.config.get_crossfade_duration_ms()
        
        if duration_ms <= 0:
            # No crossfade
            self.is_crossfading = False
            return
        
        self.is_crossfading = True
        self.crossfade_start_time = self._get_time_ms()
        self.old_frame = old_frame
        self.crossfade_alpha = 1.0  # Start with old frame fully visible
        
        logger.debug(f"Started crossfade transition ({duration_ms}ms)")
    
    def update_crossfade(self, new_frame: Any) -> Any:
        """Update crossfade and return blended frame."""
        if not self.is_crossfading or self.old_frame is None:
            return new_frame
        
        current_time = self._get_time_ms()
        duration_ms = self.config.get_crossfade_duration_ms()
        elapsed = current_time - self.crossfade_start_time
        
        if elapsed >= duration_ms:
            # Crossfade complete
            self.is_crossfading = False
            self.old_frame = None
            self.crossfade_alpha = 0.0
            return new_frame
        
        # Calculate alpha for blending (1.0 = old frame, 0.0 = new frame)
        self.crossfade_alpha = 1.0 - (elapsed / duration_ms)
        
        # Blend frames
        try:
            import cv2
            import numpy as np
            
            # Ensure frames are the same size
            if self.old_frame.shape != new_frame.shape:
                self.old_frame = cv2.resize(self.old_frame, 
                                          (new_frame.shape[1], new_frame.shape[0]))
            
            # Alpha blend: result = alpha * old + (1-alpha) * new
            blended = cv2.addWeighted(
                self.old_frame, self.crossfade_alpha,
                new_frame, 1.0 - self.crossfade_alpha,
                0
            )
            
            return blended
            
        except Exception as e:
            logger.error(f"Crossfade blending error: {e}")
            # Fallback to new frame
            self.is_crossfading = False
            return new_frame
    
    def _get_time_ms(self) -> float:
        """Get current time in milliseconds."""
        import time
        return time.time() * 1000
    
    def is_active(self) -> bool:
        """Check if crossfade is currently active."""
        return self.is_crossfading
    
    def get_progress(self) -> float:
        """Get crossfade progress (0.0 to 1.0)."""
        if not self.is_crossfading:
            return 1.0
        
        current_time = self._get_time_ms()
        duration_ms = self.config.get_crossfade_duration_ms()
        elapsed = current_time - self.crossfade_start_time
        
        return min(1.0, elapsed / duration_ms) if duration_ms > 0 else 1.0

class ParameterAdjustmentUI:
    """UI for adjusting playback parameters during runtime."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.show_ui = False
        self.selected_param = 0
        self.parameters = [
            ("Crossfade Duration (ms)", "crossfade_duration_ms", 50),
            ("State Change Buffer (ms)", "state_change_buffer_ms", 100),
            ("MQTT Timeout (s)", "mqtt_timeout_seconds", 5),
        ]
    
    def toggle_ui(self):
        """Toggle parameter adjustment UI visibility."""
        self.show_ui = not self.show_ui
        if self.show_ui:
            logger.info("Parameter adjustment UI enabled")
        else:
            logger.info("Parameter adjustment UI disabled")
    
    def handle_keyboard_input(self, key: int) -> bool:
        """Handle keyboard input for parameter adjustment."""
        if not self.show_ui:
            return False
        
        key_char = chr(key & 0xFF).lower()
        
        # Navigation
        if key == 81 or key == 82:  # Arrow up/down (may vary by system)
            self.selected_param = (self.selected_param + 1) % len(self.parameters)
            return True
        elif key_char == 'p':
            self.toggle_ui()
            return True
        
        # Adjustment
        elif key_char == '+' or key_char == '=':
            self._adjust_selected_parameter(1)
            return True
        elif key_char == '-':
            self._adjust_selected_parameter(-1)
            return True
        
        # Save
        elif key_char == 's':
            self.config.save_settings()
            logger.info("Settings saved")
            return True
        
        # Reset
        elif key_char == 'r':
            self._reset_selected_parameter()
            return True
        
        return False
    
    def _adjust_selected_parameter(self, direction: int):
        """Adjust the currently selected parameter."""
        if 0 <= self.selected_param < len(self.parameters):
            name, key, step = self.parameters[self.selected_param]
            
            current = self.config.get(key)
            new_value = current + (direction * step)
            
            # Apply bounds based on parameter type
            if key == "crossfade_duration_ms":
                new_value = max(0, min(new_value, 5000))
                self.config.set_crossfade_duration_ms(new_value)
            elif key == "state_change_buffer_ms":
                new_value = max(0, min(new_value, 10000))
                self.config.set_state_change_buffer_ms(new_value)
            elif key == "mqtt_timeout_seconds":
                new_value = max(10, min(new_value, 300))
                self.config.set_mqtt_timeout_seconds(new_value)
            
            logger.info(f"Adjusted {name}: {current} → {new_value}")
    
    def _reset_selected_parameter(self):
        """Reset selected parameter to default value."""
        if 0 <= self.selected_param < len(self.parameters):
            name, key, _ = self.parameters[self.selected_param]
            default_value = self.config.defaults.get(key)
            self.config.set(key, default_value)
            logger.info(f"Reset {name} to default: {default_value}")
    
    def draw_ui(self, image):
        """Draw parameter adjustment UI overlay."""
        if not self.show_ui:
            return
        
        try:
            import cv2
            
            # UI background
            overlay = image.copy()
            ui_height = 200
            ui_width = 400
            ui_x = 50
            ui_y = 50
            
            cv2.rectangle(overlay, (ui_x, ui_y), (ui_x + ui_width, ui_y + ui_height), 
                         (40, 40, 40), -1)
            cv2.addWeighted(overlay, 0.8, image, 0.2, 0, image)
            
            # Title
            cv2.putText(image, "Playback Parameters", (ui_x + 10, ui_y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Parameters
            for i, (name, key, _) in enumerate(self.parameters):
                y_pos = ui_y + 60 + (i * 30)
                current_value = self.config.get(key)
                
                # Highlight selected parameter
                color = (100, 255, 100) if i == self.selected_param else (255, 255, 255)
                text = f"{name}: {current_value}"
                
                cv2.putText(image, text, (ui_x + 10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Instructions
            instructions = [
                "P: Toggle UI",
                "+/-: Adjust value",
                "S: Save settings",
                "R: Reset selected"
            ]
            
            for i, instruction in enumerate(instructions):
                y_pos = ui_y + ui_height - 60 + (i * 15)
                cv2.putText(image, instruction, (ui_x + 10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
        except Exception as e:
            logger.error(f"Error drawing parameter UI: {e}")

# Test functions
def test_config_manager():
    """Test configuration manager functionality."""
    print("Testing ConfigManager...")
    
    # Test with temporary config file
    config = ConfigManager("config/test_config.json")
    
    # Test default values
    assert config.get_crossfade_duration_ms() == 200, "Default crossfade should be 200ms"
    
    # Test setting values
    config.set_crossfade_duration_ms(300)
    assert config.get_crossfade_duration_ms() == 300, "Crossfade should be updated"
    
    # Test bounds
    config.set_crossfade_duration_ms(-100)
    assert config.get_crossfade_duration_ms() >= 0, "Crossfade should be clamped to >= 0"
    
    config.set_crossfade_duration_ms(10000)
    assert config.get_crossfade_duration_ms() <= 5000, "Crossfade should be clamped to <= 5000"
    
    # Test save/load
    config.save_settings()
    config2 = ConfigManager("config/test_config.json")
    assert config2.get_crossfade_duration_ms() == config.get_crossfade_duration_ms(), "Settings should persist"
    
    print("✅ ConfigManager tests passed")

if __name__ == "__main__":
    test_config_manager()
