import requests
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
import time
from queue import Queue
import threading

logger = logging.getLogger(__name__)

@dataclass
class ViolationNotification:
    timestamp: str
    camera_id: str
    violation_type: str
    person_id: Optional[str]
    confidence: float
    image_path: str
    location: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class NotificationSender:
    def __init__(self, endpoint: str, timeout: int = 10, retry_attempts: int = 3,
                 retry_delay: float = 1.0, async_mode: bool = True):
        self.endpoint = endpoint
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.async_mode = async_mode

        # Queue for async notifications
        self.notification_queue = Queue()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None

        # Statistics
        self.stats = {
            "total_sent": 0,
            "successful_sent": 0,
            "failed_sent": 0,
            "last_success_time": None,
            "last_error": None,
            "last_error_time": None
        }

        logger.info(f"Notification sender initialized: {self.endpoint}")

    def start_async_worker(self) -> None:
        """Start the async notification worker thread"""
        if self.is_running:
            logger.warning("Async worker is already running")
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._async_worker, daemon=True)
        self.worker_thread.start()
        logger.info("Async notification worker started")

    def stop_async_worker(self) -> None:
        """Stop the async notification worker thread"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Async notification worker stopped")

    def send_violation_notification(self, camera_id: str, violation_type: str,
                                  person_id: Optional[str], confidence: float,
                                  image_path: str, bbox: Optional[tuple] = None,
                                  async_send: bool = None) -> bool:
        """Send violation notification"""
        try:
            # Create notification data
            notification = self._create_notification(
                camera_id, violation_type, person_id, confidence, image_path, bbox
            )

            # Determine send mode
            use_async = async_send if async_send is not None else self.async_mode

            if use_async and self.is_running:
                self.notification_queue.put(notification)
                logger.debug(f"Queued notification for async sending: {camera_id}")
                return True
            else:
                return self._send_notification_sync(notification)

        except Exception as e:
            logger.error(f"Error creating violation notification: {e}")
            self._update_stats(success=False, error=str(e))
            return False

    def _create_notification(self, camera_id: str, violation_type: str,
                           person_id: Optional[str], confidence: float,
                           image_path: str, bbox: Optional[tuple]) -> ViolationNotification:
        """Create notification object"""
        timestamp = datetime.now().isoformat()

        # Convert bbox to location dict
        if bbox:
            x, y, w, h = bbox
            location = {"x": x, "y": y, "width": w, "height": h}
        else:
            location = {"x": 0, "y": 0, "width": 0, "height": 0}

        return ViolationNotification(
            timestamp=timestamp,
            camera_id=camera_id,
            violation_type=violation_type,
            person_id=person_id,
            confidence=confidence,
            image_path=image_path,
            location=location
        )

    def _send_notification_sync(self, notification: ViolationNotification) -> bool:
        """Send notification synchronously"""
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    self.endpoint,
                    json=notification.to_dict(),
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    logger.info(f"Notification sent successfully: {notification.camera_id}")
                    self._update_stats(success=True)
                    return True
                else:
                    logger.warning(f"Notification failed with status {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Notification attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)

        self._update_stats(success=False, error="Max retry attempts exceeded")
        return False

    async def _send_notification_async(self, notification: ViolationNotification) -> bool:
        """Send notification asynchronously"""
        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(
                        self.endpoint,
                        json=notification.to_dict(),
                        headers={'Content-Type': 'application/json'}
                    ) as response:

                        if response.status == 200:
                            logger.info(f"Async notification sent successfully: {notification.camera_id}")
                            self._update_stats(success=True)
                            return True
                        else:
                            text = await response.text()
                            logger.warning(f"Async notification failed with status {response.status}: {text}")

            except Exception as e:
                logger.error(f"Async notification attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)

        self._update_stats(success=False, error="Max retry attempts exceeded (async)")
        return False

    def _async_worker(self) -> None:
        """Async worker thread for processing notifications"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while self.is_running:
                try:
                    # Get notification from queue with timeout
                    notification = self.notification_queue.get(timeout=1.0)

                    # Send notification
                    task = loop.create_task(self._send_notification_async(notification))
                    loop.run_until_complete(task)

                    self.notification_queue.task_done()

                except Exception as e:
                    if self.is_running:  # Only log if we're still supposed to be running
                        logger.error(f"Error in async worker: {e}")

        finally:
            loop.close()

    def send_custom_notification(self, data: Dict[str, Any], async_send: bool = None) -> bool:
        """Send custom notification data"""
        try:
            use_async = async_send if async_send is not None else self.async_mode

            if use_async and self.is_running:
                # For custom data, we'll send it directly without queuing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    task = loop.create_task(self._send_custom_async(data))
                    return loop.run_until_complete(task)
                finally:
                    loop.close()
            else:
                return self._send_custom_sync(data)

        except Exception as e:
            logger.error(f"Error sending custom notification: {e}")
            return False

    def _send_custom_sync(self, data: Dict[str, Any]) -> bool:
        """Send custom notification synchronously"""
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    self.endpoint,
                    json=data,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    logger.info("Custom notification sent successfully")
                    self._update_stats(success=True)
                    return True
                else:
                    logger.warning(f"Custom notification failed with status {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Custom notification attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)

        self._update_stats(success=False, error="Max retry attempts exceeded (custom)")
        return False

    async def _send_custom_async(self, data: Dict[str, Any]) -> bool:
        """Send custom notification asynchronously"""
        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(
                        self.endpoint,
                        json=data,
                        headers={'Content-Type': 'application/json'}
                    ) as response:

                        if response.status == 200:
                            logger.info("Custom async notification sent successfully")
                            self._update_stats(success=True)
                            return True
                        else:
                            text = await response.text()
                            logger.warning(f"Custom async notification failed with status {response.status}: {text}")

            except Exception as e:
                logger.error(f"Custom async notification attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)

        self._update_stats(success=False, error="Max retry attempts exceeded (custom async)")
        return False

    def test_connection(self) -> bool:
        """Test connection to notification endpoint"""
        try:
            test_data = {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "message": "Connection test from RTSP monitoring system"
            }

            response = requests.post(
                self.endpoint,
                json=test_data,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )

            success = response.status_code == 200
            if success:
                logger.info(f"Connection test successful: {self.endpoint}")
            else:
                logger.warning(f"Connection test failed: {response.status_code}")

            return success

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _update_stats(self, success: bool, error: Optional[str] = None) -> None:
        """Update statistics"""
        self.stats["total_sent"] += 1

        if success:
            self.stats["successful_sent"] += 1
            self.stats["last_success_time"] = datetime.now().isoformat()
        else:
            self.stats["failed_sent"] += 1
            self.stats["last_error"] = error
            self.stats["last_error_time"] = datetime.now().isoformat()

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        stats = self.stats.copy()
        stats["queue_size"] = self.notification_queue.qsize()
        stats["is_running"] = self.is_running
        stats["endpoint"] = self.endpoint

        if stats["total_sent"] > 0:
            stats["success_rate"] = stats["successful_sent"] / stats["total_sent"]
        else:
            stats["success_rate"] = 0.0

        return stats

    def clear_stats(self) -> None:
        """Clear statistics"""
        self.stats = {
            "total_sent": 0,
            "successful_sent": 0,
            "failed_sent": 0,
            "last_success_time": None,
            "last_error": None,
            "last_error_time": None
        }
        logger.info("Notification statistics cleared")

    def update_endpoint(self, new_endpoint: str) -> None:
        """Update notification endpoint"""
        self.endpoint = new_endpoint
        logger.info(f"Updated notification endpoint: {new_endpoint}")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queue_size": self.notification_queue.qsize(),
            "is_running": self.is_running,
            "async_mode": self.async_mode
        }

    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop_async_worker()

        # Clear remaining notifications
        while not self.notification_queue.empty():
            try:
                self.notification_queue.get_nowait()
            except:
                break

        logger.info("Notification sender cleaned up")