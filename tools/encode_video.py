#!/usr/bin/env python3
"""
Video Encoding Helper for Halloween Projection Mapper
Converts uploaded videos to Pi-optimized H.264 format for hardware acceleration.
"""
import os
import sys
import argparse
import subprocess
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoEncoder:
    """Pi-optimized video encoder using FFmpeg."""
    
    def __init__(self):
        self.target_specs = {
            "codec": "libx264",
            "resolution": "1920x1080",
            "fps": 30,
            "profile": "high",
            "level": "4.0",
            "preset": "medium",
            "crf": 23,  # Constant Rate Factor for quality
            "format": "mp4",
            "audio": False,  # No audio for projection
        }
        
        # Check FFmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("FFmpeg found and available")
                return True
            else:
                logger.error("FFmpeg not working properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.error("FFmpeg not found. Install with: sudo apt install ffmpeg")
            return False
    
    def get_video_info(self, input_path: str) -> Optional[dict]:
        """Get video information using FFprobe."""
        if not self.ffmpeg_available:
            return None
        
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"FFprobe failed: {result.stderr}")
                return None
            
            info = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                logger.error("No video stream found")
                return None
            
            # Parse video info
            video_info = {
                'duration': float(info.get('format', {}).get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': self._parse_fps(video_stream.get('r_frame_rate', '0/1')),
                'codec': video_stream.get('codec_name', 'unknown'),
                'bitrate': int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else 0,
                'format': info.get('format', {}).get('format_name', 'unknown')
            }
            
            return video_info
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def _parse_fps(self, fps_string: str) -> float:
        """Parse FPS from FFprobe format (e.g., '30/1')."""
        try:
            if '/' in fps_string:
                num, denom = fps_string.split('/')
                return float(num) / float(denom)
            return float(fps_string)
        except (ValueError, ZeroDivisionError):
            return 30.0  # Default
    
    def needs_encoding(self, input_path: str) -> Tuple[bool, str]:
        """Check if video needs encoding for Pi optimization."""
        info = self.get_video_info(input_path)
        if not info:
            return True, "Could not analyze video"
        
        issues = []
        
        # Check resolution
        if info['width'] != 1920 or info['height'] != 1080:
            issues.append(f"Resolution {info['width']}x{info['height']} (need 1920x1080)")
        
        # Check codec
        if info['codec'] != 'h264':
            issues.append(f"Codec {info['codec']} (need h264)")
        
        # Check FPS
        if abs(info['fps'] - 30.0) > 1.0:
            issues.append(f"FPS {info['fps']:.1f} (prefer 30fps)")
        
        # Check format
        if 'mp4' not in info['format'].lower():
            issues.append(f"Format {info['format']} (need MP4)")
        
        if issues:
            return True, "; ".join(issues)
        else:
            return False, "Already Pi-optimized"
    
    def encode_video(self, input_path: str, output_path: str, 
                    progress_callback: Optional[callable] = None) -> bool:
        """Encode video to Pi-optimized format."""
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        
        try:
            # Get input info for progress tracking
            input_info = self.get_video_info(input_path)
            duration = input_info.get('duration', 0) if input_info else 0
            
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command(input_path, output_path)
            
            logger.info(f"Encoding: {os.path.basename(input_path)}")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Run FFmpeg with progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            progress = 0.0
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # Parse FFmpeg progress
                    if 'time=' in output:
                        progress = self._parse_ffmpeg_progress(output, duration)
                        if progress_callback:
                            progress_callback(progress)
            
            # Check result
            return_code = process.poll()
            if return_code == 0:
                logger.info(f"Encoding completed: {os.path.basename(output_path)}")
                return True
            else:
                stderr = process.stderr.read()
                logger.error(f"Encoding failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Encoding error: {e}")
            return False
    
    def _build_ffmpeg_command(self, input_path: str, output_path: str) -> List[str]:
        """Build FFmpeg command for Pi optimization."""
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-y',  # Overwrite output
            '-c:v', self.target_specs['codec'],
            '-profile:v', self.target_specs['profile'],
            '-level:v', self.target_specs['level'],
            '-preset', self.target_specs['preset'],
            '-crf', str(self.target_specs['crf']),
            '-s', self.target_specs['resolution'],
            '-r', str(self.target_specs['fps']),
            '-pix_fmt', 'yuv420p',  # Pi-compatible pixel format
            '-movflags', '+faststart',  # Optimize for streaming
            '-an',  # No audio
            '-f', self.target_specs['format'],
            output_path
        ]
        
        return cmd
    
    def _parse_ffmpeg_progress(self, output_line: str, total_duration: float) -> float:
        """Parse progress from FFmpeg output."""
        try:
            if 'time=' in output_line:
                # Extract time=HH:MM:SS.ss
                time_part = output_line.split('time=')[1].split()[0]
                
                # Parse time format
                if ':' in time_part:
                    parts = time_part.split(':')
                    if len(parts) == 3:
                        hours = float(parts[0])
                        minutes = float(parts[1])
                        seconds = float(parts[2])
                        current_time = hours * 3600 + minutes * 60 + seconds
                        
                        if total_duration > 0:
                            progress = min(100.0, (current_time / total_duration) * 100)
                            return progress
            
            return 0.0
            
        except (ValueError, IndexError):
            return 0.0

