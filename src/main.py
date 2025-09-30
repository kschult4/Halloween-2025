#!/usr/bin/env python3
"""
Halloween Projection Mapper - Main Application
Entry point for the complete projection mapping system.
"""
import sys
import os
import time
import logging
import argparse
from typing import Optional
import cv2

# Add src directory to path for imports
sys.path.append(os.path.dirname(__file__))

from video_engine import VideoEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HalloweenProjectionMapper:
    """Main application class for Halloween Projection Mapper."""
    
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.engine: Optional[VideoEngine] = None
        self.is_running = False
        self.headless = False
        self._connect_mqtt = True
        
    def initialize(self, *, connect_mqtt: bool = True, allow_empty_media: bool = False,
                   headless: bool = False) -> bool:
        """Initialize the projection system."""
        try:
            logger.info("Initializing Halloween Projection Mapper...")
            self.headless = headless
            self._connect_mqtt = connect_mqtt
            
            # Create video engine
            self.engine = VideoEngine(
                mqtt_broker=self.mqtt_broker,
                mqtt_port=self.mqtt_port,
                headless=headless
            )
            
            # Preload videos
            media_folders = ['media/active', 'media/ambient']
            self.engine.preload_videos(media_folders)
            
            available_videos = self.engine.get_available_videos()
            if not available_videos:
                message = "No videos found in media folders"
                logger.warning(f"{message}!")
                logger.info("Add MP4 files to media/active/ and media/ambient/")
                if not allow_empty_media:
                    return False
                if not headless:
                    self.engine.start_idle_display(
                        "Add MP4 videos to media/active or media/ambient"
                    )
            
            logger.info(f"Loaded {len(available_videos)} videos: {available_videos}")
            
            # Connect to MQTT broker
            if connect_mqtt:
                mqtt_connected = self.engine.connect_mqtt()
                if mqtt_connected:
                    logger.info("MQTT connection established - ready for controller commands")
                else:
                    logger.warning("MQTT connection failed - running in standalone mode")
            else:
                logger.info("Skipping MQTT connection (demo/status mode)")
            
            # Start with ambient video
            if not headless and self.engine.fallback_ambient_video:
                self.engine.start_playback(self.engine.fallback_ambient_video)
                logger.info(f"Started ambient playback: {self.engine.fallback_ambient_video}")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def run(self):
        """Run the main application loop."""
        if not self.engine:
            logger.error("Engine not initialized")
            return

        if self.engine.headless:
            logger.info("Headless mode active — skipping interactive run loop")
            return
        
        logger.info("Halloween Projection Mapper running...")
        logger.info("Controls:")
        logger.info("  E - Toggle edit mode for mask adjustment")
        logger.info("  S - Save mask configuration (in edit mode)")
        logger.info("  R - Reset masks to defaults (in edit mode)")
        logger.info("  P - Toggle parameter UI | C - Test crossfade | I - Info")
        logger.info("  ESC/Q - Exit application")
        
        self.is_running = True
        
        try:
            while self.is_running:
                # Input is handled inside VideoEngine's rendering thread
                # Here we only watch for exit signals and window closure
                if getattr(self.engine, 'exit_requested', False):
                    logger.info("Exit requested by engine")
                    break

                if cv2.getWindowProperty(self.engine.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    logger.info("Window closed")
                    break

                time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        
        if self.engine:
            self.engine.cleanup()
            self.engine = None
        
        if not self.headless:
            cv2.destroyAllWindows()
        self.is_running = False
        logger.info("Cleanup complete")
    
    def get_status(self):
        """Get current system status."""
        if self.engine:
            return self.engine.get_system_status()
        return {"error": "Engine not initialized"}

def setup_arg_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Halloween Projection Mapper - Interactive projection system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run with default MQTT broker (localhost)
  python main.py --broker 192.168.1.100  # Use specific MQTT broker
  python main.py --demo                   # Run with MQTT simulator
  python main.py --status                 # Show status and exit
        """
    )
    
    parser.add_argument(
        '--broker', 
        default='localhost',
        help='MQTT broker hostname or IP (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=1883,
        help='MQTT broker port (default: 1883)'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run with MQTT simulator for testing'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show system status and exit'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser

def run_demo_mode(app: HalloweenProjectionMapper):
    """Run application in demo mode with simulated MQTT messages."""
    if not app.engine:
        logger.error("Demo mode requested before initialization")
        return

    logger.info("Starting demo mode with internal MQTT simulation")

    import threading

    def demo_sequence():
        time.sleep(3)  # Let system start up

        demo_messages = [
            ("ambient", "ambient_01", 3),
            ("active", "active_01", 4),
            ("ambient", None, 2),
            ("active", "active_02", 3),
            ("ambient", "ambient_01", 5),
        ]

        for state, media, duration in demo_messages:
            if not app.is_running:
                break

            logger.info(f"Demo: {state} / {media} for {duration}s")
            app.engine.simulate_state_change(state, media)
            time.sleep(duration)

        logger.info("Demo sequence complete")

    demo_thread = threading.Thread(target=demo_sequence, daemon=True)
    demo_thread.start()

    # Run normal application
    app.run()

def main():
    """Main application entry point."""
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create application
    app = HalloweenProjectionMapper(mqtt_broker=args.broker, mqtt_port=args.port)

    try:
        # Initialize system
        init_success = app.initialize(
            connect_mqtt=not args.demo and not args.status,
            allow_empty_media=True,
            headless=args.status
        )
        if not init_success:
            logger.error("Failed to initialize system")
            return 1
        
        # Handle status request
        if args.status:
            status = app.get_status()
            import json
            print(json.dumps(status, indent=2))
            return 0

        # Run application
        if args.demo:
            run_demo_mode(app)
        else:
            app.run()
        
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    
    finally:
        app.cleanup()

if __name__ == "__main__":
    sys.exit(main())
