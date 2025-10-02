"""
Inactivity Detection Manager
無活動檢測管理器 - 檢測30秒內沒有人臉且沒有動作的情況
"""

import cv2
import time
import json
import logging
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass, asdict

try:
    from ..detectors.base_detector import DetectionResult
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from detectors.base_detector import DetectionResult

logger = logging.getLogger(__name__)


class InactivityDetectionManager:
    """
    無活動檢測管理器

    檢測邏輯：
    1. 30秒沒有偵測到人臉 AND
    2. 30秒沒有任何動作

    當兩個條件同時滿足時，返回 DetectionResult
    """

    def __init__(self,
                 inactivity_threshold: int = 30,    # 無活動閾值（秒）
                 motion_threshold: float = 5.0,     # 動作閾值（%）
                 check_interval: int = 30):         # 檢查間隔（秒）

        self.inactivity_threshold = inactivity_threshold
        self.motion_threshold = motion_threshold
        self.check_interval = check_interval

        # 每個攝影機的狀態
        self.camera_states: Dict[str, Dict] = {}

        # 統計數據
        self.stats = {
            "total_detections": 0,
            "start_time": datetime.now()
        }

        # 線程鎖
        self._lock = threading.Lock()

        logger.info(
            f"Inactivity Detection Manager initialized - "
            f"threshold: {inactivity_threshold}s, "
            f"motion_threshold: {motion_threshold}%, "
            f"check_interval: {check_interval}s"
        )

    def process_frame(self, frame: np.ndarray, camera_id: str,
                     face_detections: List = None) -> List[DetectionResult]:
        """
        處理單一幀，進行無活動檢測

        Args:
            frame: 影像幀
            camera_id: 攝影機ID
            face_detections: 人臉檢測結果列表

        Returns:
            List[DetectionResult]: 檢測結果列表（通常為空或包含一個inactivity結果）
        """
        try:
            current_time = datetime.now()

            # 初始化攝影機狀態
            if camera_id not in self.camera_states:
                self._initialize_camera_state(camera_id, current_time)

            camera_state = self.camera_states[camera_id]

            # 更新人臉狀態
            if face_detections and len(face_detections) > 0:
                camera_state["last_face_time"] = current_time
                logger.debug(f"[{camera_id}] Face detected, reset inactivity timer")

            # 計算動作分數
            motion_score = self._calculate_motion(frame, camera_state)

            # 更新動作狀態
            if motion_score > self.motion_threshold:
                camera_state["last_motion_time"] = current_time
                logger.debug(f"[{camera_id}] Motion detected (score: {motion_score:.2f}%)")

            # 更新前一幀
            camera_state["previous_frame"] = frame.copy()

            # 檢查是否應該進行無活動檢測
            detection_result = self._check_inactivity(
                camera_id, frame, current_time, motion_score
            )

            if detection_result:
                return [detection_result]
            else:
                return []

        except Exception as e:
            logger.error(f"Error processing frame for inactivity detection: {e}")
            return []

    def _initialize_camera_state(self, camera_id: str, current_time: datetime) -> None:
        """初始化攝影機狀態"""
        with self._lock:
            self.camera_states[camera_id] = {
                "last_face_time": current_time,
                "last_motion_time": current_time,
                "last_detection_time": None,
                "previous_frame": None,
                "motion_history": []
            }
        logger.info(f"Initialized camera state for {camera_id}")

    def _calculate_motion(self, frame: np.ndarray, camera_state: Dict) -> float:
        """
        計算畫面動作分數

        使用幀差法檢測動作

        Returns:
            動作分數（0-100），數值越大表示動作越明顯
        """
        try:
            previous_frame = camera_state.get("previous_frame")

            if previous_frame is None:
                return 0.0

            # 轉換為灰度圖
            gray1 = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 高斯模糊減少噪點
            gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
            gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

            # 計算幀差
            frame_diff = cv2.absdiff(gray1, gray2)

            # 二值化
            _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)

            # 計算變化的像素比例
            changed_pixels = np.sum(thresh > 0)
            total_pixels = thresh.shape[0] * thresh.shape[1]
            motion_ratio = (changed_pixels / total_pixels) * 100

            # 更新動作歷史（保留最近10次）
            motion_history = camera_state.get("motion_history", [])
            motion_history.append(motion_ratio)
            if len(motion_history) > 10:
                motion_history = motion_history[-10:]
            camera_state["motion_history"] = motion_history

            # 計算平均動作分數
            avg_motion = np.mean(motion_history) if motion_history else 0.0

            return avg_motion

        except Exception as e:
            logger.error(f"Error calculating motion: {e}")
            return 0.0

    def _check_inactivity(self, camera_id: str, frame: np.ndarray,
                         current_time: datetime, motion_score: float) -> Optional[DetectionResult]:
        """
        檢查是否符合無活動條件

        條件：
        1. 距離最後一次看到人臉 >= inactivity_threshold 秒
        2. 距離最後一次偵測到動作 >= inactivity_threshold 秒
        3. 距離上次檢測 >= check_interval 秒（避免重複檢測）
        """
        camera_state = self.camera_states[camera_id]

        last_face_time = camera_state["last_face_time"]
        last_motion_time = camera_state["last_motion_time"]
        last_detection_time = camera_state.get("last_detection_time")

        # 計算時間差
        time_since_face = (current_time - last_face_time).total_seconds()
        time_since_motion = (current_time - last_motion_time).total_seconds()

        # 檢查是否符合無活動條件
        no_face = time_since_face >= self.inactivity_threshold
        no_motion = time_since_motion >= self.inactivity_threshold

        if not (no_face and no_motion):
            return None

        # 檢查檢測間隔（避免重複檢測）
        if last_detection_time is not None:
            time_since_detection = (current_time - last_detection_time).total_seconds()
            if time_since_detection < self.check_interval:
                logger.debug(
                    f"[{camera_id}] Inactivity condition met but check interval not reached "
                    f"({time_since_detection:.0f}s < {self.check_interval}s)"
                )
                return None

        # 符合所有條件，觸發無活動檢測
        logger.warning(
            f"[{camera_id}] INACTIVITY DETECTED - "
            f"No face: {time_since_face:.0f}s, No motion: {time_since_motion:.0f}s"
        )

        # 更新最後檢測時間
        camera_state["last_detection_time"] = current_time

        # 更新統計
        with self._lock:
            self.stats["total_detections"] += 1

        # 創建 DetectionResult
        # bbox 設為 None 表示全畫面檢測
        detection_result = DetectionResult(
            detection_type="inactivity",
            confidence=1.0,
            bbox=(0, 0, frame.shape[1], frame.shape[0]),  # 全畫面
            additional_data={
                "time_since_face_seconds": time_since_face,
                "time_since_motion_seconds": time_since_motion,
                "motion_score": motion_score,
                "duration_seconds": int(max(time_since_face, time_since_motion))
            }
        )

        return detection_result

    def get_stats(self) -> Dict:
        """獲取統計資訊"""
        with self._lock:
            runtime = datetime.now() - self.stats["start_time"]
            return {
                **self.stats,
                "tracked_cameras": len(self.camera_states),
                "inactivity_threshold_seconds": self.inactivity_threshold,
                "motion_threshold": self.motion_threshold,
                "check_interval_seconds": self.check_interval,
                "runtime_hours": runtime.total_seconds() / 3600
            }

    def set_thresholds(self, inactivity_threshold: int = None,
                      motion_threshold: float = None,
                      check_interval: int = None) -> None:
        """設置閾值參數"""
        if inactivity_threshold is not None and inactivity_threshold > 0:
            self.inactivity_threshold = inactivity_threshold
            logger.info(f"Updated inactivity threshold to {inactivity_threshold}s")

        if motion_threshold is not None and motion_threshold > 0:
            self.motion_threshold = motion_threshold
            logger.info(f"Updated motion threshold to {motion_threshold}%")

        if check_interval is not None and check_interval > 0:
            self.check_interval = check_interval
            logger.info(f"Updated check interval to {check_interval}s")

    def reset_camera_state(self, camera_id: str = None) -> None:
        """重置攝影機狀態（用於測試或強制重新檢測）"""
        with self._lock:
            if camera_id:
                if camera_id in self.camera_states:
                    current_time = datetime.now()
                    self.camera_states[camera_id]["last_detection_time"] = None
                    logger.info(f"Reset detection state for {camera_id}")
            else:
                for state in self.camera_states.values():
                    state["last_detection_time"] = None
                logger.info("Reset all camera detection states")

    def cleanup(self) -> None:
        """清理資源"""
        logger.info("Cleaning up Inactivity Detection Manager")
        with self._lock:
            self.camera_states.clear()