class VideoBatchProcessor:
    """Batch processor for multiple video files."""
    
    def __init__(self, media_dir: str = "media"):
        self.media_dir = Path(media_dir)
        self.encoder = VideoEncoder()
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    def scan_for_videos(self) -> List[Path]:
        """Scan media directory for video files."""
        videos = []
        
        for folder in ['active', 'ambient']:
            folder_path = self.media_dir / folder
            if folder_path.exists():
                for file_path in folder_path.iterdir():
                    if file_path.suffix.lower() in self.supported_formats:
                        videos.append(file_path)
        
        return videos
    
    def process_batch(self, videos: List[Path], keep_originals: bool = True) -> dict:
        """Process a batch of videos."""
        results = {
            'processed': [],
            'skipped': [],
            'failed': [],
            'total': len(videos)
        }
        
        for i, video_path in enumerate(videos, 1):
            logger.info(f"\n=== Processing {i}/{len(videos)}: {video_path.name} ===")
            
            # Check if encoding needed
            needs_encoding, reason = self.encoder.needs_encoding(str(video_path))
            
            if not needs_encoding:
                logger.info(f"Skipping: {reason}")
                results['skipped'].append(str(video_path))
                continue
            
            logger.info(f"Encoding needed: {reason}")
            
            # Determine output path
            if keep_originals:
                # Create encoded version alongside original
                output_path = video_path.with_suffix('.encoded.mp4')
            else:
                # Create backup and replace
                backup_path = video_path.with_suffix(f'{video_path.suffix}.backup')
                shutil.move(str(video_path), str(backup_path))
                output_path = video_path.with_suffix('.mp4')
            
            # Encode video
            def progress_cb(progress):
                print(f"\rEncoding progress: {progress:.1f}%", end='', flush=True)
            
            success = self.encoder.encode_video(str(video_path), str(output_path), progress_cb)
            print()  # New line after progress
            
            if success:
                logger.info(f"Successfully encoded: {output_path.name}")
                results['processed'].append(str(output_path))
                
                # Verify output
                if not output_path.exists() or output_path.stat().st_size == 0:
                    logger.error(f"Output file is empty or missing: {output_path}")
                    results['failed'].append(str(video_path))
                    
            else:
                logger.error(f"Failed to encode: {video_path.name}")
                results['failed'].append(str(video_path))
                
                # Restore backup if we moved original
                if not keep_originals:
                    backup_path = video_path.with_suffix(f'{video_path.suffix}.backup')
                    if backup_path.exists():
                        shutil.move(str(backup_path), str(video_path))
        
        return results

def print_video_info(video_path: str):
    """Print detailed video information."""
    encoder = VideoEncoder()
    info = encoder.get_video_info(video_path)
    
    if not info:
        print(f"❌ Could not analyze: {video_path}")
        return
    
    print(f"\n📹 Video Information: {os.path.basename(video_path)}")
    print(f"   Resolution: {info['width']}x{info['height']}")
    print(f"   Duration: {info['duration']:.1f} seconds")
    print(f"   FPS: {info['fps']:.1f}")
    print(f"   Codec: {info['codec']}")
    print(f"   Format: {info['format']}")
    print(f"   Bitrate: {info['bitrate']} bps" if info['bitrate'] else "   Bitrate: Unknown")
    
    # Check optimization status
    needs_encoding, reason = encoder.needs_encoding(video_path)
    if needs_encoding:
        print(f"   Status: ⚠️  Needs encoding ({reason})")
    else:
        print(f"   Status: ✅ Pi-optimized")

