import json
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from ..streams.base_stream import BaseStream
from ..streams.stream_factory import StreamFactory

logger = logging.getLogger(__name__)

class UniversalStreamManager:
    def __init__(self, config_path: str = "streamSource.json"):
        self.config_path = config_path
        self.streams: Dict[str, BaseStream] = {}
        self.frame_callbacks: Dict[str, Callable] = {}
        self.error_callbacks: Dict[str, Callable] = {}
        self.processing_fps = 2
        self.last_processing_time: Dict[str, float] = {}

        self.global_settings = {}
        self.stream_configs = []

    def load_config(self) -> bool:
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"Stream configuration file not found: {self.config_path}")
                return False

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            self.global_settings = config_data.get('global_settings', {})
            self.stream_configs = config_data.get('stream_sources', [])

            self.processing_fps = self.global_settings.get('processing_fps', 2)

            logger.info(f"Loaded {len(self.stream_configs)} stream configurations")
            return True

        except Exception as e:
            logger.error(f"Error loading stream configuration: {e}")
            return False

    def initialize_streams(self) -> Dict[str, bool]:
        results = {}

        for stream_config in self.stream_configs:
            if not stream_config.get('enabled', True):
                logger.info(f"Stream {stream_config['id']} is disabled, skipping")
                results[stream_config['id']] = False
                continue

            is_valid, error_msg = StreamFactory.validate_config(stream_config)
            if not is_valid:
                logger.error(f"Invalid configuration for stream {stream_config['id']}: {error_msg}")
                results[stream_config['id']] = False
                continue

            stream = StreamFactory.create_stream(stream_config)
            if stream:
                self.streams[stream.stream_id] = stream
                self.last_processing_time[stream.stream_id] = 0

                stream.set_error_callback(self._handle_stream_error)

                results[stream.stream_id] = True
                logger.info(f"Initialized stream: {stream.stream_id} ({stream.__class__.__name__})")
            else:
                results[stream_config['id']] = False

        return results

    def add_stream(self, stream_config: Dict[str, Any]) -> bool:
        is_valid, error_msg = StreamFactory.validate_config(stream_config)
        if not is_valid:
            logger.error(f"Invalid stream configuration: {error_msg}")
            return False

        if stream_config['id'] in self.streams:
            logger.warning(f"Stream {stream_config['id']} already exists")
            return False

        stream = StreamFactory.create_stream(stream_config)
        if stream:
            self.streams[stream.stream_id] = stream
            self.last_processing_time[stream.stream_id] = 0

            stream.set_error_callback(self._handle_stream_error)

            logger.info(f"Added stream: {stream.stream_id}")
            return True

        return False

    def remove_stream(self, stream_id: str) -> bool:
        if stream_id not in self.streams:
            logger.warning(f"Stream {stream_id} does not exist")
            return False

        self.streams[stream_id].stop_capture()
        del self.streams[stream_id]

        if stream_id in self.frame_callbacks:
            del self.frame_callbacks[stream_id]

        if stream_id in self.error_callbacks:
            del self.error_callbacks[stream_id]

        if stream_id in self.last_processing_time:
            del self.last_processing_time[stream_id]

        logger.info(f"Removed stream: {stream_id}")
        return True

    def start_stream(self, stream_id: str) -> bool:
        if stream_id not in self.streams:
            logger.error(f"Stream {stream_id} does not exist")
            return False

        return self.streams[stream_id].start_capture()

    def stop_stream(self, stream_id: str) -> bool:
        if stream_id not in self.streams:
            logger.error(f"Stream {stream_id} does not exist")
            return False

        self.streams[stream_id].stop_capture()
        return True

    def start_all_streams(self) -> Dict[str, bool]:
        results = {}
        for stream_id in self.streams:
            results[stream_id] = self.start_stream(stream_id)
        return results

    def stop_all_streams(self) -> None:
        for stream_id in self.streams:
            self.stop_stream(stream_id)

    def set_frame_callback(self, stream_id: str, callback: Callable) -> None:
        self.frame_callbacks[stream_id] = callback
        if stream_id in self.streams:
            self.streams[stream_id].set_frame_callback(callback)

    def set_error_callback(self, stream_id: str, callback: Callable) -> None:
        self.error_callbacks[stream_id] = callback

    def set_processing_fps(self, fps: int) -> None:
        self.processing_fps = max(1, fps)
        logger.info(f"Set processing FPS to: {self.processing_fps}")

    def process_frames(self) -> None:
        current_time = time.time()

        for stream_id, stream in self.streams.items():
            if not stream.is_running:
                continue

            time_since_last = current_time - self.last_processing_time[stream_id]
            if time_since_last < (1.0 / self.processing_fps):
                continue

            stream_frame = stream.get_latest_frame()
            if stream_frame is None:
                continue

            if stream_id in self.frame_callbacks:
                try:
                    self.frame_callbacks[stream_id](
                        stream_id,
                        stream_frame.frame,
                        stream_frame.timestamp
                    )
                except Exception as e:
                    logger.error(f"Error in frame callback for {stream_id}: {e}")

            self.last_processing_time[stream_id] = current_time

    def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        if stream_id not in self.streams:
            return None
        return self.streams[stream_id].get_status()

    def get_all_streams_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            stream_id: stream.get_status()
            for stream_id, stream in self.streams.items()
        }

    def get_stream_info(self, stream_id: str) -> Optional[Dict[str, Any]]:
        if stream_id not in self.streams:
            return None
        return self.streams[stream_id].get_stream_info()

    def get_all_streams_info(self) -> List[Dict[str, Any]]:
        return [
            stream.get_stream_info()
            for stream in self.streams.values()
        ]

    def get_supported_stream_types(self) -> Dict[str, str]:
        return StreamFactory.get_supported_types()

    def reload_config(self) -> bool:
        try:
            self.stop_all_streams()
            self.streams.clear()
            self.frame_callbacks.clear()
            self.error_callbacks.clear()
            self.last_processing_time.clear()

            if self.load_config():
                results = self.initialize_streams()
                success_count = sum(1 for success in results.values() if success)
                logger.info(f"Reloaded configuration: {success_count}/{len(results)} streams initialized")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            return False

    def _handle_stream_error(self, stream_id: str, error: str) -> None:
        logger.error(f"Stream error for {stream_id}: {error}")

        if stream_id in self.error_callbacks:
            try:
                self.error_callbacks[stream_id](stream_id, error)
            except Exception as e:
                logger.error(f"Error in error callback for {stream_id}: {e}")

    def cleanup(self) -> None:
        logger.info("Cleaning up Universal Stream Manager")
        self.stop_all_streams()
        self.streams.clear()
        self.frame_callbacks.clear()
        self.error_callbacks.clear()
        self.last_processing_time.clear()

    def get_statistics(self) -> Dict[str, Any]:
        running_streams = sum(1 for stream in self.streams.values() if stream.is_running)
        connected_streams = sum(1 for stream in self.streams.values() if stream.is_connected)

        stream_types = {}
        for stream in self.streams.values():
            stream_type = stream.__class__.__name__
            stream_types[stream_type] = stream_types.get(stream_type, 0) + 1

        return {
            'total_streams': len(self.streams),
            'running_streams': running_streams,
            'connected_streams': connected_streams,
            'processing_fps': self.processing_fps,
            'stream_types': stream_types,
            'supported_types': self.get_supported_stream_types()
        }