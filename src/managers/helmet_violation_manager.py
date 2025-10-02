import cv2
import time
import json
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass, asdict

try:
    from ..detectors.helmet_detector import HelmetDetector
    from ..detectors.base_detector import DetectionResult
    from .notification_sender import NotificationSender, ViolationNotification
    from .screenshot_manager import ScreenshotManager
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from detectors.helmet_detector import HelmetDetector
    from detectors.base_detector import DetectionResult
    from managers.notification_sender import NotificationSender, ViolationNotification
    from managers.screenshot_manager import ScreenshotManager

logger = logging.getLogger(__name__)

@dataclass
class HelmetViolationRecord:
    """安全帽違規記錄"""
    person_id: str
    violation_type: str
    detection_time: str
    confidence: float
    camera_id: str
    image_path: str
    bbox: Tuple[int, int, int, int]

    def to_dict(self) -> Dict:
        return asdict(self)

class HelmetViolationManager:
    """安全帽違規管理器 - 處理同一人員未戴安全帽的20秒間隔截圖控制，只在偵測到人臉時檢測"""

    def __init__(self,
                 helmet_detector: HelmetDetector,
                 notification_sender: Optional[NotificationSender] = None,
                 screenshot_manager: Optional[ScreenshotManager] = None,
                 screenshot_interval: int = 20,  # 截圖間隔秒數，預設20秒
                 records_dir: str = "data/helmet_violations"):

        self.helmet_detector = helmet_detector
        self.notification_sender = notification_sender
        self.screenshot_manager = screenshot_manager
        self.screenshot_interval = screenshot_interval
        self.records_dir = Path(records_dir)

        # 確保目錄存在
        self.records_dir.mkdir(parents=True, exist_ok=True)

        # 追蹤每個人員的最後截圖時間
        self.last_screenshot_time: Dict[str, datetime] = {}

        # 違規記錄緩存
        self.violation_records: List[HelmetViolationRecord] = []

        # 統計數據
        self.stats = {
            "total_violations": 0,
            "unique_violators": 0,
            "screenshots_taken": 0,
            "notifications_sent": 0,
            "start_time": datetime.now()
        }

        # 線程鎖
        self._lock = threading.Lock()

        logger.info(f"Helmet Violation Manager initialized with {screenshot_interval}s screenshot interval")

    def process_frame(self, frame, camera_id: str = "default", face_detections: List = None) -> List[Dict]:
        """
        處理單一幀，進行安全帽違規檢測和後續處理

        重要：只有在偵測到人臉時才進行安全帽檢測
        """
        try:
            # 檢查是否有人臉檢測結果
            if not face_detections or len(face_detections) == 0:
                logger.debug("No faces detected, skipping helmet detection")
                return []

            # 進行安全帽違規檢測
            violations = self.helmet_detector.detect_helmet_violations(frame)

            if not violations:
                return []

            processed_results = []
            current_time = datetime.now()

            for violation in violations:
                # 嘗試關聯到具體人員
                person_id = self._associate_violation_with_person(violation, face_detections)

                # 如果沒有關聯到具體人臉，跳過這個違規
                if not person_id or person_id.startswith("unknown_at_"):
                    logger.debug(f"Helmet violation not associated with a face, skipping")
                    continue

                # 處理每個檢測到的違規
                result = self._process_single_violation(
                    violation, frame, camera_id, current_time, person_id
                )
                if result:
                    processed_results.append(result)

            return processed_results

        except Exception as e:
            logger.error(f"Error processing frame for helmet violations: {e}")
            return []

    def _associate_violation_with_person(self, violation: DetectionResult, face_detections: List) -> Optional[str]:
        """
        將違規與人員關聯

        重要：必須要有人臉檢測結果才能進行關聯
        如果沒有關聯到人臉，返回None表示此違規不應被處理
        """
        if not face_detections:
            logger.debug("No face detections available for association")
            return None

        vx, vy, vw, vh = violation.bbox

        # 找到與違規區域重疊最多的人臉檢測結果
        best_overlap = 0
        best_person_id = None

        for face_detection in face_detections:
            fx, fy, fw, fh = face_detection.bbox

            # 計算重疊區域
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

        # 只有當重疊度足夠時才返回person_id
        # 重疊度閾值設為0.3，確保違規確實與人臉區域有明顯關聯
        if best_overlap > 0.3 and best_person_id:
            logger.debug(f"Helmet violation associated with person {best_person_id} (overlap: {best_overlap:.2f})")
            return best_person_id
        else:
            logger.debug(f"Helmet violation not associated with any face (best overlap: {best_overlap:.2f})")
            return None

    def _process_single_violation(self, violation: DetectionResult, frame, camera_id: str,
                                current_time: datetime, person_id: str) -> Optional[Dict]:
        """處理單個安全帽違規結果"""
        try:
            confidence = violation.confidence
            bbox = violation.bbox
            violation_type = violation.detection_type

            # 檢查是否需要截圖（間隔控制）
            should_screenshot = self._should_take_screenshot(person_id, current_time)

            # 截圖保存
            image_path = None
            if should_screenshot and self.screenshot_manager:
                image_path = self.screenshot_manager.take_screenshot(
                    frame=frame,
                    camera_id=camera_id,
                    violation_type=violation_type,
                    person_id=person_id,
                    confidence=confidence,
                    bbox=bbox,
                    add_annotations=True
                )

            # 創建違規記錄
            record = HelmetViolationRecord(
                person_id=person_id,
                violation_type=violation_type,
                detection_time=current_time.isoformat(),
                confidence=confidence,
                camera_id=camera_id,
                image_path=image_path or "",
                bbox=bbox
            )

            # 保存記錄到文件
            self._save_violation_record(record)

            # 更新最後截圖時間（如果確實截圖了）
            if should_screenshot and image_path:
                with self._lock:
                    self.last_screenshot_time[person_id] = current_time

            # 發送通知
            if should_screenshot and self.notification_sender and image_path:
                self._send_violation_notification(record)

            # 更新統計
            self._update_stats(person_id, should_screenshot)

            return {
                "person_id": person_id,
                "violation_type": violation_type,
                "confidence": confidence,
                "bbox": bbox,
                "screenshot_taken": should_screenshot,
                "record_saved": True,
                "image_path": image_path
            }

        except Exception as e:
            logger.error(f"Error processing violation for {person_id}: {e}")
            return None

    def _should_take_screenshot(self, person_id: str, current_time: datetime) -> bool:
        """檢查是否應該截圖（基於時間間隔）"""
        with self._lock:
            last_time = self.last_screenshot_time.get(person_id)

            if last_time is None:
                return True  # 第一次檢測到此人的違規

            # 檢查時間間隔
            time_diff = current_time - last_time
            return time_diff.total_seconds() >= self.screenshot_interval

    def _save_violation_record(self, record: HelmetViolationRecord) -> None:
        """保存違規記錄到JSON文件"""
        try:
            # 按日期組織記錄文件
            date_str = datetime.fromisoformat(record.detection_time).strftime("%Y-%m-%d")
            records_file = self.records_dir / f"violations_{date_str}.json"

            # 讀取現有記錄
            records = []
            if records_file.exists():
                with open(records_file, 'r', encoding='utf-8') as f:
                    records = json.load(f)

            # 添加新記錄
            records.append(record.to_dict())

            # 保存回文件
            with open(records_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)

            # 也添加到內存緩存
            with self._lock:
                self.violation_records.append(record)
                # 限制內存中的記錄數量
                if len(self.violation_records) > 1000:
                    self.violation_records = self.violation_records[-500:]

            logger.debug(f"Saved violation record for {record.person_id}")

        except Exception as e:
            logger.error(f"Failed to save violation record: {e}")

    def _send_violation_notification(self, record: HelmetViolationRecord) -> None:
        """發送安全帽違規通知"""
        try:
            notification = ViolationNotification(
                timestamp=record.detection_time,
                camera_id=record.camera_id,
                violation_type=record.violation_type,
                person_id=record.person_id,
                confidence=record.confidence,
                image_path=record.image_path,
                location={
                    "x": record.bbox[0],
                    "y": record.bbox[1],
                    "width": record.bbox[2],
                    "height": record.bbox[3]
                }
            )

            # 添加安全帽違規特定信息
            notification_data = notification.to_dict()
            notification_data.update({
                "detection_type": "helmet_violation",
                "message": f"安全帽違規檢測: {record.violation_type} (人員: {record.person_id})"
            })

            # 發送通知
            if self.notification_sender:
                self.notification_sender.send_notification(notification_data)
                logger.info(f"Sent helmet violation notification for {record.person_id}")

        except Exception as e:
            logger.error(f"Failed to send helmet violation notification: {e}")

    def _update_stats(self, person_id: str, screenshot_taken: bool) -> None:
        """更新統計數據"""
        with self._lock:
            self.stats["total_violations"] += 1

            if screenshot_taken:
                self.stats["screenshots_taken"] += 1
                self.stats["notifications_sent"] += 1

            # 統計唯一違規人員數量
            unique_violators = len(self.last_screenshot_time)
            if person_id not in self.last_screenshot_time:
                unique_violators += 1
            self.stats["unique_violators"] = unique_violators

    def get_violation_history(self, person_id: Optional[str] = None,
                            days: int = 7) -> List[Dict]:
        """獲取違規歷史記錄"""
        try:
            records = []
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 遍歷指定日期範圍內的記錄文件
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                records_file = self.records_dir / f"violations_{date_str}.json"

                if records_file.exists():
                    with open(records_file, 'r', encoding='utf-8') as f:
                        daily_records = json.load(f)

                        # 過濾特定人員
                        if person_id:
                            daily_records = [r for r in daily_records
                                           if r.get("person_id") == person_id]

                        records.extend(daily_records)

                current_date += timedelta(days=1)

            return sorted(records, key=lambda x: x["detection_time"], reverse=True)

        except Exception as e:
            logger.error(f"Failed to get violation history: {e}")
            return []

    def get_stats(self) -> Dict:
        """獲取統計信息"""
        with self._lock:
            runtime = datetime.now() - self.stats["start_time"]
            return {
                **self.stats,
                "runtime_hours": runtime.total_seconds() / 3600,
                "screenshot_interval_seconds": self.screenshot_interval,
                "known_violators": len(self.last_screenshot_time)
            }

    def set_screenshot_interval(self, interval_seconds: int) -> None:
        """設置截圖間隔"""
        if interval_seconds > 0:
            self.screenshot_interval = interval_seconds
            logger.info(f"Updated screenshot interval to {interval_seconds} seconds")
        else:
            logger.error("Screenshot interval must be positive")

    def reset_screenshot_history(self, person_id: Optional[str] = None) -> None:
        """重置截圖歷史（用於測試或強制重新截圖）"""
        with self._lock:
            if person_id:
                if person_id in self.last_screenshot_time:
                    del self.last_screenshot_time[person_id]
                    logger.info(f"Reset screenshot history for {person_id}")
            else:
                self.last_screenshot_time.clear()
                logger.info("Reset all screenshot history")

    def cleanup(self) -> None:
        """清理資源"""
        logger.info("Cleaning up Helmet Violation Manager")
        with self._lock:
            self.violation_records.clear()
            self.last_screenshot_time.clear()