def setup_arg_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Halloween Projection Mapper - Video Encoding Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python encode_video.py --scan                    # Scan media folder
  python encode_video.py --info video.mp4         # Show video info
  python encode_video.py --encode video.mp4       # Encode single video
  python encode_video.py --batch                  # Encode all videos
  python encode_video.py --batch --replace        # Encode and replace originals
        """
    )
    
    parser.add_argument(
        '--scan',
        action='store_true',
        help='Scan media folder for videos and show status'
    )
    
    parser.add_argument(
        '--info',
        metavar='VIDEO',
        help='Show detailed information about a video file'
    )
    
    parser.add_argument(
        '--encode',
        metavar='VIDEO',
        help='Encode a single video file'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch encode all videos in media folder'
    )
    
    parser.add_argument(
        '--output',
        metavar='PATH',
        help='Output path for encoded video (default: add .encoded.mp4)'
    )
    
    parser.add_argument(
        '--replace',
        action='store_true',
        help='Replace original files (creates .backup copies)'
    )
    
    parser.add_argument(
        '--media-dir',
        default='media',
        help='Media directory path (default: media)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser

def main():
    """Main application entry point."""
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize encoder
    encoder = VideoEncoder()
    if not encoder.ffmpeg_available:
        print("❌ FFmpeg is required but not available.")
        print("Install with: sudo apt install ffmpeg")
        return 1
    
    try:
        # Handle different modes
        if args.scan:
            # Scan media folder
            processor = VideoBatchProcessor(args.media_dir)
            videos = processor.scan_for_videos()
            
            if not videos:
                print(f"No videos found in {args.media_dir}/")
                return 0
            
            print(f"Found {len(videos)} videos in {args.media_dir}/:")
            
            for video_path in videos:
                needs_encoding, reason = encoder.needs_encoding(str(video_path))
                status = "⚠️  Needs encoding" if needs_encoding else "✅ Ready"
                print(f"  {video_path.relative_to(args.media_dir)}: {status}")
                if needs_encoding:
                    print(f"    └─ {reason}")
        
        elif args.info:
            # Show video info
            if not os.path.exists(args.info):
                print(f"❌ File not found: {args.info}")
                return 1
            
            print_video_info(args.info)
        
        elif args.encode:
            # Encode single video
            if not os.path.exists(args.encode):
                print(f"❌ File not found: {args.encode}")
                return 1
            
            # Determine output path
            input_path = Path(args.encode)
            if args.output:
                output_path = args.output
            elif args.replace:
                backup_path = input_path.with_suffix(f'{input_path.suffix}.backup')
                shutil.copy2(str(input_path), str(backup_path))
                output_path = str(input_path.with_suffix('.mp4'))
                print(f"Created backup: {backup_path.name}")
            else:
                output_path = str(input_path.with_suffix('.encoded.mp4'))
            
            print(f"Encoding: {input_path.name} → {Path(output_path).name}")
            
            def progress_cb(progress):
                print(f"\rProgress: {progress:.1f}%", end='', flush=True)
            
            success = encoder.encode_video(str(input_path), output_path, progress_cb)
            print()  # New line
            
            if success:
                print(f"✅ Encoding completed: {Path(output_path).name}")
                return 0
            else:
                print(f"❌ Encoding failed")
                return 1
        
        elif args.batch:
            # Batch process
            processor = VideoBatchProcessor(args.media_dir)
            videos = processor.scan_for_videos()
            
            if not videos:
                print(f"No videos found in {args.media_dir}/")
                return 0
            
            print(f"Found {len(videos)} videos for batch processing")
            
            results = processor.process_batch(videos, keep_originals=not args.replace)
            
            # Print summary
            print(f"\n=== Batch Processing Complete ===")
            print(f"Total videos: {results['total']}")
            print(f"Processed: {len(results['processed'])}")
            print(f"Skipped: {len(results['skipped'])}")
            print(f"Failed: {len(results['failed'])}")
            
            if results['failed']:
                print(f"\nFailed videos:")
                for failed in results['failed']:
                    print(f"  ❌ {failed}")
                return 1
        
        else:
            # No action specified
            parser.print_help()
            return 0
            
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())