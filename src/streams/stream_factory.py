from typing import Dict, Any, Optional
import logging

from .base_stream import BaseStream
from .http_stream import HTTPStream, WebcamStream
from .webrtc_stream import create_webrtc_stream
from .hls_stream import create_hls_stream
from .dash_stream import create_dash_stream
from .onvif_stream import create_onvif_stream

logger = logging.getLogger(__name__)

class RTSPStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        self.rtsp_url = config['url']
        self.username = config.get('username')
        self.password = config.get('password')
        self.timeout = config.get('timeout', 30)

        import cv2
        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        try:
            import cv2

            if self.cap:
                self.cap.release()

            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.get('buffer_size', 1))

            if 'fps' in self.config:
                self.cap.set(cv2.CAP_PROP_FPS, self.config['fps'])

            if not self.cap.isOpened():
                raise ConnectionError(f"Failed to open RTSP stream: {self.rtsp_url}")

            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise ConnectionError(f"Failed to read initial frame from: {self.rtsp_url}")

            self.is_connected = True
            self.reconnect_count = 0
            self.last_error = None

            logger.info(f"Successfully connected to RTSP stream: {self.stream_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to RTSP stream: {e}")
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
        import cv2
        import time

        while self.is_running:
            try:
                if not self.is_connected:
                    if not self._reconnect():
                        break
                    continue

                if self.cap is None or not self.cap.isOpened():
                    if not self._reconnect():
                        break
                    continue

                ret, frame = self.cap.read()

                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from RTSP {self.stream_id}")
                    if not self._reconnect():
                        break
                    continue

                self._put_frame(frame, {'source': 'rtsp', 'url': self.rtsp_url})

            except Exception as e:
                self._handle_error(f"Error in RTSP capture loop: {e}")
                if not self._reconnect():
                    break

    def _reconnect(self) -> bool:
        import time

        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for RTSP {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect RTSP {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected RTSP {self.stream_id}")
            return True

        return False

class StreamFactory:
    @staticmethod
    def create_stream(stream_config: Dict[str, Any]) -> Optional[BaseStream]:
        try:
            stream_type = stream_config.get('type', '').upper()
            stream_id = stream_config['id']
            name = stream_config['name']
            location = stream_config['location']
            config = stream_config['config']

            if stream_type == 'WEBCAM':
                return WebcamStream(stream_id, name, location, config)

            elif stream_type == 'RTSP':
                return RTSPStream(stream_id, name, location, config)

            elif stream_type == 'HTTP_MJPEG':
                return HTTPStream(stream_id, name, location, config)

            elif stream_type == 'HLS':
                return create_hls_stream(stream_id, name, location, config)

            elif stream_type == 'DASH':
                return create_dash_stream(stream_id, name, location, config)

            elif stream_type == 'WEBRTC':
                return create_webrtc_stream(stream_id, name, location, config)

            elif stream_type == 'ONVIF':
                return create_onvif_stream(stream_id, name, location, config)

            else:
                logger.error(f"Unsupported stream type: {stream_type}")
                return None

        except Exception as e:
            logger.error(f"Error creating stream {stream_config.get('id', 'unknown')}: {e}")
            return None

    @staticmethod
    def get_supported_types() -> Dict[str, str]:
        return {
            'WEBCAM': 'Local webcam device',
            'RTSP': 'Real Time Streaming Protocol',
            'HTTP_MJPEG': 'HTTP Motion JPEG stream',
            'HLS': 'HTTP Live Streaming',
            'DASH': 'Dynamic Adaptive Streaming over HTTP',
            'WEBRTC': 'Web Real-Time Communication',
            'ONVIF': 'Open Network Video Interface Forum'
        }

    @staticmethod
    def validate_config(stream_config: Dict[str, Any]) -> tuple[bool, str]:
        required_fields = ['id', 'name', 'type', 'location', 'config']

        for field in required_fields:
            if field not in stream_config:
                return False, f"Missing required field: {field}"

        stream_type = stream_config['type'].upper()
        config = stream_config['config']

        if stream_type == 'WEBCAM':
            if 'device_index' not in config:
                return False, "Webcam config missing 'device_index'"

        elif stream_type == 'RTSP':
            if 'url' not in config:
                return False, "RTSP config missing 'url'"

        elif stream_type == 'HTTP_MJPEG':
            if 'url' not in config:
                return False, "HTTP MJPEG config missing 'url'"

        elif stream_type == 'HLS':
            if 'url' not in config:
                return False, "HLS config missing 'url'"

        elif stream_type == 'DASH':
            if 'url' not in config:
                return False, "DASH config missing 'url'"

        elif stream_type == 'WEBRTC':
            if 'signaling_url' not in config:
                return False, "WebRTC config missing 'signaling_url'"

        elif stream_type == 'ONVIF':
            required_onvif = ['host', 'username', 'password']
            for field in required_onvif:
                if field not in config:
                    return False, f"ONVIF config missing '{field}'"

        else:
            return False, f"Unsupported stream type: {stream_type}"

        return True, "Configuration is valid"