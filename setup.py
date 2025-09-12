#!/usr/bin/env python3
"""
Setup script for Halloween Projection Mapper
Handles dependency installation and initial configuration.
"""
import os
import sys
import subprocess

def check_python_version():
    """Ensure Python 3.7+ is being used."""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        return False
    print(f"Python version: {sys.version}")
    return True

def install_dependencies():
    """Install required Python packages."""
    print("Installing Python dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def create_media_folders():
    """Create required media folder structure."""
    folders = [
        "media/active",
        "media/ambient", 
        "config",
        "tools",
        "tests"
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"Created folder: {folder}")

def create_default_configs():
    """Create default configuration files."""
    
    # Default settings
    settings_content = """{
    "crossfade_duration_ms": 200,
    "state_change_buffer_ms": 0,
    "mqtt_timeout_seconds": 60,
    "video_preload_seconds": 2.0
}"""
    settings_path = "config/settings.json"
    if not os.path.exists(settings_path):
        with open(settings_path, "w") as f:
            f.write(settings_content)
        print("Created config/settings.json")
    else:
        print("config/settings.json already exists — leaving it unchanged")
    
    # Default masks (used as initial template; preserved if already present)
    masks_content = """{
    "strips": [
        {"corners": [[0, 0], [1920, 0], [1920, 180], [0, 180]]},
        {"corners": [[0, 180], [1920, 180], [1920, 360], [0, 360]]},
        {"corners": [[0, 360], [1920, 360], [1920, 540], [0, 540]]},
        {"corners": [[0, 540], [1920, 540], [1920, 720], [0, 720]]},
        {"corners": [[0, 720], [1920, 720], [1920, 900], [0, 900]]},
        {"corners": [[0, 900], [1920, 900], [1920, 1080], [0, 1080]]}
    ]
}"""
    masks_path = "config/masks.json"
    if not os.path.exists(masks_path):
        with open(masks_path, "w") as f:
            f.write(masks_content)
        print("Created config/masks.json")
    else:
        print("config/masks.json already exists — leaving it unchanged")

def print_pi_setup_instructions():
    """Print Raspberry Pi specific setup instructions."""
    print("\n" + "="*60)
    print("RASPBERRY PI SETUP INSTRUCTIONS")
    print("="*60)
    print("""
For optimal performance on Raspberry Pi 4, add these lines to /boot/config.txt:

    gpu_mem=128
    dtoverlay=vc4-kms-v3d
    max_framebuffers=2

Then reboot your Pi.

To enable hardware H.264 decoding, ensure these packages are installed:
    sudo apt update
    sudo apt install python3-opencv
    sudo apt install libavcodec-dev libavformat-dev libswscale-dev

For auto-start on boot, create a systemd service:
    sudo cp systemd/halloween-projection.service /etc/systemd/system/
    sudo systemctl enable halloween-projection.service
""")

def main():
    """Run complete setup process."""
    print("Halloween Projection Mapper - Setup")
    print("="*40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create folder structure
    create_media_folders()
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create default configs
    create_default_configs()
    
    # Print Pi-specific instructions
    print_pi_setup_instructions()
    
    print("\n✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Copy your MP4 videos to media/active/ and media/ambient/")
    print("2. Run: python tests/test_stage1.py")
    print("3. If on Raspberry Pi, follow the setup instructions above")
    
    return True

if __name__ == "__main__":
    main()
