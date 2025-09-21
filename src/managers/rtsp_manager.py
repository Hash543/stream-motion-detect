import cv2
import threading
import time
import logging
from typing import Dict, Optional, Callable, Any
from queue import Queue, Empty
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class RTSPStream:
    def __init__(self, camera_id: str, rtsp_url: str, location: str,
                 max_reconnect_attempts: int = 5, reconnect_delay: int = 5):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.location = location
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_queue = Queue(maxsize=10)
        self.last_frame_time = None
        self.reconnect_count = 0
        self.last_error = None

    def connect(self) -> bool:
        try:
            if self.cap is not None:
                self.cap.release()

            self.cap = cv2.VideoCapture(self.rtsp_url)

            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            if not self.cap.isOpened():
                raise ConnectionError(f"Failed to open RTSP stream: {self.rtsp_url}")

            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise ConnectionError(f"Failed to read initial frame from: {self.rtsp_url}")

            self.reconnect_count = 0
            self.last_error = None
            logger.info(f"Successfully connected to RTSP stream: {self.camera_id}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to connect to RTSP stream {self.camera_id}: {e}")
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            return False

    def start_capture(self) -> bool:
        if self.is_running:
            logger.warning(f"Stream {self.camera_id} is already running")
            return True

        if not self.connect():
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

        logger.info(f"Started capture for stream: {self.camera_id}")
        return True

    def stop_capture(self) -> None:
        self.is_running = False

        if self.thread is not None:
            self.thread.join(timeout=5)

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break

        logger.info(f"Stopped capture for stream: {self.camera_id}")

    def _capture_loop(self) -> None:
        while self.is_running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    if not self._reconnect():
                        break
                    continue

                ret, frame = self.cap.read()

                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from {self.camera_id}")
                    if not self._reconnect():
                        break
                    continue

                self.last_frame_time = datetime.now()

                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass

                self.frame_queue.put((frame, self.last_frame_time))

            except Exception as e:
                logger.error(f"Error in capture loop for {self.camera_id}: {e}")
                if not self._reconnect():
                    break

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for {self.camera_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect {self.camera_id} (attempt {self.reconnect_count})")

        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected {self.camera_id}")
            return True

        return False

    def get_latest_frame(self) -> Optional[tuple]:
        try:
            return self.frame_queue.get_nowait()
        except Empty:
            return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "location": self.location,
            "is_running": self.is_running,
            "is_connected": self.cap is not None and self.cap.isOpened(),
            "last_frame_time": self.last_frame_time,
            "reconnect_count": self.reconnect_count,
            "last_error": self.last_error,
            "queue_size": self.frame_queue.qsize()
        }

class RTSPManager:
    def __init__(self):
        self.streams: Dict[str, RTSPStream] = {}
        self.frame_callbacks: Dict[str, Callable] = {}
        self.processing_fps = 2
        self.last_processing_time: Dict[str, float] = {}

    def add_stream(self, camera_id: str, rtsp_url: str, location: str) -> bool:
        if camera_id in self.streams:
            logger.warning(f"Stream {camera_id} already exists")
            return False

        stream = RTSPStream(camera_id, rtsp_url, location)
        self.streams[camera_id] = stream
        self.last_processing_time[camera_id] = 0

        logger.info(f"Added RTSP stream: {camera_id}")
        return True

    def remove_stream(self, camera_id: str) -> bool:
        if camera_id not in self.streams:
            logger.warning(f"Stream {camera_id} does not exist")
            return False

        self.streams[camera_id].stop_capture()
        del self.streams[camera_id]

        if camera_id in self.frame_callbacks:
            del self.frame_callbacks[camera_id]

        if camera_id in self.last_processing_time:
            del self.last_processing_time[camera_id]

        logger.info(f"Removed RTSP stream: {camera_id}")
        return True

    def start_stream(self, camera_id: str) -> bool:
        if camera_id not in self.streams:
            logger.error(f"Stream {camera_id} does not exist")
            return False

        return self.streams[camera_id].start_capture()

    def stop_stream(self, camera_id: str) -> bool:
        if camera_id not in self.streams:
            logger.error(f"Stream {camera_id} does not exist")
            return False

        self.streams[camera_id].stop_capture()
        return True

    def start_all_streams(self) -> Dict[str, bool]:
        results = {}
        for camera_id in self.streams:
            results[camera_id] = self.start_stream(camera_id)
        return results

    def stop_all_streams(self) -> None:
        for camera_id in self.streams:
            self.stop_stream(camera_id)

    def set_frame_callback(self, camera_id: str, callback: Callable) -> None:
        self.frame_callbacks[camera_id] = callback

    def set_processing_fps(self, fps: int) -> None:
        self.processing_fps = max(1, fps)
        logger.info(f"Set processing FPS to: {self.processing_fps}")

    def process_frames(self) -> None:
        current_time = time.time()

        for camera_id, stream in self.streams.items():
            if not stream.is_running:
                continue

            time_since_last = current_time - self.last_processing_time[camera_id]
            if time_since_last < (1.0 / self.processing_fps):
                continue

            frame_data = stream.get_latest_frame()
            if frame_data is None:
                continue

            frame, timestamp = frame_data

            if camera_id in self.frame_callbacks:
                try:
                    self.frame_callbacks[camera_id](camera_id, frame, timestamp)
                except Exception as e:
                    logger.error(f"Error in frame callback for {camera_id}: {e}")

            self.last_processing_time[camera_id] = current_time

    def get_stream_status(self, camera_id: str) -> Optional[Dict[str, Any]]:
        if camera_id not in self.streams:
            return None
        return self.streams[camera_id].get_status()

    def get_all_streams_status(self) -> Dict[str, Dict[str, Any]]:
        return {
            camera_id: stream.get_status()
            for camera_id, stream in self.streams.items()
        }

    def cleanup(self) -> None:
        logger.info("Cleaning up RTSP Manager")
        self.stop_all_streams()
        self.streams.clear()
        self.frame_callbacks.clear()
        self.last_processing_time.clear()