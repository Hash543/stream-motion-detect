import cv2
import os
import time
import json
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
import hashlib

from ..detectors.face_recognizer import FaceRecognizer
from .notification_sender import NotificationSender, ViolationNotification
from .screenshot_manager import ScreenshotManager
from .database_manager import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class FaceDetectionRecord:
    """人臉檢測記錄"""
    person_id: str
    person_name: str
    detection_time: str
    confidence: float
    camera_id: str
    image_path: str
    bbox: Tuple[int, int, int, int]

    def to_dict(self) -> Dict:
        return asdict(self)

class FaceDetectionManager:
    """人臉檢測管理器 - 處理人臉識別後的建檔和通知間隔控制"""

    def __init__(self,
                 face_recognizer: FaceRecognizer,
                 notification_sender: Optional[NotificationSender] = None,
                 screenshot_manager: Optional[ScreenshotManager] = None,
                 database_manager: Optional[DatabaseManager] = None,
                 notification_interval: int = 10,  # 通知間隔秒數
                 records_dir: str = "data/face_detections",
                 auto_filing: bool = True):  # 自動建檔功能開關

        self.face_recognizer = face_recognizer
        self.notification_sender = notification_sender
        self.screenshot_manager = screenshot_manager
        self.database_manager = database_manager
        self.notification_interval = notification_interval
        self.records_dir = Path(records_dir)
        self.auto_filing = auto_filing

        # 確保目錄存在
        self.records_dir.mkdir(parents=True, exist_ok=True)

        # 追蹤最後通知時間，避免同一人短時間內重複通知
        self.last_notification_time: Dict[str, datetime] = {}

        # 追蹤已建檔的人員，避免重複建檔操作
        self.filed_persons: set = set()

        # 檢測記錄緩存
        self.detection_records: List[FaceDetectionRecord] = []

        # 統計數據
        self.stats = {
            "total_detections": 0,
            "unique_persons_detected": 0,
            "notifications_sent": 0,
            "records_saved": 0,
            "persons_filed": 0,  # 新增：建檔人數統計
            "start_time": datetime.now()
        }

        # 線程鎖
        self._lock = threading.Lock()

        logger.info(f"Face Detection Manager initialized with {notification_interval}s notification interval")

    def process_frame(self, frame, camera_id: str = "default") -> List[Dict]:
        """處理單一幀，進行人臉檢測和後續處理"""
        try:
            # 進行人臉檢測
            detections = self.face_recognizer.detect(frame)

            if not detections:
                return []

            processed_results = []
            current_time = datetime.now()

            for detection in detections:
                # 處理每個檢測到的人臉
                result = self._process_single_detection(
                    detection, frame, camera_id, current_time
                )
                if result:
                    processed_results.append(result)

            return processed_results

        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return []

    def _process_single_detection(self, detection, frame, camera_id: str, current_time: datetime) -> Optional[Dict]:
        """處理單個人臉檢測結果"""
        try:
            person_id = detection.person_id
            person_name = detection.additional_data.get("person_name", "Unknown")
            confidence = detection.confidence
            bbox = detection.bbox

            # 檢查是否需要發送通知（間隔控制）
            should_notify = self._should_send_notification(person_id, current_time)

            # 截圖保存
            image_path = None
            if should_notify and self.screenshot_manager:
                image_path = self._save_face_screenshot(frame, bbox, person_id, current_time)

            # 創建檢測記錄
            record = FaceDetectionRecord(
                person_id=person_id,
                person_name=person_name,
                detection_time=current_time.isoformat(),
                confidence=confidence,
                camera_id=camera_id,
                image_path=image_path or "",
                bbox=bbox
            )

            # 保存記錄到文件
            self._save_detection_record(record)

            # 自動建檔到資料庫
            person_filed = False
            if self.auto_filing and self.database_manager and person_id != "unknown":
                person_filed = self._ensure_person_filing(person_id, person_name, camera_id, confidence)

            # 發送通知
            if should_notify and self.notification_sender and image_path:
                self._send_face_detection_notification(record)

                # 更新最後通知時間
                with self._lock:
                    self.last_notification_time[person_id] = current_time

            # 更新統計
            self._update_stats(person_id, should_notify, person_filed)

            return {
                "person_id": person_id,
                "person_name": person_name,
                "confidence": confidence,
                "bbox": bbox,
                "notification_sent": should_notify,
                "record_saved": True,
                "image_path": image_path
            }

        except Exception as e:
            logger.error(f"Error processing detection for {detection.person_id}: {e}")
            return None

    def _ensure_person_filing(self, person_id: str, person_name: str,
                            camera_id: str, confidence: float) -> bool:
        """確保人員已建檔到資料庫"""
        try:
            is_new_filing = person_id not in self.filed_persons

            # 嘗試建檔或更新人員記錄
            additional_info = {
                'detection_source': 'face_recognition',
                'first_detected_camera': camera_id,
                'first_detection_confidence': confidence
            }

            success = self.database_manager.ensure_person_exists(
                person_id=person_id,
                name=person_name,
                additional_info=additional_info
            )

            if success:
                # 更新最後出現資訊
                self.database_manager.update_person_last_seen(
                    person_id=person_id,
                    camera_id=camera_id,
                    confidence=confidence
                )

                # 標記為已建檔
                with self._lock:
                    self.filed_persons.add(person_id)

                if is_new_filing:
                    logger.info(f"New person filed to database: {person_id} ({person_name})")
                else:
                    logger.debug(f"Person filing updated: {person_id} ({person_name})")

            return success and is_new_filing  # 只有新建檔才回傳True

        except Exception as e:
            logger.error(f"Failed to ensure person filing for {person_id}: {e}")
            return False

    def _should_send_notification(self, person_id: str, current_time: datetime) -> bool:
        """檢查是否應該發送通知（基於時間間隔）"""
        if person_id == "unknown":
            return False  # 不對未知人員發送通知

        with self._lock:
            last_time = self.last_notification_time.get(person_id)

            if last_time is None:
                return True  # 第一次檢測到此人

            # 檢查時間間隔
            time_diff = current_time - last_time
            return time_diff.total_seconds() >= self.notification_interval

    def _save_face_screenshot(self, frame, bbox: Tuple[int, int, int, int],
                            person_id: str, timestamp: datetime) -> Optional[str]:
        """保存人臉截圖"""
        try:
            x, y, w, h = bbox

            # 擴展邊界框以包含更多上下文
            padding = 20
            height, width = frame.shape[:2]

            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(width, x + w + padding)
            y2 = min(height, y + h + padding)

            # 提取人臉區域
            face_region = frame[y1:y2, x1:x2]

            # 生成文件名
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"face_{person_id}_{timestamp_str}.jpg"

            # 創建目錄
            face_images_dir = self.records_dir / "images" / person_id
            face_images_dir.mkdir(parents=True, exist_ok=True)

            # 保存圖片
            image_path = face_images_dir / filename
            cv2.imwrite(str(image_path), face_region)

            logger.debug(f"Saved face screenshot: {image_path}")
            return str(image_path)

        except Exception as e:
            logger.error(f"Failed to save face screenshot: {e}")
            return None

    def _save_detection_record(self, record: FaceDetectionRecord) -> None:
        """保存檢測記錄到JSON文件（線程安全）"""
        try:
            # 按日期組織記錄文件
            date_str = datetime.fromisoformat(record.detection_time).strftime("%Y-%m-%d")
            records_file = self.records_dir / f"detections_{date_str}.json"

            # 使用锁保护文件读写操作，防止并发写入导致 JSON 损坏
            with self._lock:
                # 讀取現有記錄
                records = []
                if records_file.exists():
                    try:
                        with open(records_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                records = json.loads(content)
                    except json.JSONDecodeError as e:
                        # JSON 文件损坏，备份并重新开始
                        logger.warning(f"Corrupted JSON file detected: {records_file}, backing up and starting fresh")
                        backup_file = records_file.with_suffix('.json.backup')
                        if records_file.exists():
                            import shutil
                            shutil.copy(records_file, backup_file)
                        records = []

                # 添加新記錄
                records.append(record.to_dict())

                # 使用临时文件+原子重命名来保证写入安全
                import tempfile
                import os
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=records_file.parent,
                    suffix='.tmp',
                    text=True
                )

                try:
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        json.dump(records, f, indent=2, ensure_ascii=False)

                    # 原子性地替换旧文件
                    import shutil
                    shutil.move(temp_path, records_file)
                except:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise

                # 也添加到內存緩存
                self.detection_records.append(record)
                # 限制內存中的記錄數量
                if len(self.detection_records) > 1000:
                    self.detection_records = self.detection_records[-500:]

            logger.debug(f"Saved detection record for {record.person_id}")

        except Exception as e:
            logger.error(f"Failed to save detection record: {e}")

    def _send_face_detection_notification(self, record: FaceDetectionRecord) -> None:
        """發送人臉檢測通知"""
        try:
            notification = ViolationNotification(
                timestamp=record.detection_time,
                camera_id=record.camera_id,
                violation_type="face_detection",
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

            # 添加人臉檢測特定信息
            notification_data = notification.to_dict()
            notification_data.update({
                "person_name": record.person_name,
                "detection_type": "face_recognition",
                "message": f"檢測到人員: {record.person_name} (ID: {record.person_id})"
            })

            # 發送通知
            if self.notification_sender:
                self.notification_sender.send_notification(notification_data)
                logger.info(f"Sent face detection notification for {record.person_name}")

        except Exception as e:
            logger.error(f"Failed to send face detection notification: {e}")

    def _update_stats(self, person_id: str, notification_sent: bool, person_filed: bool = False) -> None:
        """更新統計數據"""
        with self._lock:
            self.stats["total_detections"] += 1
            self.stats["records_saved"] += 1

            if notification_sent:
                self.stats["notifications_sent"] += 1

            if person_filed:
                self.stats["persons_filed"] += 1

            # 統計唯一人員數量
            unique_persons = len(self.last_notification_time)
            if person_id not in self.last_notification_time:
                unique_persons += 1
            self.stats["unique_persons_detected"] = unique_persons

    def get_detection_history(self, person_id: Optional[str] = None,
                            days: int = 7) -> List[Dict]:
        """獲取檢測歷史記錄"""
        try:
            records = []
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 遍歷指定日期範圍內的記錄文件
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                records_file = self.records_dir / f"detections_{date_str}.json"

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
            logger.error(f"Failed to get detection history: {e}")
            return []

    def get_stats(self) -> Dict:
        """獲取統計信息"""
        with self._lock:
            runtime = datetime.now() - self.stats["start_time"]
            return {
                **self.stats,
                "runtime_hours": runtime.total_seconds() / 3600,
                "notification_interval_seconds": self.notification_interval,
                "known_persons": len(self.last_notification_time)
            }

    def set_notification_interval(self, interval_seconds: int) -> None:
        """設置通知間隔"""
        if interval_seconds > 0:
            self.notification_interval = interval_seconds
            logger.info(f"Updated notification interval to {interval_seconds} seconds")
        else:
            logger.error("Notification interval must be positive")

    def reset_notification_history(self, person_id: Optional[str] = None) -> None:
        """重置通知歷史（用於測試或強制重新通知）"""
        with self._lock:
            if person_id:
                if person_id in self.last_notification_time:
                    del self.last_notification_time[person_id]
                    logger.info(f"Reset notification history for {person_id}")
            else:
                self.last_notification_time.clear()
                logger.info("Reset all notification history")

    def cleanup(self) -> None:
        """清理資源"""
        logger.info("Cleaning up Face Detection Manager")
        with self._lock:
            self.detection_records.clear()
            self.last_notification_time.clear()
            self.filed_persons.clear()