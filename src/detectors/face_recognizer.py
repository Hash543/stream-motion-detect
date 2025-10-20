import cv2
import numpy as np
import pickle
import os
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import json
from datetime import datetime
from .base_detector import AIDetector, DetectionResult, Person

# 嘗試導入 face_recognition，如果失敗則使用替代方案
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    # print("Warning: face_recognition not available, using MediaPipe as fallback")

# 導入 MediaPipe 作為備用方案
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

class FaceRecognizer(AIDetector):
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.6,
                 face_database_path: str = "data/face_database.pkl",
                 person_info_path: str = "data/person_info.json"):
        super().__init__(model_path, confidence_threshold)

        self.face_database_path = face_database_path
        self.person_info_path = person_info_path

        # Face database: {person_id: [face_encodings]}
        self.face_database: Dict[str, List[np.ndarray]] = {}
        # Person information: {person_id: {name, department, etc.}}
        self.person_info: Dict[str, Dict[str, str]] = {}

        # Detection parameters
        self.face_detection_model = "hog"  # "hog" or "cnn"
        self.num_jitters = 1
        self.tolerance = 1 - confidence_threshold  # Convert confidence to tolerance

        # 初始化檢測引擎
        self.use_face_recognition = FACE_RECOGNITION_AVAILABLE
        self.use_mediapipe = MEDIAPIPE_AVAILABLE

        if self.use_mediapipe:
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )

    def get_detector_type(self) -> str:
        return "face_recognizer"

    def load_model(self) -> bool:
        try:
            # Load face database
            if os.path.exists(self.face_database_path):
                with open(self.face_database_path, 'rb') as f:
                    self.face_database = pickle.load(f)
                logger.info(f"Loaded face database with {len(self.face_database)} persons")
            else:
                logger.info("Face database not found, starting with empty database")

            # Load person information
            if os.path.exists(self.person_info_path):
                with open(self.person_info_path, 'r', encoding='utf-8') as f:
                    self.person_info = json.load(f)
                logger.info(f"Loaded person information for {len(self.person_info)} persons")
            else:
                logger.info("Person info not found, starting with empty info")

            self.is_loaded = True
            logger.info("Face recognizer loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load face recognizer: {e}")
            self.is_loaded = False
            return False

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        if not self.is_loaded:
            logger.error("Model not loaded. Call load_model() first.")
            return []

        try:
            frame = self.preprocess_frame(frame)
            return self._detect_and_recognize_faces(frame)

        except Exception as e:
            logger.error(f"Error during face recognition: {e}")
            return []

    def _detect_and_recognize_faces(self, frame: np.ndarray) -> List[DetectionResult]:
        detections = []

        if not FACE_RECOGNITION_AVAILABLE:
            # logger.warning("face_recognition not available, using MediaPipe fallback")
            return self._detect_faces_with_mediapipe(frame)

        # Convert BGR to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Find face locations
        face_locations = face_recognition.face_locations(
            rgb_frame,
            model=self.face_detection_model
        )

        if not face_locations:
            return detections

        # Get face encodings
        face_encodings = face_recognition.face_encodings(
            rgb_frame,
            face_locations,
            num_jitters=self.num_jitters
        )

        # Process each detected face
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Convert face_recognition format to our format
            bbox = (left, top, right - left, bottom - top)

            # Recognize the person
            person_id, confidence = self._recognize_person(face_encoding)

            detection = DetectionResult(
                detection_type="face",
                confidence=confidence,
                bbox=bbox,
                person_id=person_id,
                additional_data={
                    "face_encoding": face_encoding.tolist(),
                    "person_name": self.person_info.get(person_id, {}).get("name", "Unknown"),
                    "face_location": (top, right, bottom, left)
                }
            )

            detections.append(detection)

        return self.filter_results_by_confidence(detections)

    def _detect_faces_with_mediapipe(self, frame: np.ndarray) -> List[DetectionResult]:
        """MediaPipe fallback for face detection when face_recognition is not available"""
        detections = []

        if not MEDIAPIPE_AVAILABLE:
            logger.error("Neither face_recognition nor MediaPipe is available")
            return detections

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame
        results = self.face_detection.process(rgb_frame)

        if results.detections:
            h, w, _ = frame.shape

            for detection in results.detections:
                # Get bounding box
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)

                # Ensure bbox is within frame bounds
                x = max(0, min(x, w - 1))
                y = max(0, min(y, h - 1))
                width = max(1, min(width, w - x))
                height = max(1, min(height, h - y))

                bbox = (x, y, width, height)
                confidence = detection.score[0]

                detection_result = DetectionResult(
                    detection_type="face",
                    confidence=confidence,
                    bbox=bbox,
                    person_id="unknown",  # Cannot recognize without face_recognition
                    additional_data={
                        "person_name": "Unknown",
                        "detection_method": "mediapipe"
                    }
                )

                detections.append(detection_result)

        return self.filter_results_by_confidence(detections)

    def _recognize_person(self, face_encoding: np.ndarray) -> Tuple[str, float]:
        """Recognize a person from face encoding"""
        if not FACE_RECOGNITION_AVAILABLE or not self.face_database:
            return "unknown", 0.0

        best_match_person = "unknown"
        best_distance = float('inf')

        for person_id, known_encodings in self.face_database.items():
            if not known_encodings:
                continue

            # Calculate distances to all known encodings for this person
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            min_distance = np.min(distances)

            if min_distance < best_distance:
                best_distance = min_distance
                best_match_person = person_id

        # Convert distance to confidence
        if best_distance <= self.tolerance:
            confidence = 1.0 - best_distance
            return best_match_person, confidence
        else:
            return "unknown", 0.0

    def add_person(self, person_id: str, name: str, face_images: List[np.ndarray],
                   additional_info: Optional[Dict[str, str]] = None) -> bool:
        """Add a new person to the face database"""
        if not FACE_RECOGNITION_AVAILABLE:
            logger.error("Cannot add person: face_recognition not available")
            return False

        try:
            face_encodings = []

            for image in face_images:
                # Convert BGR to RGB if necessary
                if len(image.shape) == 3 and image.shape[2] == 3:
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:
                    rgb_image = image

                # Get face encodings
                encodings = face_recognition.face_encodings(rgb_image)
                if encodings:
                    face_encodings.extend(encodings)

            if not face_encodings:
                logger.error(f"No faces found in images for person {person_id}")
                return False

            # Add to database
            self.face_database[person_id] = face_encodings

            # Add person info
            person_data = {"name": name, "added_date": datetime.now().isoformat()}
            if additional_info:
                person_data.update(additional_info)

            self.person_info[person_id] = person_data

            # Save databases
            self._save_face_database()
            self._save_person_info()

            logger.info(f"Added person {person_id} ({name}) with {len(face_encodings)} face encodings")
            return True

        except Exception as e:
            logger.error(f"Failed to add person {person_id}: {e}")
            return False

    def remove_person(self, person_id: str) -> bool:
        """Remove a person from the face database"""
        try:
            if person_id in self.face_database:
                del self.face_database[person_id]

            if person_id in self.person_info:
                del self.person_info[person_id]

            self._save_face_database()
            self._save_person_info()

            logger.info(f"Removed person {person_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove person {person_id}: {e}")
            return False

    def update_person_info(self, person_id: str, info_updates: Dict[str, str]) -> bool:
        """Update person information"""
        try:
            if person_id not in self.person_info:
                logger.error(f"Person {person_id} not found")
                return False

            self.person_info[person_id].update(info_updates)
            self.person_info[person_id]["updated_date"] = datetime.now().isoformat()

            self._save_person_info()
            logger.info(f"Updated info for person {person_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update person {person_id}: {e}")
            return False

    def get_person_info(self, person_id: str) -> Optional[Dict[str, str]]:
        """Get information about a person"""
        return self.person_info.get(person_id)

    def get_all_persons(self) -> Dict[str, Dict[str, str]]:
        """Get information about all registered persons"""
        return self.person_info.copy()

    def _save_face_database(self) -> None:
        """Save face database to file"""
        try:
            os.makedirs(os.path.dirname(self.face_database_path), exist_ok=True)
            with open(self.face_database_path, 'wb') as f:
                pickle.dump(self.face_database, f)

        except Exception as e:
            logger.error(f"Failed to save face database: {e}")

    def _save_person_info(self) -> None:
        """Save person information to file"""
        try:
            os.makedirs(os.path.dirname(self.person_info_path), exist_ok=True)
            with open(self.person_info_path, 'w', encoding='utf-8') as f:
                json.dump(self.person_info, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save person info: {e}")

    def set_detection_model(self, model: str) -> None:
        """Set face detection model ('hog' or 'cnn')"""
        if model in ['hog', 'cnn']:
            self.face_detection_model = model
            logger.info(f"Set face detection model to: {model}")
        else:
            logger.error(f"Invalid model: {model}. Use 'hog' or 'cnn'")

    def extract_face_from_bbox(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Extract face region from frame using bounding box"""
        try:
            x, y, w, h = bbox
            height, width = frame.shape[:2]

            # Ensure bbox is within frame bounds
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            return frame[y:y+h, x:x+w]

        except Exception as e:
            logger.error(f"Failed to extract face: {e}")
            return None

    def create_annotated_frame(self, frame: np.ndarray) -> np.ndarray:
        """Create annotated frame with face recognition results"""
        detections = self.detect(frame)

        annotated_frame = frame.copy()

        for detection in detections:
            x, y, w, h = detection.bbox

            # Draw face rectangle
            color = (0, 255, 0) if detection.person_id != "unknown" else (0, 0, 255)
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)

            # Draw person name and confidence
            person_name = detection.additional_data.get("person_name", "Unknown")
            label = f"{person_name}: {detection.confidence:.2f}"

            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            label_y = y - 10 if y - 10 > label_size[1] else y + h + 20

            cv2.rectangle(annotated_frame,
                         (x, label_y - label_size[1] - 5),
                         (x + label_size[0], label_y + 5),
                         color, -1)

            cv2.putText(annotated_frame, label, (x, label_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return annotated_frame

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the face database"""
        total_persons = len(self.face_database)
        total_encodings = sum(len(encodings) for encodings in self.face_database.values())

        return {
            "total_persons": total_persons,
            "total_face_encodings": total_encodings,
            "persons": list(self.face_database.keys()),
            "database_path": self.face_database_path,
            "info_path": self.person_info_path
        }

    def cleanup(self) -> None:
        """Clean up resources"""
        self.face_database.clear()
        self.person_info.clear()
        super().cleanup()
        logger.info("Cleaned up face recognizer")