"""
Lazy loading detection manager to reduce memory pressure at startup
"""
import logging
from typing import Optional, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)


class LazyDetectorManager:
    """
    Manages lazy loading of detection models to prevent memory conflicts at startup.
    Models are only loaded when first needed for a specific detection rule.
    """

    def __init__(self):
        self._detectors: Dict[str, Any] = {}
        self._locks: Dict[str, Lock] = {
            'helmet': Lock(),
            'drowsiness': Lock(),
            'face_recognition': Lock()
        }
        self._loading_state: Dict[str, bool] = {
            'helmet': False,
            'drowsiness': False,
            'face_recognition': False
        }

    def get_helmet_detector(self):
        """Lazy load helmet detector only when needed"""
        if 'helmet' not in self._detectors:
            with self._locks['helmet']:
                if 'helmet' not in self._detectors:
                    logger.info("Lazy loading helmet detector (YOLOv8)...")
                    self._loading_state['helmet'] = True
                    try:
                        from src.detectors.helmet_detector import HelmetDetector
                        detector = HelmetDetector()
                        detector.load_model()  # Actually load the model weights
                        self._detectors['helmet'] = detector
                        logger.info("✓ Helmet detector loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load helmet detector: {e}")
                        raise
                    finally:
                        self._loading_state['helmet'] = False

        return self._detectors.get('helmet')

    def get_drowsiness_detector(self):
        """Lazy load drowsiness detector only when needed"""
        if 'drowsiness' not in self._detectors:
            with self._locks['drowsiness']:
                if 'drowsiness' not in self._detectors:
                    logger.info("Lazy loading drowsiness detector (MediaPipe)...")
                    self._loading_state['drowsiness'] = True
                    try:
                        from src.detectors.drowsiness_detector import DrowsinessDetector
                        detector = DrowsinessDetector()
                        detector.load_model()  # Actually load the model weights
                        self._detectors['drowsiness'] = detector
                        logger.info("✓ Drowsiness detector loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load drowsiness detector: {e}")
                        raise
                    finally:
                        self._loading_state['drowsiness'] = False

        return self._detectors.get('drowsiness')

    def get_face_recognizer(self):
        """Lazy load face recognizer only when needed"""
        if 'face_recognition' not in self._detectors:
            with self._locks['face_recognition']:
                if 'face_recognition' not in self._detectors:
                    logger.info("Lazy loading face recognizer (TensorFlow Lite)...")
                    self._loading_state['face_recognition'] = True
                    try:
                        from src.detectors.face_recognizer import FaceRecognizer
                        detector = FaceRecognizer()
                        detector.load_model()  # Actually load the model weights
                        self._detectors['face_recognition'] = detector
                        logger.info("✓ Face recognizer loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load face recognizer: {e}")
                        raise
                    finally:
                        self._loading_state['face_recognition'] = False

        return self._detectors.get('face_recognition')

    def is_loading(self, detector_type: str) -> bool:
        """Check if a detector is currently being loaded"""
        return self._loading_state.get(detector_type, False)

    def is_loaded(self, detector_type: str) -> bool:
        """Check if a detector has been loaded"""
        return detector_type in self._detectors

    def get_loaded_detectors(self) -> list:
        """Get list of currently loaded detector types"""
        return list(self._detectors.keys())

    def unload_detector(self, detector_type: str):
        """Unload a specific detector to free memory"""
        if detector_type in self._detectors:
            logger.info(f"Unloading {detector_type} detector...")
            try:
                detector = self._detectors.pop(detector_type)
                # Call cleanup method if available
                if hasattr(detector, 'cleanup'):
                    detector.cleanup()
                logger.info(f"✓ {detector_type} detector unloaded")
            except Exception as e:
                logger.error(f"Error unloading {detector_type} detector: {e}")

    def unload_all(self):
        """Unload all detectors"""
        for detector_type in list(self._detectors.keys()):
            self.unload_detector(detector_type)

    def get_status(self) -> Dict[str, Dict[str, bool]]:
        """Get status of all detectors"""
        return {
            'helmet': {
                'loaded': self.is_loaded('helmet'),
                'loading': self.is_loading('helmet')
            },
            'drowsiness': {
                'loaded': self.is_loaded('drowsiness'),
                'loading': self.is_loading('drowsiness')
            },
            'face_recognition': {
                'loaded': self.is_loaded('face_recognition'),
                'loading': self.is_loading('face_recognition')
            }
        }


# Global singleton instance
_lazy_detector_manager: Optional[LazyDetectorManager] = None


def get_lazy_detector_manager() -> LazyDetectorManager:
    """Get or create the global lazy detector manager instance"""
    global _lazy_detector_manager
    if _lazy_detector_manager is None:
        _lazy_detector_manager = LazyDetectorManager()
    return _lazy_detector_manager
