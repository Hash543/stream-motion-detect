import cv2
import time
import requests
import threading
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import base64
import hashlib
import uuid
from datetime import datetime, timezone
import logging
from .base_stream import BaseStream
import numpy as np

logger = logging.getLogger(__name__)

try:
    from onvif import ONVIFCamera
    ONVIF_AVAILABLE = True
except ImportError:
    ONVIF_AVAILABLE = False
    logger.warning("ONVIF support requires onvif-zeep library. Install with: pip install onvif-zeep")

class ONVIFStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        if not ONVIF_AVAILABLE:
            raise ImportError("ONVIF support requires onvif-zeep library")

        self.host = config['host']
        self.port = config.get('port', 80)
        self.username = config['username']
        self.password = config['password']
        self.profile_token = config.get('profile_token')
        self.service_url = config.get('service_url')
        self.media_url = config.get('media_url')

        self.onvif_camera: Optional[ONVIFCamera] = None
        self.media_service = None
        self.stream_url: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        try:
            self.onvif_camera = ONVIFCamera(
                self.host,
                self.port,
                self.username,
                self.password,
                wsdl_dir='/usr/local/lib/python3.x/site-packages/wsdl' if not hasattr(self, '_wsdl_dir') else None
            )

            device_mgmt = self.onvif_camera.devicemgmt
            device_info = device_mgmt.GetDeviceInformation()

            logger.info(f"Connected to ONVIF device: {device_info.Manufacturer} {device_info.Model}")

            self.media_service = self.onvif_camera.media

            profiles = self.media_service.GetProfiles()
            if not profiles:
                raise Exception("No media profiles found on ONVIF device")

            if self.profile_token:
                profile = next((p for p in profiles if p.token == self.profile_token), None)
                if not profile:
                    logger.warning(f"Profile {self.profile_token} not found, using first available")
                    profile = profiles[0]
            else:
                profile = profiles[0]

            stream_setup = self.media_service.create_type('GetStreamUri')
            stream_setup.StreamSetup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            stream_setup.ProfileToken = profile.token

            stream_uri_response = self.media_service.GetStreamUri(stream_setup)
            self.stream_url = stream_uri_response.Uri

            if self.stream_url:
                self.cap = cv2.VideoCapture(self.stream_url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not self.cap.isOpened():
                    raise ConnectionError(f"Failed to open ONVIF stream: {self.stream_url}")

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    raise ConnectionError(f"Failed to read initial frame from ONVIF stream")

                self.is_connected = True
                self.reconnect_count = 0
                self.last_error = None

                logger.info(f"Successfully connected to ONVIF stream: {self.stream_id}")
                return True
            else:
                raise Exception("Failed to get stream URI from ONVIF device")

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to ONVIF stream: {e}")
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

        self.onvif_camera = None
        self.media_service = None

    def _capture_loop(self) -> None:
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
                    logger.warning(f"Failed to read frame from ONVIF stream {self.stream_id}")
                    if not self._reconnect():
                        break
                    continue

                self._put_frame(frame, {
                    'source': 'onvif',
                    'host': self.host,
                    'stream_url': self.stream_url
                })

            except Exception as e:
                self._handle_error(f"Error in ONVIF capture loop: {e}")
                if not self._reconnect():
                    break

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for ONVIF {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect ONVIF {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected ONVIF {self.stream_id}")
            return True

        return False

    def get_device_info(self) -> Dict[str, Any]:
        if not self.onvif_camera:
            return {}

        try:
            device_mgmt = self.onvif_camera.devicemgmt
            device_info = device_mgmt.GetDeviceInformation()

            return {
                'manufacturer': getattr(device_info, 'Manufacturer', 'Unknown'),
                'model': getattr(device_info, 'Model', 'Unknown'),
                'firmware_version': getattr(device_info, 'FirmwareVersion', 'Unknown'),
                'serial_number': getattr(device_info, 'SerialNumber', 'Unknown'),
                'hardware_id': getattr(device_info, 'HardwareId', 'Unknown')
            }
        except Exception as e:
            logger.error(f"Error getting ONVIF device info: {e}")
            return {}

    def get_profiles(self) -> List[Dict[str, Any]]:
        if not self.media_service:
            return []

        try:
            profiles = self.media_service.GetProfiles()
            return [
                {
                    'token': profile.token,
                    'name': getattr(profile, 'Name', 'Unknown'),
                    'video_source_token': getattr(profile.VideoSourceConfiguration, 'SourceToken', None) if hasattr(profile, 'VideoSourceConfiguration') else None
                }
                for profile in profiles
            ]
        except Exception as e:
            logger.error(f"Error getting ONVIF profiles: {e}")
            return []

class ManualONVIFStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        self.host = config['host']
        self.port = config.get('port', 80)
        self.username = config['username']
        self.password = config['password']
        self.service_url = config.get('service_url', f"http://{self.host}:{self.port}/onvif/device_service")

        self.session: Optional[requests.Session] = None
        self.stream_url: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        try:
            self.session = requests.Session()

            stream_url = self._discover_stream_url()
            if not stream_url:
                raise Exception("Failed to discover ONVIF stream URL")

            self.stream_url = stream_url

            self.cap = cv2.VideoCapture(self.stream_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self.cap.isOpened():
                raise ConnectionError(f"Failed to open ONVIF stream: {self.stream_url}")

            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise ConnectionError(f"Failed to read initial frame from ONVIF stream")

            self.is_connected = True
            self.reconnect_count = 0
            self.last_error = None

            logger.info(f"Successfully connected to manual ONVIF stream: {self.stream_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to manual ONVIF stream: {e}")
            self.is_connected = False
            if self.cap:
                self.cap.release()
                self.cap = None
            return False

    def _discover_stream_url(self) -> Optional[str]:
        try:
            common_onvif_paths = [
                f"rtsp://{self.username}:{self.password}@{self.host}:554/stream1",
                f"rtsp://{self.username}:{self.password}@{self.host}:554/stream2",
                f"rtsp://{self.username}:{self.password}@{self.host}:554/live/ch1",
                f"rtsp://{self.username}:{self.password}@{self.host}:554/live/main",
                f"rtsp://{self.username}:{self.password}@{self.host}:554/cam/realmonitor?channel=1&subtype=0",
            ]

            for url in common_onvif_paths:
                try:
                    test_cap = cv2.VideoCapture(url)
                    if test_cap.isOpened():
                        ret, frame = test_cap.read()
                        test_cap.release()
                        if ret and frame is not None:
                            logger.info(f"Found working ONVIF stream URL: {url}")
                            return url
                except:
                    continue

            logger.warning("Could not discover ONVIF stream URL automatically")
            return common_onvif_paths[0]

        except Exception as e:
            logger.error(f"Error discovering ONVIF stream URL: {e}")
            return None

    def disconnect(self) -> None:
        self.is_connected = False

        if self.cap:
            self.cap.release()
            self.cap = None

        if self.session:
            self.session.close()
            self.session = None

    def _capture_loop(self) -> None:
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
                    logger.warning(f"Failed to read frame from manual ONVIF stream {self.stream_id}")
                    if not self._reconnect():
                        break
                    continue

                self._put_frame(frame, {
                    'source': 'manual_onvif',
                    'host': self.host,
                    'stream_url': self.stream_url
                })

            except Exception as e:
                self._handle_error(f"Error in manual ONVIF capture loop: {e}")
                if not self._reconnect():
                    break

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for manual ONVIF {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect manual ONVIF {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected manual ONVIF {self.stream_id}")
            return True

        return False

class MockONVIFStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        logger.warning(f"ONVIF libraries not available, using mock stream for {stream_id}")

    def connect(self) -> bool:
        self.is_connected = True
        self.last_error = "ONVIF libraries not installed - using mock stream"
        logger.warning(f"Mock ONVIF connection for {self.stream_id}")
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def _capture_loop(self) -> None:
        frame_count = 0

        while self.is_running:
            try:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

                cv2.putText(frame, f"Mock ONVIF Stream", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Frame: {frame_count}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                cv2.putText(frame, f"Install onvif-zeep for real ONVIF", (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                self._put_frame(frame, {'source': 'mock_onvif', 'frame_count': frame_count})

                frame_count += 1
                time.sleep(1.0 / 30)

            except Exception as e:
                self._handle_error(f"Error in mock ONVIF capture: {e}")
                break

def create_onvif_stream(stream_id: str, name: str, location: str, config: Dict[str, Any]):
    if ONVIF_AVAILABLE:
        return ONVIFStream(stream_id, name, location, config)
    else:
        try:
            return ManualONVIFStream(stream_id, name, location, config)
        except:
            return MockONVIFStream(stream_id, name, location, config)