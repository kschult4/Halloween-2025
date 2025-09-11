"""
Video playback engine for Halloween Projection Mapper.
Handles H.264 hardware-accelerated playback, preloading, and 6-strip processing.
"""
import os
import threading
import time
import logging
from typing import Dict, Optional, Tuple, List, Any
import cv2
import numpy as np
from mask_manager import MaskManager
from mqtt_handler import MQTTHandler
from config_manager import ConfigManager, CrossfadeManager, ParameterAdjustmentUI
from error_handler import ErrorHandler, ErrorSeverity, handle_error

# Handle ffpyplayer import for Pi vs development
try:
    from ffpyplayer.player import MediaPlayer
    HAS_FFPYPLAYER = True
except ImportError:
    HAS_FFPYPLAYER = False
    MediaPlayer = None
    print("Warning: ffpyplayer not available. Using OpenCV fallback for development.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoStrip:
    """Represents one horizontal strip of a video for stair projection."""
    def __init__(self, strip_index: int, frame_height: int, frame_width: int):
        self.strip_index = strip_index
        self.strip_height = frame_height // 6
        self.y_start = strip_index * self.strip_height
        self.y_end = min((strip_index + 1) * self.strip_height, frame_height)
        self.frame_width = frame_width
        
    def extract_from_frame(self, frame: np.ndarray) -> np.ndarray:
        """Extract this strip from a full video frame."""
        return frame[self.y_start:self.y_end, :, :]

class PreloadedVideo:
    """Container for preloaded video data and metadata."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.player: Optional[MediaPlayer] = None
        self.cv_capture: Optional[cv2.VideoCapture] = None
        self.duration: float = 0.0
        self.fps: float = 30.0
        self.frame_width: int = 1920
        self.frame_height: int = 1080
        self.strips: List[VideoStrip] = []
        self.is_loaded = False
        self.use_opencv = not HAS_FFPYPLAYER
        
    def load_metadata(self):
        """Load video metadata and prepare strips."""
        try:
            if HAS_FFPYPLAYER:
                self._load_metadata_ffpyplayer()
            else:
                self._load_metadata_opencv()
                
        except Exception as e:
            logger.error(f"Failed to load metadata for {self.filepath}: {e}")
    
    def _load_metadata_ffpyplayer(self):
        """Load metadata using ffpyplayer."""
        # Create temporary player to get metadata
        temp_player = MediaPlayer(self.filepath, ff_opts={'vcodec': 'h264_mmal'})
        
        # Get first frame to determine dimensions
        frame, val = temp_player.get_frame()
        if frame is not None:
            img, t = frame
            self.frame_width = img.get_size()[0]
            self.frame_height = img.get_size()[1]
            
        # Get duration and fps
        metadata = temp_player.get_metadata()
        self.duration = metadata.get('duration', 0.0)
        self.fps = metadata.get('frame_rate', 30.0)
        
        temp_player.close_player()
        
        # Create strips
        self.strips = [VideoStrip(i, self.frame_height, self.frame_width) for i in range(6)]
        self.is_loaded = True
        
        logger.info(f"Loaded metadata (ffpyplayer) for {os.path.basename(self.filepath)}: "
                   f"{self.frame_width}x{self.frame_height}, {self.fps}fps, {self.duration:.1f}s")
    
    def _load_metadata_opencv(self):
        """Load metadata using OpenCV as fallback."""
        cap = cv2.VideoCapture(self.filepath)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {self.filepath}")
        
        self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = frame_count / self.fps if self.fps > 0 else 0.0
        
        cap.release()
        
        # Create strips
        self.strips = [VideoStrip(i, self.frame_height, self.frame_width) for i in range(6)]
        self.is_loaded = True
        
        logger.info(f"Loaded metadata (OpenCV) for {os.path.basename(self.filepath)}: "
                   f"{self.frame_width}x{self.frame_height}, {self.fps}fps, {self.duration:.1f}s")
            
    def create_player(self):
        """Create a new player instance (ffpyplayer or OpenCV)."""
        if HAS_FFPYPLAYER:
            ff_opts = {
                'vcodec': 'h264_mmal',  # Hardware decode on Pi
                'an': True,  # No audio
            }
            return MediaPlayer(self.filepath, ff_opts=ff_opts)
        else:
            # OpenCV fallback for development
            return cv2.VideoCapture(self.filepath)

class VideoEngine:
    """Core video playback engine with preloading and strip processing."""
    
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.preloaded_videos: Dict[str, PreloadedVideo] = {}
        self.current_video: Optional[str] = None
        self.current_player: Optional[MediaPlayer] = None
        self.playback_thread: Optional[threading.Thread] = None
        self.is_playing = False
        self.should_loop = True
        self.playback_lock = threading.Lock()
        
        # State management
        self.current_state = "ambient"
        self.fallback_ambient_video = None
        self.last_frame: Optional[np.ndarray] = None
        
        # Error handling and monitoring
        self.error_handler = ErrorHandler()
        self.error_handler.start_monitoring()
        
        # Configuration and crossfade management
        self.config_manager = ConfigManager()
        self.crossfade_manager = CrossfadeManager(self.config_manager)
        self.parameter_ui = ParameterAdjustmentUI(self.config_manager)
        
        # Mask management
        self.mask_manager = MaskManager()
        
        # MQTT communication with configurable timeout
        timeout_seconds = self.config_manager.get_mqtt_timeout_seconds()
        self.mqtt_handler = MQTTHandler(
            broker_host=mqtt_broker, 
            broker_port=mqtt_port,
            timeout_seconds=timeout_seconds
        )
        self.mqtt_handler.set_message_callback(self._handle_mqtt_message)
        
        # Display window
        self.window_name = "Halloween Projection"
        cv2.namedWindow(self.window_name, cv2.WINDOW_FULLSCREEN)
        
        # Set mouse callback for mask editing
        cv2.setMouseCallback(self.window_name, self.mask_manager.handle_mouse_event)
        
    def scan_media_folder(self, media_path: str) -> List[str]:
        """Scan media folder for MP4 files."""
        video_files = []
        if os.path.exists(media_path):
            for file in os.listdir(media_path):
                if file.lower().endswith(('.mp4', '.avi', '.mov')):
                    video_files.append(os.path.join(media_path, file))
        return video_files
    
    def preload_videos(self, media_folders: List[str]):
        """Preload video metadata from specified folders."""
        logger.info("Starting video preloading...")
        
        for folder in media_folders:
            video_files = self.scan_media_folder(folder)
            for video_path in video_files:
                video_id = os.path.splitext(os.path.basename(video_path))[0]
                
                preloaded = PreloadedVideo(video_path)
                preloaded.load_metadata()
                
                if preloaded.is_loaded:
                    self.preloaded_videos[video_id] = preloaded
                    logger.info(f"Preloaded: {video_id}")
        
        logger.info(f"Preloading complete. {len(self.preloaded_videos)} videos ready.")
        
        # Set fallback ambient video
        self._set_fallback_ambient_video()
    
    def get_available_videos(self) -> List[str]:
        """Get list of available video IDs."""
        return list(self.preloaded_videos.keys())
    
    def _set_fallback_ambient_video(self):
        """Set a fallback ambient video for when MQTT is offline or media not found."""
        # Look for ambient videos
        ambient_videos = [vid for vid in self.preloaded_videos.keys() if vid.startswith('ambient')]
        if ambient_videos:
            self.fallback_ambient_video = ambient_videos[0]
            logger.info(f"Set fallback ambient video: {self.fallback_ambient_video}")
        else:
            # Use any available video as fallback
            available = self.get_available_videos()
            if available:
                self.fallback_ambient_video = available[0]
                logger.warning(f"No ambient videos found, using fallback: {self.fallback_ambient_video}")
    
    def _handle_mqtt_message(self, state: str, media: Optional[str]):
        """Handle incoming MQTT state/media messages from ESP32."""
        logger.info(f"MQTT message received: state={state}, media={media}")
        
        self.current_state = state
        
        # Apply state change buffer delay
        buffer_ms = self.config_manager.get_state_change_buffer_ms()
        if buffer_ms > 0:
            logger.debug(f"Applying state change buffer: {buffer_ms}ms")
            time.sleep(buffer_ms / 1000.0)
        
        # Determine target video
        target_video = self._resolve_target_video(state, media)
        
        if target_video:
            # Start crossfade if enabled and we have a current frame
            if self.last_frame is not None and self.config_manager.get_crossfade_duration_ms() > 0:
                self.crossfade_manager.start_crossfade(self.last_frame.copy())
            
            # Measure response time
            start_time = time.time()
            success = self.start_playback(target_video)
            response_time = (time.time() - start_time) * 1000  # ms
            
            if success:
                logger.info(f"MQTT response: switched to '{target_video}' in {response_time:.1f}ms")
            else:
                logger.error(f"MQTT response: failed to switch to '{target_video}'")
                self._fallback_to_ambient()
        else:
            logger.warning(f"MQTT response: no suitable video found, falling back to ambient")
            self._fallback_to_ambient()
    
    def _resolve_target_video(self, state: str, media: Optional[str]) -> Optional[str]:
        """Resolve the target video based on state and media ID."""
        if state == "active" and media:
            # Try exact media match first
            if media in self.preloaded_videos:
                return media
            
            # Try with active prefix if not already present
            if not media.startswith('active_'):
                prefixed_media = f"active_{media}"
                if prefixed_media in self.preloaded_videos:
                    return prefixed_media
            
            logger.warning(f"Requested media '{media}' not found")
            return None
            
        elif state == "ambient":
            # For ambient state, prefer specified media or use fallback
            if media and media in self.preloaded_videos:
                return media
            
            # Try with ambient prefix
            if media and not media.startswith('ambient_'):
                prefixed_media = f"ambient_{media}"
                if prefixed_media in self.preloaded_videos:
                    return prefixed_media
            
            # Use fallback ambient video
            return self.fallback_ambient_video
        
        return None
    
    def _fallback_to_ambient(self):
        """Fallback to ambient video when requested media is not available."""
        if self.fallback_ambient_video:
            logger.info(f"Falling back to ambient video: {self.fallback_ambient_video}")
            self.start_playback(self.fallback_ambient_video)
        else:
            logger.error("No fallback ambient video available")
    
    def connect_mqtt(self) -> bool:
        """Connect to MQTT broker for ESP32 communication."""
        logger.info("Connecting to MQTT broker...")
        success = self.mqtt_handler.connect()
        
        if success:
            logger.info("MQTT connection established - ready for ESP32 commands")
        else:
            logger.error("MQTT connection failed - will use fallback ambient video")
            self._fallback_to_ambient()
        
        return success
    
    def disconnect_mqtt(self):
        """Disconnect from MQTT broker."""
        logger.info("Disconnecting from MQTT broker")
        self.mqtt_handler.disconnect()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for monitoring."""
        mqtt_status = self.mqtt_handler.get_connection_status()
        
        return {
            "video_engine": {
                "current_video": self.current_video,
                "is_playing": self.is_playing,
                "current_state": self.current_state,
                "fallback_video": self.fallback_ambient_video,
                "available_videos": len(self.preloaded_videos)
            },
            "mqtt": mqtt_status,
            "masks": {
                "edit_mode": self.mask_manager.is_editing,
                "masks_loaded": len(self.mask_manager.masks)
            }
        }
    
    def start_playback(self, video_id: str) -> bool:
        """Start playback of specified video with looping."""
        try:
            with self.playback_lock:
                if video_id not in self.preloaded_videos:
                    self.error_handler.handle_error(
                        component="video_playback",
                        error_type="video_not_found",
                        severity=ErrorSeverity.MEDIUM,
                        message=f"Video {video_id} not found in preloaded videos",
                        context={"requested_video": video_id, "available_videos": list(self.preloaded_videos.keys())}
                    )
                    return False
                
                # Stop current playback
                self.stop_playback()
                
                self.current_video = video_id
                self.is_playing = True
                
                # Start playback thread
                self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
                self.playback_thread.start()
                
                logger.info(f"Started playback: {video_id}")
                return True
                
        except Exception as e:
            self.error_handler.handle_error(
                component="video_playback",
                error_type="playback_start_failed",
                severity=ErrorSeverity.HIGH,
                message=f"Failed to start playback for {video_id}",
                exception=e,
                context={"video_id": video_id}
            )
            return False
    
    def stop_playback(self):
        """Stop current video playback."""
        self.is_playing = False
        
        self._cleanup_current_player()
            
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
            
        self.current_video = None
    
    def _playback_loop(self):
        """Main playback loop with looping support."""
        while self.is_playing and self.current_video:
            try:
                # Create new player instance
                preloaded = self.preloaded_videos[self.current_video]
                self.current_player = preloaded.create_player()
                
                frame_time = 1.0 / preloaded.fps
                
                if HAS_FFPYPLAYER:
                    self._playback_loop_ffpyplayer(preloaded, frame_time)
                else:
                    self._playback_loop_opencv(preloaded, frame_time)
                
                # Clean up player for restart
                self._cleanup_current_player()
                    
            except Exception as e:
                self.error_handler.handle_error(
                    component="video_playback",
                    error_type="playback_loop_error",
                    severity=ErrorSeverity.HIGH,
                    message="Video playback loop encountered error",
                    exception=e,
                    context={"current_video": self.current_video}
                )
                self.is_playing = False
    
    def _playback_loop_ffpyplayer(self, preloaded: PreloadedVideo, frame_time: float):
        """Playback loop using ffpyplayer."""
        while self.is_playing:
            frame, val = self.current_player.get_frame()
            
            if val == 'eof':
                if self.should_loop:
                    logger.debug(f"Looping video: {self.current_video}")
                    break  # Break inner loop to restart video
                else:
                    self.is_playing = False
                    break
            
            if frame is not None:
                img, t = frame
                
                # Convert to OpenCV format
                w, h = img.get_size()
                frame_array = np.frombuffer(img.to_bytearray()[0], dtype=np.uint8)
                frame_array = frame_array.reshape((h, w, 3))
                frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
                
                # Process strips (basic display for now)
                self._display_strips(frame_bgr, preloaded.strips)
            
            # Frame timing
            time.sleep(frame_time)
    
    def _playback_loop_opencv(self, preloaded: PreloadedVideo, frame_time: float):
        """Playback loop using OpenCV."""
        while self.is_playing:
            ret, frame = self.current_player.read()
            
            if not ret:
                if self.should_loop:
                    logger.debug(f"Looping video: {self.current_video}")
                    # Reset to beginning for loop
                    self.current_player.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    self.is_playing = False
                    break
            
            # Process strips (basic display for now)
            self._display_strips(frame, preloaded.strips)
            
            # Frame timing
            time.sleep(frame_time)
    
    def _cleanup_current_player(self):
        """Clean up current player regardless of type."""
        if self.current_player:
            if HAS_FFPYPLAYER and hasattr(self.current_player, 'close_player'):
                self.current_player.close_player()
            elif hasattr(self.current_player, 'release'):
                self.current_player.release()
            self.current_player = None
    
    def _display_strips(self, frame: np.ndarray, strips: List[VideoStrip]):
        """Display video strips with masking, crossfade, and overlays."""
        # Store current frame for potential crossfade
        self.last_frame = frame.copy()
        
        # Apply crossfade if active
        if self.crossfade_manager.is_active():
            frame = self.crossfade_manager.update_crossfade(frame)
        
        # Apply masks for projection (in final implementation)
        display_frame = self.mask_manager.apply_masks_to_frame(frame.copy())
        
        # Add editing overlay if in edit mode
        self.mask_manager.draw_edit_overlay(display_frame)
        
        # Add parameter adjustment UI if enabled
        self.parameter_ui.draw_ui(display_frame)
        
        # Add crossfade progress indicator
        if self.crossfade_manager.is_active():
            self._draw_crossfade_indicator(display_frame)
        
        cv2.imshow(self.window_name, display_frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key != 255:  # Key was pressed
            # Try parameter UI first
            if not self.parameter_ui.handle_keyboard_input(key):
                # Then mask manager
                if not self.mask_manager.handle_keyboard_event(key):
                    # Handle application-level keys
                    self._handle_application_keys(key)
    
    def _draw_crossfade_indicator(self, image: np.ndarray):
        """Draw crossfade progress indicator."""
        try:
            progress = self.crossfade_manager.get_progress()
            
            # Progress bar
            bar_width = 200
            bar_height = 10
            bar_x = image.shape[1] - bar_width - 20
            bar_y = 20
            
            # Background
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                         (40, 40, 40), -1)
            
            # Progress
            progress_width = int(bar_width * progress)
            cv2.rectangle(image, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), 
                         (100, 255, 100), -1)
            
            # Label
            cv2.putText(image, "Crossfade", (bar_x, bar_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
        except Exception as e:
            logger.error(f"Error drawing crossfade indicator: {e}")
    
    def _handle_application_keys(self, key: int):
        """Handle application-level keyboard commands."""
        key_char = chr(key & 0xFF).lower()
        
        if key_char == 'p':
            # Toggle parameter UI
            self.parameter_ui.toggle_ui()
        elif key_char == 'c':
            # Test crossfade
            if self.last_frame is not None:
                self.crossfade_manager.start_crossfade(self.last_frame.copy())
                logger.info("Manual crossfade triggered")
        elif key_char == 'i':
            # Show system info
            self._show_system_info()
    
    def _show_system_info(self):
        """Log current system information."""
        status = self.get_system_status()
        config_settings = self.config_manager.get_all_settings()
        
        logger.info("=== SYSTEM STATUS ===")
        logger.info(f"Video: {status['video_engine']['current_video']} ({status['video_engine']['current_state']})")
        logger.info(f"MQTT: {'Connected' if status['mqtt']['connected'] else 'Disconnected'}")
        logger.info(f"Crossfade: {config_settings['crossfade_duration_ms']}ms")
        logger.info(f"Buffer: {config_settings['state_change_buffer_ms']}ms")
        logger.info(f"Timeout: {config_settings['mqtt_timeout_seconds']}s")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.stop_playback()
            self.disconnect_mqtt()
            
            # Stop error monitoring
            if hasattr(self, 'error_handler'):
                self.error_handler.stop_monitoring()
            
            cv2.destroyAllWindows()
            logger.info("Video engine cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Don't use error handler during cleanup to avoid loops

# Test functions for Stage 1 verification
def test_video_engine():
    """Basic test of video engine functionality."""
    engine = VideoEngine()
    
    # Test media scanning
    media_folders = ['media/active', 'media/ambient']
    engine.preload_videos(media_folders)
    
    available_videos = engine.get_available_videos()
    print(f"Available videos: {available_videos}")
    
    if available_videos:
        # Test playback
        test_video = available_videos[0]
        print(f"Testing playback of: {test_video}")
        
        if engine.start_playback(test_video):
            print("Playback started successfully")
            print("Press any key to stop...")
            cv2.waitKey(0)
        else:
            print("Failed to start playback")
    
    engine.cleanup()

if __name__ == "__main__":
    test_video_engine()