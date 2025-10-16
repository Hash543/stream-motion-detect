#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for all streaming formats
"""

import sys
import os
import time
import logging
from pathlib import Path

# Set encoding
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.managers.universal_stream_manager import UniversalStreamManager

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_stream_manager():
    """Test the stream manager"""
    print("=== Testing Universal Stream Manager ===")

    stream_manager = UniversalStreamManager("streamSource.json")

    print("\n1. Loading stream configuration...")
    if stream_manager.load_config():
        print("OK Successfully loaded configuration")
        print(f"  - Global settings: {stream_manager.global_settings}")
        print(f"  - Stream count: {len(stream_manager.stream_configs)}")

        for config in stream_manager.stream_configs:
            enabled = "ENABLED" if config.get('enabled', True) else "DISABLED"
            print(f"  {enabled} {config['id']} ({config['type']}) - {config['name']}")
    else:
        print("FAIL Failed to load configuration")
        return False

    print("\n2. Initializing streams...")
    results = stream_manager.initialize_streams()

    success_count = 0
    for stream_id, success in results.items():
        status = "OK" if success else "FAIL"
        print(f"  {status} {stream_id}")
        if success:
            success_count += 1

    print(f"\nInitialization result: {success_count}/{len(results)} successful")

    print("\n3. Getting supported stream types...")
    supported_types = stream_manager.get_supported_stream_types()
    for stream_type, description in supported_types.items():
        print(f"  * {stream_type}: {description}")

    print("\n4. Testing stream startup...")
    if stream_manager.streams:
        start_results = stream_manager.start_all_streams()

        for stream_id, success in start_results.items():
            status = "OK" if success else "FAIL"
            print(f"  {status} Starting {stream_id}")

        print("\n5. Waiting for stream data...")
        time.sleep(3)

        print("\n6. Checking stream status...")
        all_status = stream_manager.get_all_streams_status()

        for stream_id, status in all_status.items():
            running = "Running" if status['is_running'] else "Stopped"
            connected = "Connected" if status['is_connected'] else "Disconnected"
            queue_size = status.get('queue_size', 0)

            print(f"  * {stream_id}: {running}, {connected}, Queue: {queue_size}")

            if status.get('last_error'):
                print(f"    Error: {status['last_error']}")

        print("\n7. System statistics...")
        stats = stream_manager.get_statistics()
        print(f"  * Total streams: {stats['total_streams']}")
        print(f"  * Running: {stats['running_streams']}")
        print(f"  * Connected: {stats['connected_streams']}")
        print(f"  * Processing FPS: {stats['processing_fps']}")

        if stats['stream_types']:
            print("  * Stream type distribution:")
            for stream_type, count in stats['stream_types'].items():
                print(f"    - {stream_type}: {count}")

        print("\n8. Stopping streams...")
        stream_manager.stop_all_streams()
        print("OK All streams stopped")

    else:
        print("No streams available for testing")

    stream_manager.cleanup()
    return True

def test_individual_streams():
    """Test individual stream types"""
    print("\n=== Testing Individual Stream Types ===")

    # Test local webcam
    print("\nTesting local webcam...")
    from src.streams.http_stream import WebcamStream

    webcam_config = {
        'device_index': 0,
        'resolution': {'width': 640, 'height': 480},
        'fps': 30,
        'max_reconnect_attempts': 2,
        'reconnect_delay': 1
    }

    webcam = WebcamStream("test_webcam", "Test Camera", "Local", webcam_config)

    try:
        if webcam.connect():
            print("OK Local webcam connected successfully")

            if webcam.start_capture():
                print("OK Started frame capture")
                time.sleep(2)

                frame_data = webcam.get_latest_frame()
                if frame_data:
                    print(f"OK Successfully got frame: {frame_data.frame.shape}")
                else:
                    print("FAIL Could not get frame")

                webcam.stop_capture()
                print("OK Stopped capture")
            else:
                print("FAIL Could not start capture")
        else:
            print("FAIL Local webcam connection failed")
    except Exception as e:
        print(f"FAIL Webcam test error: {e}")

def main():
    """Main function"""
    print("Starting stream system test...")

    try:
        # Check if configuration file exists
        if not os.path.exists("streamSource.json"):
            print("ERROR: streamSource.json configuration file not found")
            return 1

        # Test stream manager
        if not test_stream_manager():
            print("Stream manager test failed")
            return 1

        # Test individual streams
        test_individual_streams()

        print("\n=== Test Complete ===")
        print("All tests completed. Check the output above for stream format status.")

        return 0

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)