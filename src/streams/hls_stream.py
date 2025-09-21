import cv2
import time
import requests
import threading
import os
import tempfile
import numpy as np
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import logging
from .base_stream import BaseStream

logger = logging.getLogger(__name__)

try:
    import m3u8
    HLS_AVAILABLE = True
except ImportError:
    HLS_AVAILABLE = False
    logger.warning("HLS support requires m3u8 library. Install with: pip install m3u8")

class HLSStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        if not HLS_AVAILABLE:
            raise ImportError("HLS support requires m3u8 library")

        self.playlist_url = config['url']
        self.timeout = config.get('timeout', 30)
        self.buffer_segments = config.get('buffer_segments', 3)
        self.headers = config.get('headers', {})

        self.session: Optional[requests.Session] = None
        self.playlist: Optional[object] = None
        self.segment_urls: List[str] = []
        self.current_segment_index = 0
        self.temp_dir: Optional[str] = None

    def connect(self) -> bool:
        try:
            if self.session:
                self.session.close()

            self.session = requests.Session()
            if self.headers:
                self.session.headers.update(self.headers)

            self.temp_dir = tempfile.mkdtemp(prefix="hls_stream_")

            response = self.session.get(self.playlist_url, timeout=self.timeout)
            response.raise_for_status()

            self.playlist = m3u8.loads(response.text)

            if not self.playlist.segments:
                if self.playlist.playlists:
                    best_playlist = max(self.playlist.playlists,
                                      key=lambda p: p.stream_info.bandwidth if p.stream_info else 0)
                    playlist_url = urljoin(self.playlist_url, best_playlist.uri)

                    response = self.session.get(playlist_url, timeout=self.timeout)
                    response.raise_for_status()
                    self.playlist = m3u8.loads(response.text)

            if not self.playlist.segments:
                raise Exception("No segments found in HLS playlist")

            self._update_segment_urls()

            self.is_connected = True
            self.reconnect_count = 0
            self.last_error = None

            logger.info(f"Successfully connected to HLS stream: {self.stream_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to HLS stream: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        self.is_connected = False

        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except:
                pass
            self.temp_dir = None

    def _update_segment_urls(self) -> None:
        base_url = self.playlist_url.rsplit('/', 1)[0] + '/'
        self.segment_urls = [
            urljoin(base_url, segment.uri) for segment in self.playlist.segments
        ]

    def _capture_loop(self) -> None:
        while self.is_running:
            try:
                if not self.is_connected:
                    if not self._reconnect():
                        break
                    continue

                self._process_segments()

            except Exception as e:
                self._handle_error(f"Error in HLS capture loop: {e}")
                if not self._reconnect():
                    break

    def _process_segments(self) -> None:
        while self.is_running and self.current_segment_index < len(self.segment_urls):
            segment_url = self.segment_urls[self.current_segment_index]

            try:
                self._download_and_process_segment(segment_url)
                self.current_segment_index += 1

                if self.current_segment_index >= len(self.segment_urls):
                    if not self._refresh_playlist():
                        break

            except Exception as e:
                logger.error(f"Error processing segment {segment_url}: {e}")
                self.current_segment_index += 1

    def _download_and_process_segment(self, segment_url: str) -> None:
        response = self.session.get(segment_url, timeout=self.timeout, stream=True)
        response.raise_for_status()

        segment_path = os.path.join(self.temp_dir, f"segment_{self.current_segment_index}.ts")

        with open(segment_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        self._extract_frames_from_segment(segment_path)

        try:
            os.remove(segment_path)
        except:
            pass

    def _extract_frames_from_segment(self, segment_path: str) -> None:
        cap = cv2.VideoCapture(segment_path)

        try:
            while cap.isOpened() and self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame is not None:
                    self._put_frame(frame, {
                        'source': 'hls',
                        'segment_index': self.current_segment_index,
                        'playlist_url': self.playlist_url
                    })

                    time.sleep(1.0 / 30)

        finally:
            cap.release()

    def _refresh_playlist(self) -> bool:
        try:
            if not self.playlist.is_endlist:
                response = self.session.get(self.playlist_url, timeout=self.timeout)
                response.raise_for_status()

                new_playlist = m3u8.loads(response.text)

                if len(new_playlist.segments) > len(self.playlist.segments):
                    self.playlist = new_playlist
                    self._update_segment_urls()
                    return True

            return False

        except Exception as e:
            logger.error(f"Error refreshing HLS playlist: {e}")
            return False

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for HLS {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect HLS {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected HLS {self.stream_id}")
            return True

        return False

class MockHLSStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        logger.warning(f"m3u8 library not available, using mock HLS stream for {stream_id}")

    def connect(self) -> bool:
        self.is_connected = True
        self.last_error = "m3u8 library not installed - using mock stream"
        logger.warning(f"Mock HLS connection for {self.stream_id}")
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def _capture_loop(self) -> None:
        frame_count = 0

        while self.is_running:
            try:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

                cv2.putText(frame, f"Mock HLS Stream", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Frame: {frame_count}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                cv2.putText(frame, f"Install m3u8 for real HLS", (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                self._put_frame(frame, {'source': 'mock_hls', 'frame_count': frame_count})

                frame_count += 1
                time.sleep(1.0 / 30)

            except Exception as e:
                self._handle_error(f"Error in mock HLS capture: {e}")
                break

def create_hls_stream(stream_id: str, name: str, location: str, config: Dict[str, Any]):
    if HLS_AVAILABLE:
        return HLSStream(stream_id, name, location, config)
    else:
        return MockHLSStream(stream_id, name, location, config)