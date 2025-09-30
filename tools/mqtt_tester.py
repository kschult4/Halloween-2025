#!/usr/bin/env python3
"""
MQTT Tester for Halloween Projection Mapper
Simulates controller MQTT messages for testing projection system.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
import json
import threading
from mqtt_handler import MQTTSimulator

class MQTTTester:
    """Interactive MQTT testing tool."""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.simulator = MQTTSimulator(broker_host, broker_port)
        self.is_connected = False
    
    def connect(self) -> bool:
        """Connect to MQTT broker."""
        print(f"Connecting to MQTT broker at {self.simulator.broker_host}:{self.simulator.broker_port}...")
        self.is_connected = self.simulator.connect()
        
        if self.is_connected:
            print("✅ Connected to MQTT broker")
        else:
            print("❌ Failed to connect to MQTT broker")
            print("Make sure broker is running: mosquitto -v")
        
        return self.is_connected
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.is_connected:
            self.simulator.disconnect()
            self.is_connected = False
            print("Disconnected from MQTT broker")
    
    def send_message(self, state: str, media: str = None):
        """Send a message to the projection system."""
        if not self.is_connected:
            print("❌ Not connected to MQTT broker")
            return False
        
        success = self.simulator.send_message(state, media)
        if success:
            print(f"📤 Sent: state={state}, media={media}")
        else:
            print(f"❌ Failed to send message")
        
        return success
    
    def run_motion_sequence(self):
        """Simulate a motion detection sequence."""
        print("\n🎬 Running motion detection sequence...")
        
        # Motion detected
        self.send_message("active", "active_01")
        time.sleep(3)
        
        # Motion stops
        self.send_message("ambient", "ambient_01")
        
        print("Motion sequence complete")
    
    def run_interactive_mode(self):
        """Run interactive command interface."""
        print("\n" + "=" * 50)
        print("MQTT TESTER - Interactive Mode")
        print("=" * 50)
        print("Commands:")
        print("  1 or a - Send active message")
        print("  2 or b - Send ambient message")
        print("  m - Run motion sequence")
        print("  s - Show status")
        print("  q - Quit")
        print("")
        
        while True:
            try:
                cmd = input("Command: ").lower().strip()
                
                if cmd in ['q', 'quit', 'exit']:
                    break
                
                elif cmd in ['1', 'a', 'active']:
                    media = input("Media ID (or Enter for active_01): ").strip()
                    if not media:
                        media = "active_01"
                    self.send_message("active", media)
                
                elif cmd in ['2', 'b', 'ambient']:
                    media = input("Media ID (or Enter for ambient_01): ").strip()
                    if not media:
                        media = "ambient_01"
                    self.send_message("ambient", media)
                
                elif cmd == 'm':
                    self.run_motion_sequence()
                
                elif cmd == 's':
                    self.show_status()
                
                elif cmd == 'help':
                    print("Commands: 1/a (active), 2/b (ambient), m (motion), s (status), q (quit)")
                
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for commands.")
            
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        print("\nExiting interactive mode...")
    
    def show_status(self):
        """Show current tester status."""
        print(f"MQTT Tester Status:")
        print(f"  Broker: {self.simulator.broker_host}:{self.simulator.broker_port}")
        print(f"  Topic: {self.simulator.topic}")
        print(f"  Connected: {self.is_connected}")
    
    def run_automated_demo(self):
        """Run automated demo sequence."""
        print("\n🎭 Running automated demo sequence...")
        
        sequences = [
            ("ambient", "ambient_01", 2),
            ("active", "active_01", 3),
            ("ambient", "ambient_01", 2),
            ("active", "active_02", 3),
            ("ambient", None, 2),
        ]
        
        for i, (state, media, duration) in enumerate(sequences, 1):
            print(f"\nStep {i}/{len(sequences)}: {state} / {media} for {duration}s")
            self.send_message(state, media)
            time.sleep(duration)
        
        print("\n✅ Automated demo complete")

def main():
    """Main MQTT tester application."""
    print("Halloween Projection Mapper - MQTT Tester")
    print("=" * 50)
    
    # Parse command line arguments
    broker_host = "localhost"
    broker_port = 1883
    
    if len(sys.argv) > 1:
        broker_host = sys.argv[1]
    if len(sys.argv) > 2:
        broker_port = int(sys.argv[2])
    
    # Create tester
    tester = MQTTTester(broker_host, broker_port)
    
    try:
        # Connect to broker
        if not tester.connect():
            print("\nTroubleshooting:")
            print("1. Install MQTT broker: brew install mosquitto  # macOS")
            print("2. Start broker: mosquitto -v")
            print("3. Or use public broker: python mqtt_tester.py test.mosquitto.org")
            return
        
        # Show initial status
        tester.show_status()
        
        # Choose mode
        print("\nSelect mode:")
        print("1. Interactive mode (manual commands)")
        print("2. Automated demo")
        print("3. Single motion sequence")
        
        try:
            choice = input("\nChoice (1-3): ").strip()
        except EOFError:
            choice = "2"  # Default for non-interactive environments
        
        if choice == "1":
            tester.run_interactive_mode()
        elif choice == "2":
            tester.run_automated_demo()
        elif choice == "3":
            tester.run_motion_sequence()
        else:
            print("Invalid choice, running automated demo...")
            tester.run_automated_demo()
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        tester.disconnect()
        print("MQTT tester finished")

if __name__ == "__main__":
    main()
