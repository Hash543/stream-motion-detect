"""
WebSocket API Router for Real-time Violation Notifications
即時違規通知 WebSocket API
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

from api.database import get_db

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 連線管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """接受新的 WebSocket 連線"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """移除 WebSocket 連線"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """廣播訊息給所有連線的客戶端"""
        disconnected = []
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    disconnected.append(connection)

        # 移除斷線的連線
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """發送訊息給特定客戶端"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    def get_connection_count(self) -> int:
        """取得目前連線數量"""
        return len(self.active_connections)


# 全域連線管理器
manager = ConnectionManager()


@router.websocket("/violations")
async def websocket_violations_endpoint(websocket: WebSocket):
    """
    WebSocket 端點用於接收即時違規通知

    連線範例:
    ```javascript
    const ws = new WebSocket('ws://localhost:8282/api/ws/violations');

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Violation received:', data);

        // 處理違規通知
        if (data.type === 'violation') {
            alert(`Violation detected: ${data.data.violation_type} at ${data.data.camera_id}`);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };
    ```

    訊息格式:
    {
        "type": "violation",
        "timestamp": "2025-10-16T12:34:56.789Z",
        "data": {
            "id": 123,
            "violation_type": "no_helmet",
            "camera_id": "camera_001",
            "stream_id": "stream_001",
            "confidence": 0.95,
            "person_id": "P001",
            "severity": "高等",
            "lat": 25.033,
            "lng": 121.565,
            "address": "台北市信義區",
            "image_path": "/uploads/violations/2025-10-16/violation_123.jpg",
            "created_at": "2025-10-16T12:34:56.789Z"
        }
    }
    """
    await manager.connect(websocket)

    try:
        # 發送歡迎訊息
        await manager.send_personal_message({
            "type": "connection",
            "message": "Connected to violation notification service",
            "timestamp": datetime.now().isoformat(),
            "active_connections": manager.get_connection_count()
        }, websocket)

        # 保持連線並接收客戶端訊息 (可選)
        while True:
            data = await websocket.receive_text()

            # 處理客戶端發送的訊息 (例如: ping/pong)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def broadcast_violation(violation_data: Dict[str, Any]):
    """
    廣播違規事件給所有連線的 WebSocket 客戶端

    Args:
        violation_data: 違規資料字典，包含:
            - id: 違規事件ID
            - violation_type: 違規類型 (no_helmet, drowsiness, etc.)
            - camera_id: 攝像頭ID
            - stream_id: 串流ID
            - confidence: 信心分數
            - person_id: 人員ID (如果有的話)
            - severity: 嚴重程度
            - lat, lng: 經緯度
            - address: 地址
            - image_path: 圖片路徑
            - created_at: 建立時間

    使用範例:
    ```python
    from api.routers.websocket import broadcast_violation

    await broadcast_violation({
        "id": alert_event.id,
        "violation_type": "no_helmet",
        "camera_id": "camera_001",
        "stream_id": "stream_001",
        "confidence": 0.95,
        "person_id": "P001",
        "severity": "高等",
        "lat": 25.033,
        "lng": 121.565,
        "address": "台北市信義區",
        "image_path": "/uploads/violations/2025-10-16/violation_123.jpg",
        "created_at": datetime.now().isoformat()
    })
    ```
    """
    message = {
        "type": "violation",
        "timestamp": datetime.now().isoformat(),
        "data": violation_data
    }

    await manager.broadcast(message)
    logger.info(f"Broadcasted violation: {violation_data.get('violation_type')} from {violation_data.get('camera_id')}")


@router.get("/connections")
async def get_connection_info():
    """
    取得目前 WebSocket 連線資訊
    """
    return {
        "status": "success",
        "data": {
            "active_connections": manager.get_connection_count(),
            "timestamp": datetime.now().isoformat()
        }
    }
