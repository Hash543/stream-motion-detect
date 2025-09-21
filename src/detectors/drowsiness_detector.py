import cv2
import numpy as np
import mediapipe as mp
from scipy.spatial import distance as dist
from typing import List, Dict, Any, Optional, Tuple
import logging
import time
from collections import deque
from .base_detector import AIDetector, DetectionResult

# 嘗試導入 dlib，如果失敗則只使用 MediaPipe
try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False
    print("Warning: dlib not available, using MediaPipe only for face detection")

logger = logging.getLogger(__name__)

class DrowsinessDetector(AIDetector):
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.6,
                 ear_threshold: float = 0.25, mar_threshold: float = 0.7,
                 drowsiness_duration: float = 3.0):
        super().__init__(model_path, confidence_threshold)

        self.ear_threshold = ear_threshold          # Eye Aspect Ratio threshold
        self.mar_threshold = mar_threshold          # Mouth Aspect Ratio threshold
        self.drowsiness_duration = drowsiness_duration  # Duration in seconds

        # MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=10,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Dlib face detector and predictor (fallback)
        self.face_detector = None
        self.landmark_predictor = None

        # Eye landmark indices for MediaPipe
        self.LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        self.RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

        # Mouth landmark indices for MediaPipe
        self.MOUTH = [61, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318]

        # Tracking variables
        self.person_states: Dict[str, Dict] = {}

    def get_detector_type(self) -> str:
        return "drowsiness_detector"

    def load_model(self) -> bool:
        try:
            # Try to load dlib predictor as fallback (only if available)
            if DLIB_AVAILABLE and self.model_path:
                self.face_detector = dlib.get_frontal_face_detector()
                self.landmark_predictor = dlib.shape_predictor(self.model_path)
                logger.info(f"Loaded dlib shape predictor from: {self.model_path}")
            elif not DLIB_AVAILABLE:
                logger.info("dlib not available, using MediaPipe only")

            self.is_loaded = True
            logger.info("Drowsiness detector initialized successfully")
            return True

        except Exception as e:
            logger.warning(f"Could not load dlib predictor: {e}. Using MediaPipe only.")
            self.is_loaded = True  # MediaPipe doesn't require external model
            return True

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        if not self.is_loaded:
            logger.error("Model not loaded. Call load_model() first.")
            return []

        try:
            frame = self.preprocess_frame(frame)
            return self._detect_drowsiness_mediapipe(frame)

        except Exception as e:
            logger.error(f"Error during drowsiness detection: {e}")
            return []

    def _detect_drowsiness_mediapipe(self, frame: np.ndarray) -> List[DetectionResult]:
        detections = []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return detections

        height, width = frame.shape[:2]

        for idx, face_landmarks in enumerate(results.multi_face_landmarks):
            person_id = f"face_{idx}"

            # Convert landmarks to pixel coordinates
            landmarks = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * width)
                y = int(landmark.y * height)
                landmarks.append((x, y))

            # Calculate facial features
            ear = self._calculate_ear_mediapipe(landmarks)
            mar = self._calculate_mar_mediapipe(landmarks)
            head_pose = self._estimate_head_pose_mediapipe(landmarks, width, height)

            # Get face bounding box
            face_bbox = self._get_face_bbox(landmarks)

            # Initialize person state if not exists
            if person_id not in self.person_states:
                self.person_states[person_id] = {
                    'ear_history': deque(maxlen=30),  # ~1 second at 30fps
                    'drowsy_start_time': None,
                    'last_alert_time': 0
                }

            person_state = self.person_states[person_id]
            person_state['ear_history'].append(ear)

            # Detect drowsiness
            is_drowsy, drowsy_confidence = self._detect_drowsiness_state(
                ear, mar, head_pose, person_state
            )

            if is_drowsy and drowsy_confidence >= self.confidence_threshold:
                detection = DetectionResult(
                    detection_type="drowsiness",
                    confidence=drowsy_confidence,
                    bbox=face_bbox,
                    person_id=person_id,
                    additional_data={
                        "ear": ear,
                        "mar": mar,
                        "head_pose": head_pose,
                        "drowsy_duration": time.time() - (person_state['drowsy_start_time'] or time.time())
                    }
                )
                detections.append(detection)

        return self.filter_results_by_confidence(detections)

    def _calculate_ear_mediapipe(self, landmarks: List[Tuple[int, int]]) -> float:
        """Calculate Eye Aspect Ratio using MediaPipe landmarks"""
        try:
            # Left eye EAR
            left_eye_points = [landmarks[i] for i in self.LEFT_EYE[:6]]  # Use key points
            left_ear = self._compute_ear(left_eye_points)

            # Right eye EAR
            right_eye_points = [landmarks[i] for i in self.RIGHT_EYE[:6]]  # Use key points
            right_ear = self._compute_ear(right_eye_points)

            # Average EAR
            return (left_ear + right_ear) / 2.0

        except (IndexError, ZeroDivisionError):
            return 1.0  # Default to "eyes open"

    def _calculate_mar_mediapipe(self, landmarks: List[Tuple[int, int]]) -> float:
        """Calculate Mouth Aspect Ratio using MediaPipe landmarks"""
        try:
            mouth_points = [landmarks[i] for i in self.MOUTH[:6]]  # Use key points
            return self._compute_mar(mouth_points)

        except (IndexError, ZeroDivisionError):
            return 0.0  # Default to "mouth closed"

    def _compute_ear(self, eye_points: List[Tuple[int, int]]) -> float:
        """Compute Eye Aspect Ratio from eye landmarks"""
        if len(eye_points) < 6:
            return 1.0

        # Vertical distances
        A = dist.euclidean(eye_points[1], eye_points[5])
        B = dist.euclidean(eye_points[2], eye_points[4])

        # Horizontal distance
        C = dist.euclidean(eye_points[0], eye_points[3])

        if C == 0:
            return 1.0

        # EAR formula
        ear = (A + B) / (2.0 * C)
        return ear

    def _compute_mar(self, mouth_points: List[Tuple[int, int]]) -> float:
        """Compute Mouth Aspect Ratio from mouth landmarks"""
        if len(mouth_points) < 6:
            return 0.0

        # Vertical distances
        A = dist.euclidean(mouth_points[1], mouth_points[5])
        B = dist.euclidean(mouth_points[2], mouth_points[4])

        # Horizontal distance
        C = dist.euclidean(mouth_points[0], mouth_points[3])

        if C == 0:
            return 0.0

        # MAR formula
        mar = (A + B) / (2.0 * C)
        return mar

    def _estimate_head_pose_mediapipe(self, landmarks: List[Tuple[int, int]],
                                    width: int, height: int) -> Dict[str, float]:
        """Estimate head pose angles"""
        try:
            # Key points for head pose estimation
            nose_tip = landmarks[1]        # Nose tip
            chin = landmarks[18]           # Chin
            left_eye = landmarks[33]       # Left eye corner
            right_eye = landmarks[263]     # Right eye corner

            # Calculate head tilt (roll)
            eye_center_x = (left_eye[0] + right_eye[0]) / 2
            eye_center_y = (left_eye[1] + right_eye[1]) / 2

            dx = right_eye[0] - left_eye[0]
            dy = right_eye[1] - left_eye[1]
            roll = np.degrees(np.arctan2(dy, dx))

            # Calculate head nod (pitch) - simplified
            face_height = abs(nose_tip[1] - chin[1])
            center_y = height / 2
            pitch_factor = (nose_tip[1] - center_y) / (height / 2)
            pitch = pitch_factor * 30  # Scale to degrees

            # Calculate head turn (yaw) - simplified
            face_center_x = (nose_tip[0] + chin[0]) / 2
            center_x = width / 2
            yaw_factor = (face_center_x - center_x) / (width / 2)
            yaw = yaw_factor * 30  # Scale to degrees

            return {
                "roll": roll,
                "pitch": pitch,
                "yaw": yaw
            }

        except (IndexError, ZeroDivisionError):
            return {"roll": 0, "pitch": 0, "yaw": 0}

    def _get_face_bbox(self, landmarks: List[Tuple[int, int]]) -> Tuple[int, int, int, int]:
        """Get bounding box from face landmarks"""
        if not landmarks:
            return (0, 0, 1, 1)

        x_coords = [point[0] for point in landmarks]
        y_coords = [point[1] for point in landmarks]

        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        # Add some padding
        padding = 10
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        width = x_max - x_min + 2 * padding
        height = y_max - y_min + 2 * padding

        return (x_min, y_min, width, height)

    def _detect_drowsiness_state(self, ear: float, mar: float, head_pose: Dict[str, float],
                               person_state: Dict) -> Tuple[bool, float]:
        """Detect if person is drowsy based on multiple factors"""
        current_time = time.time()
        drowsy_indicators = 0
        total_indicators = 4

        # 1. Check EAR (closed eyes)
        if ear < self.ear_threshold:
            drowsy_indicators += 1

            if person_state['drowsy_start_time'] is None:
                person_state['drowsy_start_time'] = current_time
        else:
            person_state['drowsy_start_time'] = None

        # 2. Check EAR trend (gradual closing)
        if len(person_state['ear_history']) >= 10:
            recent_ear = list(person_state['ear_history'])[-10:]
            if np.mean(recent_ear[:5]) > np.mean(recent_ear[5:]):
                drowsy_indicators += 1

        # 3. Check excessive yawning (MAR)
        if mar > self.mar_threshold:
            drowsy_indicators += 1

        # 4. Check head pose (nodding)
        if abs(head_pose.get("pitch", 0)) > 20:  # Head nodding
            drowsy_indicators += 1

        # Calculate confidence based on indicators
        confidence = drowsy_indicators / total_indicators

        # Check duration for sustained drowsiness
        if person_state['drowsy_start_time']:
            drowsy_duration = current_time - person_state['drowsy_start_time']
            if drowsy_duration >= self.drowsiness_duration:
                confidence = min(1.0, confidence + 0.3)  # Boost confidence for sustained drowsiness
                return True, confidence

        # Return True if enough indicators suggest drowsiness
        is_drowsy = drowsy_indicators >= 2
        return is_drowsy, confidence

    def create_annotated_frame(self, frame: np.ndarray) -> np.ndarray:
        """Create annotated frame with drowsiness detection"""
        detections = self.detect(frame)

        color_map = {
            "drowsiness": (0, 165, 255),  # Orange
            "face": (255, 255, 0)         # Cyan
        }

        annotated_frame = self.draw_all_detections(frame, detections, color_map)

        # Add EAR/MAR information
        for detection in detections:
            if detection.additional_data:
                x, y, w, h = detection.bbox
                ear = detection.additional_data.get("ear", 0)
                mar = detection.additional_data.get("mar", 0)

                info_text = f"EAR: {ear:.2f} MAR: {mar:.2f}"
                cv2.putText(annotated_frame, info_text,
                           (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX,
                           0.5, (255, 255, 255), 1)

        return annotated_frame

    def cleanup(self) -> None:
        """Clean up resources"""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()

        self.person_states.clear()
        super().cleanup()
        logger.info("Cleaned up drowsiness detector")