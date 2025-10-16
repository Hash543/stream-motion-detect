import cv2
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
import signal
import sys
import json

from .managers.config_manager import ConfigManager
from .managers.rtsp_manager import RTSPManager
from .managers.universal_stream_manager import UniversalStreamManager
from .managers.screenshot_manager import ScreenshotManager
from .managers.notification_sender import NotificationSender
from .managers.rule_engine_manager import RuleEngineManager
from .managers.alert_event_manager import AlertEventManager

from .detectors.helmet_detector import HelmetDetector
from .detectors.drowsiness_detector import DrowsinessDetector
from .detectors.face_recognizer import FaceRecognizer
from .managers.face_detection_manager import FaceDetectionManager
from .managers.helmet_violation_manager import HelmetViolationManager
from .managers.inactivity_detection_manager import InactivityDetectionManager

logger = logging.getLogger(__name__)

class MonitoringSystem:
    def __init__(self, config_path: str = "config/config.json", stream_config_path: str = "streamSource.json"):
        self.config_manager = ConfigManager(config_path)
        self.config = None

        # Core managers
        self.rtsp_manager = None
        self.stream_manager = UniversalStreamManager(stream_config_path)
        self.screenshot_manager = None
        self.notification_sender = None
        self.rule_engine_manager = None
        self.alert_event_manager = None

        # AI Detectors
        self.helmet_detector = None
        self.drowsiness_detector = None
        self.face_recognizer = None

        # Face Detection Manager
        self.face_detection_manager = None

        # Helmet Violation Manager
        self.helmet_violation_manager = None

        # Inactivity Detection Manager
        self.inactivity_detection_manager = None

        # System state
        self.is_running = False
        self.monitoring_thread = None

        # Statistics
        self.stats = {
            "start_time": None,
            "total_frames_processed": 0,
            "violations_detected": 0,
            "screenshots_taken": 0,
            "notifications_sent": 0
        }

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def initialize(self) -> bool:
        """Initialize the monitoring system"""
        try:
            logger.info("Initializing RTSP Monitoring System...")

            # Load configuration
            self.config = self.config_manager.load_config()
            self.config_manager.create_directories()

            # Setup logging
            self._setup_logging()

            # Initialize managers
            self._initialize_managers()

            # Initialize AI detectors
            self._initialize_detectors()

            # Setup RTSP streams (legacy)
            self._setup_rtsp_streams()

            # # Setup universal streams
            # self._setup_universal_streams()

            logger.info("System initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            return False

    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        log_config = self.config.logging

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_config.level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_config.log_file),
                logging.StreamHandler()
            ]
        )

        logger.info(f"Logging configured: {log_config.log_file}")

    def _initialize_managers(self) -> None:
        """Initialize all managers"""
        # Screenshot manager
        self.screenshot_manager = ScreenshotManager(
            screenshot_path=self.config.storage.screenshot_path,
            image_quality=self.config.storage.image_quality,
            max_storage_days=self.config.storage.max_storage_days
        )

        # Notification sender
        self.notification_sender = NotificationSender(
            endpoint=self.config.notification_api.endpoint,
            timeout=self.config.notification_api.timeout,
            retry_attempts=self.config.notification_api.retry_attempts
        )

        # RTSP manager
        self.rtsp_manager = RTSPManager()
        self.rtsp_manager.set_processing_fps(self.config.detection_settings.processing_fps)

        # Rule Engine manager
        self.rule_engine_manager = RuleEngineManager()
        self.rule_engine_manager.reload_rules()

        # Alert Event manager
        self.alert_event_manager = AlertEventManager()

        logger.info("All managers initialized")

    def _initialize_detectors(self) -> None:
        """Initialize AI detectors"""
        try:
            # Helmet detector
            self.helmet_detector = HelmetDetector(
                model_path=self.config.models.helmet_model_path,
                confidence_threshold=self.config.detection_settings.helmet_confidence_threshold
            )
            self.helmet_detector.load_model()

            # Drowsiness detector
            self.drowsiness_detector = DrowsinessDetector(
                confidence_threshold=self.config.detection_settings.face_recognition_threshold,
                drowsiness_duration=self.config.detection_settings.drowsiness_duration_threshold
            )
            self.drowsiness_detector.load_model()

            # Face recognizer
            self.face_recognizer = FaceRecognizer(
                model_path=self.config.models.face_model_path,
                confidence_threshold=self.config.detection_settings.face_recognition_threshold
            )
            self.face_recognizer.load_model()

            # Face Detection Manager with 10-second notification interval
            # Note: database_manager removed - use API instead
            self.face_detection_manager = FaceDetectionManager(
                face_recognizer=self.face_recognizer,
                notification_sender=self.notification_sender,
                screenshot_manager=self.screenshot_manager,
                database_manager=None,  # Use API instead
                notification_interval=10,  # 10 seconds interval
                auto_filing=False  # Disabled - use API instead
            )

            # Helmet Violation Manager with 20-second screenshot interval
            # 只在偵測到人臉時進行安全帽檢測
            self.helmet_violation_manager = HelmetViolationManager(
                helmet_detector=self.helmet_detector,
                notification_sender=self.notification_sender,
                screenshot_manager=self.screenshot_manager,
                screenshot_interval=20  # 20 seconds interval for same person
            )

            # Inactivity Detection Manager
            # 檢測10分鐘內沒有人臉且沒有動作的情況
            self.inactivity_detection_manager = InactivityDetectionManager(
                inactivity_threshold=600,  # 600 seconds (10 minutes) of inactivity
                motion_threshold=5.0,      # Motion detection threshold
                check_interval=600         # Check interval (10 minutes)
            )

            logger.info("All AI detectors and managers initialized")

        except Exception as e:
            logger.error(f"Failed to initialize detectors: {e}")
            raise

    def _setup_rtsp_streams(self) -> None:
        """Setup RTSP streams (legacy)"""
        for source in self.config.rtsp_sources:
            self.rtsp_manager.add_stream(
                source.id,
                source.url,
                source.location
            )

            # Set frame callback for each stream
            self.rtsp_manager.set_frame_callback(source.id, self._process_frame)

        logger.info(f"Setup {len(self.config.rtsp_sources)} legacy RTSP streams")

    def _setup_universal_streams(self) -> None:
        """Setup universal streams from streamSource.json"""
        if not self.stream_manager.load_config():
            logger.warning("Failed to load universal stream configuration")
            return

        results = self.stream_manager.initialize_streams()

        for stream_id, stream in self.stream_manager.streams.items():
            # Set frame callback for each stream
            self.stream_manager.set_frame_callback(stream_id, self._process_frame)

        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Setup {success_count}/{len(results)} universal streams")

    def start(self) -> bool:
        """Start the monitoring system"""
        try:
            if self.is_running:
                logger.warning("System is already running")
                return True

            logger.info("Starting RTSP Monitoring System...")

            # Start notification sender async worker
            # ???????? 開啟通知 worker
            # self.notification_sender.start_async_worker()

            # Start RTSP streams (legacy)
            results = self.rtsp_manager.start_all_streams()
            failed_streams = [cam_id for cam_id, success in results.items() if not success]

            if failed_streams:
                logger.warning(f"Failed to start legacy RTSP streams: {failed_streams}")

            # Start universal streams
            universal_results = self.stream_manager.start_all_streams()
            failed_universal = [stream_id for stream_id, success in universal_results.items() if not success]

            if failed_universal:
                logger.warning(f"Failed to start universal streams: {failed_universal}")

            total_streams = len(results) + len(universal_results)
            successful_streams = sum(results.values()) + sum(universal_results.values())
            logger.info(f"Started {successful_streams}/{total_streams} total streams")

            # Start monitoring thread
            self.is_running = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()

            self.stats["start_time"] = datetime.now()

            logger.info("RTSP Monitoring System started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.stop()
            return False

    def stop(self) -> None:
        """Stop the monitoring system"""
        logger.info("Stopping RTSP Monitoring System...")

        self.is_running = False

        # Stop monitoring thread
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        # Stop RTSP streams
        if self.rtsp_manager:
            self.rtsp_manager.stop_all_streams()

        # Stop universal streams
        if self.stream_manager:
            self.stream_manager.stop_all_streams()

        # Stop notification sender
        if self.notification_sender:
            self.notification_sender.stop_async_worker()

        # Cleanup detectors
        if self.helmet_detector:
            self.helmet_detector.cleanup()
        if self.drowsiness_detector:
            self.drowsiness_detector.cleanup()
        if self.face_recognizer:
            self.face_recognizer.cleanup()
        if self.face_detection_manager:
            self.face_detection_manager.cleanup()
        if self.helmet_violation_manager:
            self.helmet_violation_manager.cleanup()
        if self.inactivity_detection_manager:
            self.inactivity_detection_manager.cleanup()

        logger.info("RTSP Monitoring System stopped")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Monitoring loop started")

        try:
            while self.is_running:
                # Process frames from all streams
                self.rtsp_manager.process_frames()
                self.stream_manager.process_frames()

                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        finally:
            logger.info("Monitoring loop ended")

    def _process_frame(self, camera_id: str, frame, timestamp: datetime) -> None:
        """Process a single frame from RTSP stream"""
        try:
            self.stats["total_frames_processed"] += 1

            # Get stream type and enabled detection types from Rule Engine
            stream_type = self._get_stream_type(camera_id)
            enabled_detection_types = self.rule_engine_manager.get_enabled_detection_types(
                stream_id=camera_id,
                stream_type=stream_type
            )

            if not enabled_detection_types:
                logger.debug(f"No enabled detection types for {camera_id}, skipping frame")
                return

            logger.debug(f"Enabled detection types for {camera_id}: {enabled_detection_types}")

            # Always run face recognition for violation association (needed by other detectors)
            face_detections = self.face_recognizer.detect(frame)

            # Process face detection only if 'face' is in enabled types
            if 'face' in enabled_detection_types and self.face_detection_manager:
                face_detection_results = self.face_detection_manager.process_frame(frame, camera_id)
                if face_detection_results:
                    logger.debug(f"Face detection results: {len(face_detection_results)} faces processed")

            # Process inactivity detection only if 'inactivity' is in enabled types
            if 'inactivity' in enabled_detection_types and self.inactivity_detection_manager:
                inactivity_detections = self.inactivity_detection_manager.process_frame(
                    frame, camera_id, face_detections
                )
                # Handle inactivity violations
                for violation in inactivity_detections:
                    self._handle_violation(camera_id, frame, violation, face_detections, timestamp)

            # Process helmet detection only if 'helmet' is in enabled types
            if 'helmet' in enabled_detection_types and self.helmet_violation_manager:
                helmet_violation_results = self.helmet_violation_manager.process_frame(
                    frame, camera_id, face_detections
                )
                if helmet_violation_results:
                    logger.debug(
                        f"Helmet violation results: {len(helmet_violation_results)} "
                        f"violations processed with interval control"
                    )

            # Process drowsiness detection only if 'drowsiness' is in enabled types
            if 'drowsiness' in enabled_detection_types and self.drowsiness_detector:
                drowsiness_detections = self.drowsiness_detector.detect(frame)
                # Handle drowsiness violations
                for violation in drowsiness_detections:
                    self._handle_violation(camera_id, frame, violation, face_detections, timestamp)

        except Exception as e:
            logger.error(f"Error processing frame from {camera_id}: {e}")

    def _handle_violation(self, camera_id: str, frame, violation, face_detections, timestamp: datetime) -> None:
        """Handle a detected violation - check against Rule Engine first"""
        try:
            # Find associated person if possible
            person_id = self._associate_violation_with_person(violation, face_detections)

            # Get stream type from stream manager
            stream_type = self._get_stream_type(camera_id)

            # Check Rule Engine to see if we should process this violation
            should_trigger, matched_rule = self.rule_engine_manager.should_trigger_violation(
                stream_id=camera_id,
                stream_type=stream_type,
                detection_type=violation.detection_type,
                confidence=violation.confidence,
                person_id=person_id
            )

            if not should_trigger:
                logger.debug(
                    f"Violation {violation.detection_type} on {camera_id} "
                    f"filtered by Rule Engine (no matching rule or confidence too low)"
                )
                return

            logger.info(
                f"Rule Engine matched: {matched_rule['name']} "
                f"for {violation.detection_type} on {camera_id}"
            )

            # Take screenshot
            image_path = self.screenshot_manager.take_screenshot(
                frame=frame,
                camera_id=camera_id,
                violation_type=violation.detection_type,
                person_id=person_id,
                confidence=violation.confidence,
                bbox=violation.bbox
            )

            if image_path:
                self.stats["screenshots_taken"] += 1

            # 插入到 alert_event 表
            if self.alert_event_manager and image_path:
                alert_success = self.alert_event_manager.create_alert_event(
                    camera_id=camera_id,
                    violation_type=violation.detection_type,
                    confidence=violation.confidence,
                    image_path=image_path,
                    bbox=violation.bbox,
                    person_id=person_id
                )

                if alert_success:
                    logger.info(f"Alert event created for {violation.detection_type} on {camera_id}")

            # Send notification if enabled in rule
            if matched_rule.get('notification_enabled', True):
                success = self.notification_sender.send_violation_notification(
                    camera_id=camera_id,
                    violation_type=violation.detection_type,
                    person_id=person_id,
                    confidence=violation.confidence,
                    image_path=image_path or "",
                    bbox=violation.bbox
                )

                if success:
                    self.stats["notifications_sent"] += 1

            self.stats["violations_detected"] += 1

            logger.warning(
                f"VIOLATION DETECTED: {violation.detection_type} on {camera_id} "
                f"(confidence: {violation.confidence:.2f}, person: {person_id or 'unknown'}, "
                f"rule: {matched_rule['name']})"
            )

        except Exception as e:
            logger.error(f"Error handling violation: {e}")

    def _get_stream_type(self, camera_id: str) -> str:
        """Get stream type for a camera"""
        # Check in universal stream manager first
        if camera_id in self.stream_manager.streams:
            stream = self.stream_manager.streams[camera_id]
            return stream.stream_type
        # Default to RTSP for legacy streams
        return "rtsp"

    def _associate_violation_with_person(self, violation, face_detections) -> Optional[str]:
        """Associate a violation with a detected person"""
        if not face_detections:
            return None

        vx, vy, vw, vh = violation.bbox

        # Find the face detection that overlaps most with the violation
        best_overlap = 0
        best_person_id = None

        for face_detection in face_detections:
            fx, fy, fw, fh = face_detection.bbox

            # Calculate overlap
            overlap_x1 = max(vx, fx)
            overlap_y1 = max(vy, fy)
            overlap_x2 = min(vx + vw, fx + fw)
            overlap_y2 = min(vy + vh, fy + fh)

            if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                violation_area = vw * vh

                overlap_ratio = overlap_area / violation_area

                if overlap_ratio > best_overlap:
                    best_overlap = overlap_ratio
                    best_person_id = face_detection.person_id

        return best_person_id if best_overlap > 0.1 else None

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        status = {
            "is_running": self.is_running,
            "stats": self.stats.copy(),
            "rtsp_streams": {},
            "detectors": {},
            "managers": {}
        }

        # RTSP stream status (legacy)
        if self.rtsp_manager:
            status["rtsp_streams"] = self.rtsp_manager.get_all_streams_status()

        # Universal streams status
        if self.stream_manager:
            status["universal_streams"] = self.stream_manager.get_all_streams_status()
            status["stream_statistics"] = self.stream_manager.get_statistics()

        # Detector status
        if self.helmet_detector:
            status["detectors"]["helmet"] = self.helmet_detector.get_model_info()
        if self.drowsiness_detector:
            status["detectors"]["drowsiness"] = self.drowsiness_detector.get_model_info()
        if self.face_recognizer:
            status["detectors"]["face"] = self.face_recognizer.get_model_info()

        # Manager status
        if self.notification_sender:
            status["managers"]["notification"] = self.notification_sender.get_stats()
        if self.screenshot_manager:
            status["managers"]["screenshot"] = self.screenshot_manager.get_storage_stats()
        if self.face_detection_manager:
            status["managers"]["face_detection"] = self.face_detection_manager.get_stats()
        if self.helmet_violation_manager:
            status["managers"]["helmet_violation"] = self.helmet_violation_manager.get_stats()
        if self.inactivity_detection_manager:
            status["managers"]["inactivity_detection"] = self.inactivity_detection_manager.get_stats()

        return status

    def get_face_detection_history(self, person_id: Optional[str] = None, days: int = 7) -> List[Dict]:
        """Get face detection history"""
        if self.face_detection_manager:
            return self.face_detection_manager.get_detection_history(person_id, days)
        return []

    def set_face_notification_interval(self, interval_seconds: int) -> bool:
        """Set face detection notification interval"""
        if self.face_detection_manager:
            self.face_detection_manager.set_notification_interval(interval_seconds)
            logger.info(f"Face notification interval set to {interval_seconds} seconds")
            return True
        return False

    def reset_face_notification_history(self, person_id: Optional[str] = None) -> bool:
        """Reset face notification history for testing"""
        if self.face_detection_manager:
            self.face_detection_manager.reset_notification_history(person_id)
            return True
        return False

    def set_helmet_screenshot_interval(self, interval_seconds: int) -> bool:
        """Set helmet violation screenshot interval"""
        if self.helmet_violation_manager:
            self.helmet_violation_manager.set_screenshot_interval(interval_seconds)
            logger.info(f"Helmet screenshot interval set to {interval_seconds} seconds")
            return True
        return False

    def reset_helmet_screenshot_history(self, person_id: Optional[str] = None) -> bool:
        """Reset helmet violation screenshot history for testing"""
        if self.helmet_violation_manager:
            self.helmet_violation_manager.reset_screenshot_history(person_id)
            return True
        return False

    def get_helmet_violation_history(self, person_id: Optional[str] = None, days: int = 7) -> List[Dict]:
        """Get helmet violation history"""
        if self.helmet_violation_manager:
            return self.helmet_violation_manager.get_violation_history(person_id, days)
        return []

    def add_person_to_database(self, person_id: str, name: str,
                              face_images: List, additional_info: Optional[Dict] = None) -> bool:
        """Add a person to the face recognition database"""
        if self.face_recognizer:
            return self.face_recognizer.add_person(person_id, name, face_images, additional_info)
        return False

    def remove_person_from_database(self, person_id: str) -> bool:
        """Remove a person from the face recognition database"""
        if self.face_recognizer:
            return self.face_recognizer.remove_person(person_id)
        return False

    def get_face_database_stats(self) -> Dict:
        """Get face database statistics"""
        if self.face_recognizer:
            return self.face_recognizer.get_database_stats()
        return {}

    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)

    def run(self) -> None:
        """Run the monitoring system (blocking)"""
        try:
            if not self.initialize():
                logger.error("Failed to initialize system")
                return

            if not self.start():
                logger.error("Failed to start system")
                return

            logger.info("System is running. Press Ctrl+C to stop...")

            # Keep the main thread alive
            while self.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.stop()