import cv2
import time
import requests
import threading
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import numpy as np
from .base_stream import BaseStream
import logging

logger = logging.getLogger(__name__)

class HTTPStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        self.url = config['url']
        self.username = config.get('username')
        self.password = config.get('password')
        self.timeout = config.get('timeout', 30)
        self.headers = config.get('headers', {})

        self.session: Optional[requests.Session] = None
        self.stream_response: Optional[requests.Response] = None

    def connect(self) -> bool:
        try:
            if self.session:
                self.session.close()

            self.session = requests.Session()

            if self.headers:
                self.session.headers.update(self.headers)

            if self.username and self.password:
                self.session.auth = (self.username, self.password)

            parsed_url = urlparse(self.url)
            if not parsed_url.scheme:
                raise ValueError(f"Invalid URL format: {self.url}")

            test_response = self.session.get(self.url, timeout=self.timeout, stream=True)
            test_response.raise_for_status()

            self.is_connected = True
            self.reconnect_count = 0
            self.last_error = None

            logger.info(f"Successfully connected to HTTP stream: {self.stream_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to HTTP stream: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        self.is_connected = False

        if self.stream_response:
            try:
                self.stream_response.close()
            except:
                pass
            self.stream_response = None

        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None

    def _capture_loop(self) -> None:
        while self.is_running:
            try:
                if not self.is_connected:
                    if not self._reconnect():
                        break
                    continue

                self._stream_frames()

            except Exception as e:
                self._handle_error(f"Error in capture loop: {e}")
                if not self._reconnect():
                    break

    def _stream_frames(self) -> None:
        try:
            self.stream_response = self.session.get(
                self.url,
                timeout=self.timeout,
                stream=True
            )
            self.stream_response.raise_for_status()

            if 'multipart' in self.stream_response.headers.get('content-type', '').lower():
                self._handle_mjpeg_stream()
            else:
                self._handle_single_image()

        except Exception as e:
            raise Exception(f"Failed to stream frames: {e}")

    def _handle_mjpeg_stream(self) -> None:
        boundary = self._get_boundary()
        if not boundary:
            raise Exception("Could not find boundary in MJPEG stream")

        buffer = b''

        for chunk in self.stream_response.iter_content(chunk_size=1024):
            if not self.is_running:
                break

            buffer += chunk

            while True:
                boundary_pos = buffer.find(boundary)
                if boundary_pos == -1:
                    break

                frame_data = buffer[:boundary_pos]
                buffer = buffer[boundary_pos + len(boundary):]

                if frame_data:
                    self._process_image_data(frame_data)

    def _handle_single_image(self) -> None:
        image_data = self.stream_response.content
        self._process_image_data(image_data)

    def _process_image_data(self, image_data: bytes) -> None:
        try:
            header_end = image_data.find(b'\r\n\r\n')
            if header_end != -1:
                image_data = image_data[header_end + 4:]

            if not image_data:
                return

            np_array = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            if frame is not None:
                self._put_frame(frame, {'source': 'http', 'url': self.url})
            else:
                logger.warning(f"Failed to decode frame from {self.stream_id}")

        except Exception as e:
            logger.error(f"Error processing image data for {self.stream_id}: {e}")

    def _get_boundary(self) -> Optional[bytes]:
        content_type = self.stream_response.headers.get('content-type', '')

        if 'boundary=' in content_type:
            boundary = content_type.split('boundary=')[1].split(';')[0].strip()
            return f'--{boundary}'.encode()

        return None

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected {self.stream_id}")
            return True

        return False

class WebcamStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        self.device_index = config.get('device_index', 0)
        self.resolution = config.get('resolution', {'width': 1280, 'height': 720})
        self.fps = config.get('fps', 30)

        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        try:
            if self.cap:
                self.cap.release()

            self.cap = cv2.VideoCapture(self.device_index)

            if not self.cap.isOpened():
                raise ConnectionError(f"Failed to open webcam device: {self.device_index}")

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution['width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution['height'])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise ConnectionError(f"Failed to read initial frame from webcam: {self.device_index}")

            self.is_connected = True
            self.reconnect_count = 0
            self.last_error = None

            logger.info(f"Successfully connected to webcam: {self.stream_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to webcam: {e}")
            self.is_connected = False
            if self.cap:
                self.cap.release()
                self.cap = None
            return False

    def disconnect(self) -> None:
        self.is_connected = False

        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / self.fps
        last_frame_time = 0

        while self.is_running:
            try:
                if not self.is_connected:
                    if not self._reconnect():
                        break
                    continue

                current_time = time.time()
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue

                if self.cap is None or not self.cap.isOpened():
                    if not self._reconnect():
                        break
                    continue

                ret, frame = self.cap.read()

                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from webcam {self.stream_id}, ret={ret}, frame={frame is not None}")
                    if not self._reconnect():
                        break
                    continue

                # Debug: Log frame capture success occasionally
                if int(current_time) % 10 == 0 and current_time - last_frame_time > 9:
                    logger.debug(f"Webcam {self.stream_id} capturing frames, queue size: {self.frame_queue.qsize()}")

                self._put_frame(frame, {'source': 'webcam', 'device_index': self.device_index})
                last_frame_time = current_time

            except Exception as e:
                self._handle_error(f"Error in webcam capture loop: {e}")
                if not self._reconnect():
                    break

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for webcam {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect webcam {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected webcam {self.stream_id}")
            return True

        return False