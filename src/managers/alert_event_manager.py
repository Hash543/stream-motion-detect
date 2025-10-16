"""
Alert Event Manager
處理將違規事件插入到 alert_event 表
"""

import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

logger = logging.getLogger(__name__)


class AlertEventManager:
    """管理 Alert Event 的建立和發送"""

    def __init__(self, api_base_url: str = None, api_token: str = None):
        """
        初始化 Alert Event Manager

        Args:
            api_base_url: API 基礎 URL，例如 http://localhost:8282
            api_token: API 認證 token (可選)
        """
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:8282")
        self.api_token = api_token or os.getenv("API_TOKEN")
        self.api_endpoint = f"{self.api_base_url}/api/alertEvent/add"

        logger.info(f"AlertEventManager initialized with endpoint: {self.api_endpoint}")

    def create_alert_event(
        self,
        camera_id: str,
        violation_type: str,
        confidence: float,
        image_path: str,
        bbox: Optional[tuple] = None,
        person_id: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        address: Optional[str] = "",
        severity: Optional[str] = "中等",
        uIds: Optional[List[int]] = None,
        oIds: Optional[List[int]] = None,
        report_status: Optional[int] = None
    ) -> bool:
        """
        建立並發送 Alert Event

        Args:
            camera_id: 攝影機 ID
            violation_type: 違規類型 (helmet, drowsiness, inactivity, face)
            confidence: 信心度
            image_path: 截圖路徑
            bbox: 邊界框 (x, y, w, h)
            person_id: 人員 ID (可選)
            lat: 緯度
            lng: 經度
            address: 地址 (空字串時會自動解析)
            severity: 嚴重程度 (低等/中等/高等)
            uIds: 分配的使用者 ID 列表
            oIds: 分配的組織 ID 列表
            report_status: 報告狀態 (1:未處理, 2:處理中, 3:已處理)

        Returns:
            bool: 是否成功建立
        """
        try:
            # 映射違規類型到代碼
            type_code_map = {
                "helmet": 1,      # 未戴安全帽
                "drowsiness": 2,  # 瞌睡
                "inactivity": 7,  # 靜止偵測
                "face": 3,        # 人臉識別
                "unknown": 99     # 未知類型
            }

            type_code = type_code_map.get(violation_type, 99)

            # 計算面積和長度
            area = 0
            length = 0
            if bbox:
                x, y, w, h = bbox
                area = w * h
                length = max(w, h)

            # 建立事件資料
            event_data = {
                "camera_id": camera_id,
                "code": int(confidence * 100),  # 將信心度轉為 0-100 的整數
                "type": type_code,
                "length": length,
                "area": area,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "severity": severity,
                "image": image_path,
                "lat": lat,
                "lng": lng,
                "address": address or ""
            }

            # 如果有分配資訊，加入到事件資料中
            if uIds and oIds is not None and report_status:
                event_data["uIds"] = uIds
                event_data["oIds"] = oIds
                event_data["report_status"] = report_status

            # 發送到 API
            headers = {
                "Content-Type": "application/json"
            }

            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            response = requests.post(
                self.api_endpoint,
                json=event_data,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Alert event created successfully: "
                    f"ID={result.get('data', {}).get('id')}, "
                    f"type={violation_type}, camera={camera_id}"
                )
                return True
            else:
                logger.error(
                    f"Failed to create alert event: "
                    f"status={response.status_code}, "
                    f"response={response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error creating alert event: {e}")
            return False

    def create_helmet_violation_event(
        self,
        camera_id: str,
        confidence: float,
        image_path: str,
        bbox: Optional[tuple] = None,
        person_id: Optional[str] = None,
        severity: str = "高等"
    ) -> bool:
        """
        建立安全帽違規事件

        Args:
            camera_id: 攝影機 ID
            confidence: 信心度
            image_path: 截圖路徑
            bbox: 邊界框
            person_id: 人員 ID
            severity: 嚴重程度 (預設: 高等)
        """
        return self.create_alert_event(
            camera_id=camera_id,
            violation_type="helmet",
            confidence=confidence,
            image_path=image_path,
            bbox=bbox,
            person_id=person_id,
            severity=severity
        )

    def create_drowsiness_violation_event(
        self,
        camera_id: str,
        confidence: float,
        image_path: str,
        bbox: Optional[tuple] = None,
        person_id: Optional[str] = None,
        severity: str = "高等"
    ) -> bool:
        """
        建立瞌睡違規事件

        Args:
            camera_id: 攝影機 ID
            confidence: 信心度
            image_path: 截圖路徑
            bbox: 邊界框
            person_id: 人員 ID
            severity: 嚴重程度 (預設: 高等)
        """
        return self.create_alert_event(
            camera_id=camera_id,
            violation_type="drowsiness",
            confidence=confidence,
            image_path=image_path,
            bbox=bbox,
            person_id=person_id,
            severity=severity
        )

    def create_inactivity_violation_event(
        self,
        camera_id: str,
        confidence: float,
        image_path: str,
        bbox: Optional[tuple] = None,
        severity: str = "中等"
    ) -> bool:
        """
        建立靜止偵測違規事件

        Args:
            camera_id: 攝影機 ID
            confidence: 信心度
            image_path: 截圖路徑
            bbox: 邊界框
            severity: 嚴重程度 (預設: 中等)
        """
        return self.create_alert_event(
            camera_id=camera_id,
            violation_type="inactivity",
            confidence=confidence,
            image_path=image_path,
            bbox=bbox,
            severity=severity
        )

    def get_stats(self) -> Dict[str, Any]:
        """取得統計資訊"""
        return {
            "api_endpoint": self.api_endpoint,
            "has_token": bool(self.api_token)
        }
