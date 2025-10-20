import cv2
import numpy as np
import torch
from ultralytics import YOLO
from typing import List, Dict, Any, Optional
import logging
from .base_detector import AIDetector, DetectionResult, Person

logger = logging.getLogger(__name__)

class HelmetDetector(AIDetector):
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.7):
        super().__init__(model_path, confidence_threshold)
        self.class_names = {
            0: "person",
            1: "helmet",
            2: "no_helmet"
        }

    def get_detector_type(self) -> str:
        return "helmet_detector"

    def load_model(self) -> bool:
        try:
            if self.model_path is None or self.model_path == "":
                logger.warning("No model path provided, using default YOLOv8 model")
                self.model = YOLO('yolov8n.pt')
            else:
                if not torch.cuda.is_available():
                    logger.warning("CUDA not available, using CPU for inference")

                self.model = YOLO(self.model_path)

                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.model.to(device)

            self.is_loaded = True
            logger.info(f"Helmet detection model loaded successfully from: {self.model_path or 'default'}")
            return True

        except Exception as e:
            logger.error(f"Failed to load helmet detection model: {e}")
            self.is_loaded = False
            return False

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        if not self.is_loaded:
            logger.error("Model not loaded. Call load_model() first.")
            return []

        try:
            frame = self.preprocess_frame(frame)

            results = self.model(frame, verbose=False)

            return self._process_yolo_results(results[0], frame.shape)

        except Exception as e:
            logger.error(f"Error during helmet detection: {e}")
            return []

    def _process_yolo_results(self, result, frame_shape) -> List[DetectionResult]:
        detections = []
        height, width = frame_shape[:2]

        if result.boxes is None:
            return detections

        boxes = result.boxes.xyxy.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy().astype(int)

        for i, (box, confidence, class_id) in enumerate(zip(boxes, confidences, class_ids)):
            if confidence < self.confidence_threshold:
                continue

            x1, y1, x2, y2 = box.astype(int)

            x1 = int(max(0, min(x1, width - 1)))
            y1 = int(max(0, min(y1, height - 1)))
            x2 = int(max(x1 + 1, min(x2, width)))
            y2 = int(max(y1 + 1, min(y2, height)))

            bbox = (x1, y1, x2 - x1, y2 - y1)

            class_name = self.class_names.get(class_id, "unknown")

            detection = DetectionResult(
                detection_type=class_name,
                confidence=float(confidence),
                bbox=bbox,
                additional_data={
                    "class_id": int(class_id),
                    "raw_box": box.tolist()
                }
            )

            detections.append(detection)

        return self.filter_results_by_confidence(detections)

    def detect_helmet_violations(self, frame: np.ndarray) -> List[DetectionResult]:
        all_detections = self.detect(frame)

        violations = []
        persons = []
        helmets = []
        no_helmets = []

        for detection in all_detections:
            if detection.detection_type == "person":
                persons.append(detection)
            elif detection.detection_type == "helmet":
                helmets.append(detection)
            elif detection.detection_type == "no_helmet":
                no_helmets.append(detection)

        for no_helmet in no_helmets:
            violations.append(DetectionResult(
                detection_type="helmet_violation",
                confidence=no_helmet.confidence,
                bbox=no_helmet.bbox,
                additional_data={
                    "violation_type": "no_helmet",
                    "original_detection": no_helmet.additional_data
                }
            ))

        paired_persons = self._associate_persons_with_helmets(persons, helmets)

        for person_detection in persons:
            person_has_helmet = any(
                person_detection.bbox == paired[0].bbox
                for paired in paired_persons if len(paired) > 1
            )

            if not person_has_helmet:
                violations.append(DetectionResult(
                    detection_type="helmet_violation",
                    confidence=person_detection.confidence,
                    bbox=person_detection.bbox,
                    additional_data={
                        "violation_type": "person_without_helmet",
                        "original_detection": person_detection.additional_data
                    }
                ))

        return violations

    def _associate_persons_with_helmets(self, persons: List[DetectionResult],
                                      helmets: List[DetectionResult]) -> List[List[DetectionResult]]:
        associations = []

        for person in persons:
            person_center = self._get_bbox_center(person.bbox)
            best_helmet = None
            min_distance = float('inf')

            for helmet in helmets:
                helmet_center = self._get_bbox_center(helmet.bbox)
                distance = np.sqrt(
                    (person_center[0] - helmet_center[0])**2 +
                    (person_center[1] - helmet_center[1])**2
                )

                if distance < min_distance and self._is_helmet_on_person(person.bbox, helmet.bbox):
                    min_distance = distance
                    best_helmet = helmet

            if best_helmet:
                associations.append([person, best_helmet])
            else:
                associations.append([person])

        return associations

    def _get_bbox_center(self, bbox):
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)

    def _is_helmet_on_person(self, person_bbox, helmet_bbox, overlap_threshold: float = 0.1):
        px, py, pw, ph = person_bbox
        hx, hy, hw, hh = helmet_bbox

        if hy + hh < py or hy > py + ph * 0.4:
            return False

        person_area = pw * ph
        helmet_area = hw * hh

        intersection_x1 = max(px, hx)
        intersection_y1 = max(py, hy)
        intersection_x2 = min(px + pw, hx + hw)
        intersection_y2 = min(py + ph, hy + hh)

        if intersection_x2 <= intersection_x1 or intersection_y2 <= intersection_y1:
            return False

        intersection_area = (intersection_x2 - intersection_x1) * (intersection_y2 - intersection_y1)
        overlap_ratio = intersection_area / min(person_area, helmet_area)

        return overlap_ratio >= overlap_threshold

    def analyze_frame_safety(self, frame: np.ndarray) -> Dict[str, Any]:
        violations = self.detect_helmet_violations(frame)
        all_detections = self.detect(frame)

        total_persons = len([d for d in all_detections if d.detection_type == "person"])
        total_violations = len(violations)
        safety_score = max(0, (total_persons - total_violations) / max(total_persons, 1))

        return {
            "safety_score": safety_score,
            "total_persons": total_persons,
            "violations_count": total_violations,
            "violations": violations,
            "all_detections": all_detections,
            "is_safe": total_violations == 0
        }

    def create_annotated_frame(self, frame: np.ndarray, show_all_detections: bool = True) -> np.ndarray:
        if show_all_detections:
            detections = self.detect(frame)
        else:
            detections = self.detect_helmet_violations(frame)

        color_map = {
            "person": (255, 0, 0),           # Blue
            "helmet": (0, 255, 0),           # Green
            "no_helmet": (0, 0, 255),        # Red
            "helmet_violation": (0, 0, 255)  # Red
        }

        return self.draw_all_detections(frame, detections, color_map)