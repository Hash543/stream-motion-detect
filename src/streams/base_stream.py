from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from queue import Queue, Empty
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

class StreamFrame:
    def __init__(self, frame, timestamp: datetime, metadata: Dict[str, Any] = None):
        self.frame = frame
        self.timestamp = timestamp
        self.metadata = metadata or {}

class BaseStream(ABC):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        self.stream_id = stream_id
        self.name = name
        self.location = location
        self.config = config

        self.is_running = False
        self.is_connected = False
        self.thread: Optional[threading.Thread] = None
        self.frame_queue = Queue(maxsize=config.get('buffer_size', 10))
        self.last_frame_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.reconnect_count = 0
        self.max_reconnect_attempts = config.get('max_reconnect_attempts', 5)
        self.reconnect_delay = config.get('reconnect_delay', 5)

        self.frame_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def _capture_loop(self) -> None:
        pass

    def start_capture(self) -> bool:
        if self.is_running:
            logger.warning(f"Stream {self.stream_id} is already running")
            return True

        if not self.connect():
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

        logger.info(f"Started capture for stream: {self.stream_id}")
        return True

    def stop_capture(self) -> None:
        self.is_running = False

        if self.thread is not None:
            self.thread.join(timeout=5)

        self.disconnect()

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break

        logger.info(f"Stopped capture for stream: {self.stream_id}")

    def get_latest_frame(self) -> Optional[StreamFrame]:
        try:
            return self.frame_queue.get_nowait()
        except Empty:
            return None

    def set_frame_callback(self, callback: Callable) -> None:
        self.frame_callback = callback

    def set_error_callback(self, callback: Callable) -> None:
        self.error_callback = callback

    def _handle_error(self, error: str) -> None:
        self.last_error = error
        logger.error(f"Stream {self.stream_id} error: {error}")

        if self.error_callback:
            try:
                self.error_callback(self.stream_id, error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")

    def _put_frame(self, frame, metadata: Dict[str, Any] = None) -> None:
        if not self.is_running:
            return

        timestamp = datetime.now()
        self.last_frame_time = timestamp

        stream_frame = StreamFrame(frame, timestamp, metadata)

        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                pass

        self.frame_queue.put(stream_frame)

        if self.frame_callback:
            try:
                self.frame_callback(self.stream_id, frame, timestamp)
            except Exception as e:
                logger.error(f"Error in frame callback for {self.stream_id}: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "name": self.name,
            "location": self.location,
            "type": self.__class__.__name__,
            "is_running": self.is_running,
            "is_connected": self.is_connected,
            "last_frame_time": self.last_frame_time,
            "reconnect_count": self.reconnect_count,
            "last_error": self.last_error,
            "queue_size": self.frame_queue.qsize(),
            "config": self.config
        }

    def get_stream_info(self) -> Dict[str, Any]:
        return {
            "id": self.stream_id,
            "name": self.name,
            "type": self.__class__.__name__,
            "location": self.location
        }