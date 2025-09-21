from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import cv2
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class DetectionResult:
    detection_type: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    person_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class Person:
    person_id: str
    bbox: Tuple[int, int, int, int]
    face_encoding: Optional[np.ndarray] = None
    confidence: float = 0.0
    name: str = "Unknown"

class AIDetector(ABC):
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.is_loaded = False

    @abstractmethod
    def load_model(self) -> bool:
        pass

    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        pass

    @abstractmethod
    def get_detector_type(self) -> str:
        pass

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        if frame is None:
            raise ValueError("Input frame is None")

        if len(frame.shape) != 3:
            raise ValueError(f"Expected 3D frame, got shape: {frame.shape}")

        return frame

    def postprocess_results(self, raw_results: Any) -> List[DetectionResult]:
        return []

    def set_confidence_threshold(self, threshold: float) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        self.confidence_threshold = threshold
        logger.info(f"Set confidence threshold to {threshold} for {self.get_detector_type()}")

    def is_model_loaded(self) -> bool:
        return self.is_loaded

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "detector_type": self.get_detector_type(),
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "is_loaded": self.is_loaded
        }

    def validate_detection_result(self, result: DetectionResult) -> bool:
        if not 0 <= result.confidence <= 1:
            return False

        x, y, w, h = result.bbox
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            return False

        return True

    def filter_results_by_confidence(self, results: List[DetectionResult]) -> List[DetectionResult]:
        return [
            result for result in results
            if result.confidence >= self.confidence_threshold and self.validate_detection_result(result)
        ]

    def draw_detection_box(self, frame: np.ndarray, result: DetectionResult,
                          color: Tuple[int, int, int] = (0, 255, 0),
                          thickness: int = 2) -> np.ndarray:
        frame_copy = frame.copy()
        x, y, w, h = result.bbox

        cv2.rectangle(frame_copy, (x, y), (x + w, y + h), color, thickness)

        label = f"{result.detection_type}: {result.confidence:.2f}"
        if result.person_id:
            label += f" ({result.person_id})"

        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]

        label_y = y - 10 if y - 10 > label_size[1] else y + h + 20
        cv2.rectangle(frame_copy,
                     (x, label_y - label_size[1] - 5),
                     (x + label_size[0], label_y + 5),
                     color, -1)

        cv2.putText(frame_copy, label, (x, label_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame_copy

    def draw_all_detections(self, frame: np.ndarray, results: List[DetectionResult],
                           color_map: Optional[Dict[str, Tuple[int, int, int]]] = None) -> np.ndarray:
        if color_map is None:
            color_map = {
                "helmet": (0, 255, 0),      # Green
                "no_helmet": (0, 0, 255),   # Red
                "person": (255, 0, 0),      # Blue
                "drowsiness": (0, 165, 255), # Orange
                "face": (255, 255, 0)       # Cyan
            }

        frame_with_detections = frame.copy()

        for result in results:
            color = color_map.get(result.detection_type, (128, 128, 128))
            frame_with_detections = self.draw_detection_box(
                frame_with_detections, result, color
            )

        return frame_with_detections

    def cleanup(self) -> None:
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
        self.is_loaded = False
        logger.info(f"Cleaned up {self.get_detector_type()} detector")

class PersonDetector(AIDetector):
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5):
        super().__init__(model_path, confidence_threshold)

    def extract_persons_from_frame(self, frame: np.ndarray) -> List[Person]:
        detection_results = self.detect(frame)
        persons = []

        for result in detection_results:
            if result.detection_type == "person":
                person = Person(
                    person_id=result.person_id or f"person_{len(persons)}",
                    bbox=result.bbox,
                    confidence=result.confidence
                )
                persons.append(person)

        return persons

    def get_person_roi(self, frame: np.ndarray, person: Person) -> np.ndarray:
        x, y, w, h = person.bbox
        height, width = frame.shape[:2]

        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))

        return frame[y:y+h, x:x+w]