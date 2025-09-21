import cv2
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path
import json
import threading
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ScreenshotInfo:
    filename: str
    camera_id: str
    violation_type: str
    timestamp: datetime
    person_id: Optional[str] = None
    confidence: float = 0.0
    bbox: Optional[tuple] = None
    file_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class ScreenshotManager:
    def __init__(self, screenshot_path: str = "./screenshots/",
                 image_quality: int = 95,
                 max_storage_days: int = 30):
        self.screenshot_path = Path(screenshot_path)
        self.image_quality = max(1, min(100, image_quality))
        self.max_storage_days = max_storage_days

        # Create directory if it doesn't exist
        self.screenshot_path.mkdir(parents=True, exist_ok=True)

        # Screenshot metadata
        self.metadata_file = self.screenshot_path / "screenshots_metadata.json"
        self.metadata: List[Dict[str, Any]] = []

        # Thread lock for metadata operations
        self._metadata_lock = threading.Lock()

        # Load existing metadata
        self._load_metadata()

        logger.info(f"Screenshot manager initialized: {self.screenshot_path}")

    def take_screenshot(self, frame: np.ndarray, camera_id: str,
                       violation_type: str, person_id: Optional[str] = None,
                       confidence: float = 0.0, bbox: Optional[tuple] = None,
                       add_annotations: bool = True) -> Optional[str]:
        """Take a screenshot and save it with metadata"""
        try:
            timestamp = datetime.now()
            filename = self._generate_filename(timestamp, camera_id, violation_type)
            filepath = self.screenshot_path / filename

            # Create annotated frame if requested
            if add_annotations:
                annotated_frame = self._create_annotated_frame(
                    frame, violation_type, person_id, confidence, bbox, timestamp
                )
            else:
                annotated_frame = frame.copy()

            # Save image
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality]
            success = cv2.imwrite(str(filepath), annotated_frame, encode_param)

            if not success:
                logger.error(f"Failed to save screenshot: {filepath}")
                return None

            # Get file size
            file_size = filepath.stat().st_size

            # Create screenshot info
            screenshot_info = ScreenshotInfo(
                filename=filename,
                camera_id=camera_id,
                violation_type=violation_type,
                timestamp=timestamp,
                person_id=person_id,
                confidence=confidence,
                bbox=bbox,
                file_size=file_size
            )

            # Add to metadata
            self._add_metadata(screenshot_info)

            logger.info(f"Screenshot saved: {filename} ({file_size} bytes)")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None

    def _generate_filename(self, timestamp: datetime, camera_id: str,
                          violation_type: str) -> str:
        """Generate filename for screenshot"""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        safe_violation_type = violation_type.replace(" ", "_").replace("/", "_")
        return f"{timestamp_str}_{camera_id}_{safe_violation_type}.jpg"

    def _create_annotated_frame(self, frame: np.ndarray, violation_type: str,
                              person_id: Optional[str], confidence: float,
                              bbox: Optional[tuple], timestamp: datetime) -> np.ndarray:
        """Create annotated frame with violation information"""
        annotated_frame = frame.copy()
        height, width = frame.shape[:2]

        # Add timestamp overlay
        timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated_frame, timestamp_text,
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (255, 255, 255), 2)

        # Add black background for timestamp
        text_size = cv2.getTextSize(timestamp_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.rectangle(annotated_frame,
                     (5, height - text_size[1] - 30),
                     (text_size[0] + 15, height - 5),
                     (0, 0, 0), -1)

        cv2.putText(annotated_frame, timestamp_text,
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (255, 255, 255), 2)

        # Add violation information
        violation_text = f"VIOLATION: {violation_type.upper()}"
        if confidence > 0:
            violation_text += f" ({confidence:.2f})"

        cv2.putText(annotated_frame, violation_text,
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.8, (0, 0, 255), 2)

        # Add black background for violation text
        viol_text_size = cv2.getTextSize(violation_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.rectangle(annotated_frame,
                     (5, 5),
                     (viol_text_size[0] + 15, 40),
                     (0, 0, 0), -1)

        cv2.putText(annotated_frame, violation_text,
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.8, (0, 0, 255), 2)

        # Add person ID if available
        if person_id:
            person_text = f"Person: {person_id}"
            cv2.putText(annotated_frame, person_text,
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (255, 255, 0), 2)

        # Draw bounding box if provided
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 3)

            # Add label above bounding box
            label = violation_type
            if person_id:
                label += f" - {person_id}"

            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            label_y = y - 10 if y - 10 > label_size[1] else y + h + 20

            cv2.rectangle(annotated_frame,
                         (x, label_y - label_size[1] - 5),
                         (x + label_size[0], label_y + 5),
                         (0, 0, 255), -1)

            cv2.putText(annotated_frame, label, (x, label_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return annotated_frame

    def _add_metadata(self, screenshot_info: ScreenshotInfo) -> None:
        """Add screenshot metadata"""
        with self._metadata_lock:
            self.metadata.append(screenshot_info.to_dict())
            self._save_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from file"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded {len(self.metadata)} screenshot metadata entries")
            else:
                self.metadata = []

        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            self.metadata = []

    def _save_metadata(self) -> None:
        """Save metadata to file"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def cleanup_old_screenshots(self) -> Dict[str, int]:
        """Clean up old screenshots based on max_storage_days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_storage_days)
            deleted_files = 0
            deleted_size = 0
            remaining_metadata = []

            with self._metadata_lock:
                for metadata_entry in self.metadata:
                    try:
                        screenshot_date = datetime.fromisoformat(metadata_entry['timestamp'])

                        if screenshot_date < cutoff_date:
                            # Delete file
                            filepath = self.screenshot_path / metadata_entry['filename']
                            if filepath.exists():
                                file_size = filepath.stat().st_size
                                filepath.unlink()
                                deleted_files += 1
                                deleted_size += file_size
                                logger.debug(f"Deleted old screenshot: {metadata_entry['filename']}")
                        else:
                            remaining_metadata.append(metadata_entry)

                    except Exception as e:
                        logger.error(f"Error processing metadata entry: {e}")
                        remaining_metadata.append(metadata_entry)  # Keep on error

                # Update metadata
                self.metadata = remaining_metadata
                self._save_metadata()

            logger.info(f"Cleanup completed: deleted {deleted_files} files ({deleted_size} bytes)")

            return {
                "deleted_files": deleted_files,
                "deleted_size": deleted_size,
                "remaining_files": len(self.metadata)
            }

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"deleted_files": 0, "deleted_size": 0, "remaining_files": len(self.metadata)}

    def get_screenshots_by_camera(self, camera_id: str,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get screenshots for a specific camera"""
        with self._metadata_lock:
            results = []

            for entry in self.metadata:
                if entry['camera_id'] != camera_id:
                    continue

                try:
                    screenshot_date = datetime.fromisoformat(entry['timestamp'])

                    if start_date and screenshot_date < start_date:
                        continue

                    if end_date and screenshot_date > end_date:
                        continue

                    results.append(entry)

                except Exception as e:
                    logger.error(f"Error processing metadata entry: {e}")

            return sorted(results, key=lambda x: x['timestamp'], reverse=True)

    def get_screenshots_by_violation(self, violation_type: str,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get screenshots for a specific violation type"""
        with self._metadata_lock:
            results = []

            for entry in self.metadata:
                if entry['violation_type'] != violation_type:
                    continue

                try:
                    screenshot_date = datetime.fromisoformat(entry['timestamp'])

                    if start_date and screenshot_date < start_date:
                        continue

                    if end_date and screenshot_date > end_date:
                        continue

                    results.append(entry)

                except Exception as e:
                    logger.error(f"Error processing metadata entry: {e}")

            return sorted(results, key=lambda x: x['timestamp'], reverse=True)

    def get_recent_screenshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get most recent screenshots"""
        with self._metadata_lock:
            sorted_metadata = sorted(self.metadata,
                                   key=lambda x: x['timestamp'],
                                   reverse=True)
            return sorted_metadata[:limit]

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            total_files = len(self.metadata)
            total_size = 0

            # Calculate total size from actual files
            for file_path in self.screenshot_path.glob("*.jpg"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

            # Group by violation type
            violation_counts = {}
            for entry in self.metadata:
                violation_type = entry['violation_type']
                violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1

            # Group by camera
            camera_counts = {}
            for entry in self.metadata:
                camera_id = entry['camera_id']
                camera_counts[camera_id] = camera_counts.get(camera_id, 0) + 1

            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_path": str(self.screenshot_path),
                "max_storage_days": self.max_storage_days,
                "violation_counts": violation_counts,
                "camera_counts": camera_counts
            }

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}

    def delete_screenshot(self, filename: str) -> bool:
        """Delete a specific screenshot"""
        try:
            filepath = self.screenshot_path / filename

            if filepath.exists():
                filepath.unlink()

            # Remove from metadata
            with self._metadata_lock:
                self.metadata = [entry for entry in self.metadata
                               if entry['filename'] != filename]
                self._save_metadata()

            logger.info(f"Deleted screenshot: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error deleting screenshot {filename}: {e}")
            return False