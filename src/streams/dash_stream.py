import cv2
import time
import requests
import threading
import xml.etree.ElementTree as ET
import os
import tempfile
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import logging
from .base_stream import BaseStream
import numpy as np

logger = logging.getLogger(__name__)

class DASHStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        self.manifest_url = config['url']
        self.timeout = config.get('timeout', 30)
        self.buffer_duration = config.get('buffer_duration', 10)
        self.headers = config.get('headers', {})

        self.session: Optional[requests.Session] = None
        self.manifest: Optional[ET.Element] = None
        self.representation_url: Optional[str] = None
        self.segment_template: Optional[str] = None
        self.current_segment = 0
        self.temp_dir: Optional[str] = None

        self.segment_duration = 2.0

    def connect(self) -> bool:
        try:
            if self.session:
                self.session.close()

            self.session = requests.Session()
            if self.headers:
                self.session.headers.update(self.headers)

            self.temp_dir = tempfile.mkdtemp(prefix="dash_stream_")

            response = self.session.get(self.manifest_url, timeout=self.timeout)
            response.raise_for_status()

            self.manifest = ET.fromstring(response.content)

            if not self._parse_manifest():
                raise Exception("Failed to parse DASH manifest")

            self.is_connected = True
            self.reconnect_count = 0
            self.last_error = None

            logger.info(f"Successfully connected to DASH stream: {self.stream_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to DASH stream: {e}")
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

    def _parse_manifest(self) -> bool:
        try:
            ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}

            periods = self.manifest.findall('.//mpd:Period', ns)
            if not periods:
                logger.error("No periods found in DASH manifest")
                return False

            period = periods[0]
            adaptation_sets = period.findall('.//mpd:AdaptationSet', ns)

            video_adaptation_set = None
            for adaptation_set in adaptation_sets:
                content_type = adaptation_set.get('contentType', '')
                mime_type = adaptation_set.get('mimeType', '')

                if 'video' in content_type.lower() or 'video' in mime_type.lower():
                    video_adaptation_set = adaptation_set
                    break

            if video_adaptation_set is None:
                logger.error("No video adaptation set found in DASH manifest")
                return False

            representations = video_adaptation_set.findall('.//mpd:Representation', ns)
            if not representations:
                logger.error("No representations found in video adaptation set")
                return False

            best_representation = max(representations,
                                    key=lambda r: int(r.get('bandwidth', '0')))

            segment_template = best_representation.find('.//mpd:SegmentTemplate', ns)
            if segment_template is None:
                segment_template = video_adaptation_set.find('.//mpd:SegmentTemplate', ns)

            if segment_template is not None:
                self.segment_template = segment_template.get('media', '')
                duration = segment_template.get('duration')
                timescale = segment_template.get('timescale', '1')

                if duration and timescale:
                    self.segment_duration = float(duration) / float(timescale)

                base_url_elem = self.manifest.find('.//mpd:BaseURL', ns)
                if base_url_elem is not None:
                    base_url = base_url_elem.text
                    self.representation_url = urljoin(self.manifest_url, base_url)
                else:
                    self.representation_url = self.manifest_url.rsplit('/', 1)[0] + '/'

                return True
            else:
                logger.error("No segment template found in DASH manifest")
                return False

        except Exception as e:
            logger.error(f"Error parsing DASH manifest: {e}")
            return False

    def _capture_loop(self) -> None:
        while self.is_running:
            try:
                if not self.is_connected:
                    if not self._reconnect():
                        break
                    continue

                self._process_segments()

            except Exception as e:
                self._handle_error(f"Error in DASH capture loop: {e}")
                if not self._reconnect():
                    break

    def _process_segments(self) -> None:
        while self.is_running:
            try:
                segment_url = self._get_segment_url(self.current_segment)

                if segment_url:
                    self._download_and_process_segment(segment_url)

                self.current_segment += 1
                time.sleep(max(0, self.segment_duration - 0.5))

            except Exception as e:
                logger.error(f"Error processing DASH segment {self.current_segment}: {e}")
                self.current_segment += 1
                time.sleep(1)

    def _get_segment_url(self, segment_number: int) -> Optional[str]:
        if not self.segment_template:
            return None

        try:
            segment_url = self.segment_template.replace('$Number$', str(segment_number))
            segment_url = segment_url.replace('$Time$', str(segment_number * int(self.segment_duration)))

            return urljoin(self.representation_url, segment_url)

        except Exception as e:
            logger.error(f"Error generating segment URL: {e}")
            return None

    def _download_and_process_segment(self, segment_url: str) -> None:
        try:
            response = self.session.get(segment_url, timeout=self.timeout, stream=True)

            if response.status_code == 404:
                logger.warning(f"Segment not found: {segment_url}")
                return

            response.raise_for_status()

            segment_path = os.path.join(self.temp_dir, f"segment_{self.current_segment}.m4s")

            with open(segment_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self._extract_frames_from_segment(segment_path)

            try:
                os.remove(segment_path)
            except:
                pass

        except requests.exceptions.RequestException as e:
            if "404" not in str(e):
                logger.error(f"Error downloading DASH segment: {e}")

    def _extract_frames_from_segment(self, segment_path: str) -> None:
        cap = cv2.VideoCapture(segment_path)

        try:
            while cap.isOpened() and self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame is not None:
                    self._put_frame(frame, {
                        'source': 'dash',
                        'segment_number': self.current_segment,
                        'manifest_url': self.manifest_url
                    })

                    time.sleep(1.0 / 30)

        except Exception as e:
            logger.error(f"Error extracting frames from DASH segment: {e}")
        finally:
            cap.release()

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for DASH {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect DASH {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected DASH {self.stream_id}")
            return True

        return False

class MockDASHStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        logger.info(f"Using mock DASH stream for {stream_id} (DASH parsing implemented)")

    def connect(self) -> bool:
        self.is_connected = True
        self.last_error = None
        logger.info(f"Mock DASH connection for {self.stream_id}")
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def _capture_loop(self) -> None:
        frame_count = 0

        while self.is_running:
            try:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

                cv2.putText(frame, f"Mock DASH Stream", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Frame: {frame_count}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                cv2.putText(frame, f"DASH parsing implemented", (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                self._put_frame(frame, {'source': 'mock_dash', 'frame_count': frame_count})

                frame_count += 1
                time.sleep(1.0 / 30)

            except Exception as e:
                self._handle_error(f"Error in mock DASH capture: {e}")
                break

def create_dash_stream(stream_id: str, name: str, location: str, config: Dict[str, Any]):
    return DASHStream(stream_id, name, location, config)