# 開發與擴充指南

## 系統架構概述

### 核心設計理念

本系統採用模組化設計，主要分為以下幾個層次：

1. **管理層 (Managers)**: 負責資源管理和協調
2. **檢測層 (Detectors)**: AI檢測功能（預留擴充）
3. **資料層 (Database)**: 資料儲存和查詢
4. **通知層 (Notification)**: 外部API通知

### 架構圖

```
┌─────────────────────────────────────────────┐
│         MonitoringSystem (主控制器)          │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐
│ Stream  │  │Database │  │Screenshot│
│ Manager │  │ Manager │  │ Manager  │
└────┬────┘  └────┬────┘  └────┬─────┘
     │            │            │
     ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌──────────┐
│  Face   │  │ Helmet  │  │Notification│
│Detection│  │Violation│  │  Sender   │
│ Manager │  │ Manager │  └──────────┘
└─────────┘  └─────────┘
```

## 開發環境設定

### 1. 安裝開發工具

```bash
# 安裝開發依賴
pip install pytest pytest-cov black pylint mypy

# 安裝pre-commit hooks
pip install pre-commit
pre-commit install
```

### 2. 配置開發環境

創建 `.env.development` 檔案：
```bash
DEBUG=True
LOG_LEVEL=DEBUG
RTSP_URL_1=rtsp://test-camera:554/stream1
NOTIFICATION_ENDPOINT=http://localhost:8000/api/test
```

## 擴充新功能

### 添加新的檢測功能

#### 步驟1: 創建檢測管理器

在 `src/managers/` 目錄下創建新檔案，例如 `fire_detection_manager.py`：

```python
import cv2
import numpy as np
from typing import Dict, List, Optional
import logging

class FireDetectionManager:
    """火災檢測管理器"""

    def __init__(self, config: Dict = None):
        """
        初始化火災檢測管理器

        Args:
            config: 檢測設定
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)

    def load_model(self, model_path: str):
        """
        載入AI模型

        Args:
            model_path: 模型檔案路徑
        """
        try:
            # 載入你的模型（例如YOLO、TensorFlow等）
            # self.model = load_your_model(model_path)
            self.logger.info(f"火災檢測模型載入成功: {model_path}")
        except Exception as e:
            self.logger.error(f"模型載入失敗: {e}")
            raise

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        檢測火災

        Args:
            frame: 影像幀

        Returns:
            檢測結果列表，每個結果包含：
            - bbox: 邊界框 [x, y, width, height]
            - confidence: 信心度
            - type: 檢測類型
        """
        if self.model is None:
            self.logger.warning("模型未載入")
            return []

        try:
            # 執行檢測
            detections = []

            # 這裡實作你的檢測邏輯
            # results = self.model.predict(frame)

            # 範例：簡單的顏色檢測（實際應使用AI模型）
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 火焰顏色範圍（橘紅色）
            lower_fire = np.array([0, 100, 100])
            upper_fire = np.array([30, 255, 255])

            mask = cv2.inRange(hsv, lower_fire, upper_fire)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1000:  # 最小面積閾值
                    x, y, w, h = cv2.boundingRect(contour)
                    detections.append({
                        'bbox': [x, y, w, h],
                        'confidence': 0.85,  # 實際應從模型獲取
                        'type': 'fire'
                    })

            return detections

        except Exception as e:
            self.logger.error(f"火災檢測失敗: {e}")
            return []

    def process_frame(self, frame: np.ndarray, camera_id: str) -> Optional[Dict]:
        """
        處理單幀影像並返回違規資訊

        Args:
            frame: 影像幀
            camera_id: 攝影機ID

        Returns:
            違規資訊字典，如無違規則返回None
        """
        detections = self.detect(frame)

        if not detections:
            return None

        # 返回第一個檢測到的火災
        detection = detections[0]

        return {
            'camera_id': camera_id,
            'violation_type': 'fire_detected',
            'confidence': detection['confidence'],
            'bbox': detection['bbox'],
            'frame': frame
        }
```

#### 步驟2: 整合到監控系統

修改 `src/monitoring_system.py`，添加新的檢測器：

```python
from src.managers.fire_detection_manager import FireDetectionManager

class MonitoringSystem:
    def __init__(self, config_path: str = "config/config.json"):
        # 現有初始化程式碼...

        # 添加火災檢測管理器
        self.fire_detector = None
        if self.config.get('fire_detection', {}).get('enabled', False):
            self.fire_detector = FireDetectionManager(
                config=self.config.get('fire_detection', {})
            )
            if 'model_path' in self.config['fire_detection']:
                self.fire_detector.load_model(
                    self.config['fire_detection']['model_path']
                )

    def process_frame(self, camera_id: str, frame):
        """處理影像幀"""
        # 現有處理邏輯...

        # 添加火災檢測
        if self.fire_detector:
            fire_result = self.fire_detector.process_frame(frame, camera_id)
            if fire_result:
                self._handle_violation(fire_result)
```

#### 步驟3: 更新設定檔

在 `config/config.json` 添加新功能設定：

```json
{
  "fire_detection": {
    "enabled": true,
    "model_path": "models/fire_detection.pt",
    "confidence_threshold": 0.75,
    "cooldown_seconds": 30
  }
}
```

### 添加新的串流格式

#### 步驟1: 創建串流類別

在 `src/managers/universal_stream_manager.py` 中添加新的串流類別：

```python
class CustomStream(BaseStream):
    """自訂串流格式"""

    def __init__(self, stream_id: str, config: Dict):
        super().__init__(stream_id, config)
        self.custom_property = config.get('custom_property')

    def connect(self) -> bool:
        """建立連接"""
        try:
            # 實作連接邏輯
            self.logger.info(f"正在連接到自訂串流: {self.stream_id}")
            # your connection code here
            self._connected = True
            return True
        except Exception as e:
            self.logger.error(f"連接失敗: {e}")
            return False

    def read_frame(self) -> Optional[np.ndarray]:
        """讀取影像幀"""
        if not self._connected:
            return None

        try:
            # 實作讀取邏輯
            # frame = read_from_your_source()
            return frame
        except Exception as e:
            self.logger.error(f"讀取幀失敗: {e}")
            return None

    def disconnect(self):
        """斷開連接"""
        # 實作斷線邏輯
        self._connected = False
        self.logger.info(f"已斷開自訂串流: {self.stream_id}")
```

#### 步驟2: 註冊到工廠

更新 `StreamFactory` 類別：

```python
class StreamFactory:
    @staticmethod
    def create_stream(stream_type: str, stream_id: str, config: Dict) -> Optional[BaseStream]:
        stream_classes = {
            # 現有類型...
            "CUSTOM": CustomStream,
        }

        stream_class = stream_classes.get(stream_type)
        if stream_class:
            return stream_class(stream_id, config)
        return None
```

### 添加新的通知方式

#### 創建通知處理器

在 `src/managers/notification_sender.py` 中添加新方法：

```python
class NotificationSender:
    async def send_telegram_notification(self, violation_data: Dict) -> bool:
        """
        發送Telegram通知

        Args:
            violation_data: 違規資料

        Returns:
            是否發送成功
        """
        try:
            bot_token = self.config.get('telegram', {}).get('bot_token')
            chat_id = self.config.get('telegram', {}).get('chat_id')

            if not bot_token or not chat_id:
                self.logger.error("Telegram設定不完整")
                return False

            # 準備訊息
            message = f"""
            🚨 違規警報
            時間: {violation_data['timestamp']}
            攝影機: {violation_data['camera_id']}
            類型: {violation_data['violation_type']}
            信心度: {violation_data['confidence']:.2%}
            """

            # 發送訊息
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Telegram通知發送成功")
                        return True
                    else:
                        self.logger.error(f"Telegram通知失敗: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"發送Telegram通知時發生錯誤: {e}")
            return False

    async def send_notification(self, violation_data: Dict) -> bool:
        """發送通知（支援多種方式）"""
        tasks = []

        # HTTP API通知
        if self.config.get('api', {}).get('enabled', True):
            tasks.append(self.send_http_notification(violation_data))

        # Telegram通知
        if self.config.get('telegram', {}).get('enabled', False):
            tasks.append(self.send_telegram_notification(violation_data))

        # 執行所有通知
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 只要有一個成功就返回True
        return any(r is True for r in results)
```

## 資料庫擴充

### 添加新的資料表

#### 步驟1: 定義模型

創建 `src/models/equipment.py`：

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Equipment(Base):
    """設備資訊表"""
    __tablename__ = 'equipment'

    id = Column(Integer, primary_key=True)
    equipment_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50))
    location = Column(String(100))
    status = Column(String(20))  # active, maintenance, inactive
    last_check = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

#### 步驟2: 更新資料庫管理器

在 `src/managers/database_manager.py` 添加方法：

```python
def add_equipment(self, equipment_data: Dict) -> bool:
    """新增設備"""
    try:
        equipment = Equipment(
            equipment_id=equipment_data['equipment_id'],
            name=equipment_data['name'],
            type=equipment_data.get('type'),
            location=equipment_data.get('location'),
            status='active',
            created_at=datetime.now()
        )
        self.session.add(equipment)
        self.session.commit()
        return True
    except Exception as e:
        self.logger.error(f"新增設備失敗: {e}")
        self.session.rollback()
        return False

def get_equipment(self, equipment_id: str) -> Optional[Dict]:
    """取得設備資訊"""
    try:
        equipment = self.session.query(Equipment).filter_by(
            equipment_id=equipment_id
        ).first()

        if equipment:
            return {
                'equipment_id': equipment.equipment_id,
                'name': equipment.name,
                'type': equipment.type,
                'location': equipment.location,
                'status': equipment.status,
                'last_check': equipment.last_check.isoformat() if equipment.last_check else None
            }
        return None
    except Exception as e:
        self.logger.error(f"查詢設備失敗: {e}")
        return None
```

## API開發

### 創建RESTful API

使用FastAPI創建API端點：

#### 創建 `api/main.py`

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Stream Monitor API", version="1.0.0")

# 資料模型
class ViolationQuery(BaseModel):
    camera_id: Optional[str] = None
    violation_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100

class PersonCreate(BaseModel):
    person_id: str
    name: str
    department: Optional[str] = None
    position: Optional[str] = None

# API端點
@app.get("/")
def read_root():
    return {"message": "Stream Monitor API", "version": "1.0.0"}

@app.get("/api/violations")
def get_violations(query: ViolationQuery = Depends()):
    """查詢違規記錄"""
    from src.managers.database_manager import DatabaseManager

    db = DatabaseManager()
    violations = db.get_violations(
        camera_id=query.camera_id,
        violation_type=query.violation_type,
        start_time=query.start_time,
        end_time=query.end_time,
        limit=query.limit
    )

    return {"data": violations, "count": len(violations)}

@app.get("/api/statistics")
def get_statistics(days: int = 7):
    """取得統計資料"""
    from src.managers.database_manager import DatabaseManager

    db = DatabaseManager()
    stats = db.get_violation_statistics(days=days)

    return {"data": stats, "period_days": days}

@app.post("/api/persons")
def create_person(person: PersonCreate):
    """新增人員"""
    from src.managers.database_manager import DatabaseManager

    db = DatabaseManager()
    success = db.add_person({
        'person_id': person.person_id,
        'name': person.name,
        'department': person.department,
        'position': person.position
    })

    if success:
        return {"message": "Person created successfully"}
    raise HTTPException(status_code=400, detail="Failed to create person")

@app.get("/api/health")
def health_check():
    """健康檢查"""
    from src.monitoring_system import MonitoringSystem

    # 檢查系統狀態
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 啟動API服務

```bash
# 開發模式
uvicorn api.main:app --reload --port 8000

# 生產模式
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 測試開發

### 單元測試範例

創建 `tests/test_fire_detection.py`：

```python
import pytest
import numpy as np
from src.managers.fire_detection_manager import FireDetectionManager

class TestFireDetection:
    @pytest.fixture
    def detector(self):
        """測試用檢測器"""
        config = {
            'confidence_threshold': 0.7
        }
        return FireDetectionManager(config)

    def test_initialization(self, detector):
        """測試初始化"""
        assert detector is not None
        assert detector.confidence_threshold == 0.7

    def test_detect_no_fire(self, detector):
        """測試無火災情況"""
        # 創建測試影像（純藍色）
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = [255, 0, 0]  # BGR: 藍色

        detections = detector.detect(frame)
        assert len(detections) == 0

    def test_detect_fire(self, detector):
        """測試火災檢測"""
        # 創建測試影像（包含橘紅色區域）
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:200, 100:200] = [0, 69, 255]  # BGR: 橘紅色

        detections = detector.detect(frame)
        assert len(detections) > 0
        assert detections[0]['type'] == 'fire'

    def test_process_frame(self, detector):
        """測試幀處理"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:200, 100:200] = [0, 69, 255]

        result = detector.process_frame(frame, "test_camera")

        assert result is not None
        assert result['camera_id'] == "test_camera"
        assert result['violation_type'] == 'fire_detected'
        assert 'confidence' in result
        assert 'bbox' in result
```

### 執行測試

```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_fire_detection.py

# 顯示詳細輸出
pytest -v

# 產生覆蓋率報告
pytest --cov=src --cov-report=html
```

## 效能優化

### 1. 使用多進程處理

```python
from multiprocessing import Process, Queue

def process_camera(camera_config, result_queue):
    """處理單個攝影機的進程"""
    # 初始化檢測器
    # 處理串流
    # 將結果放入queue
    pass

def run_multiprocess_monitoring(cameras):
    """使用多進程處理多個攝影機"""
    processes = []
    result_queue = Queue()

    for camera in cameras:
        p = Process(target=process_camera, args=(camera, result_queue))
        p.start()
        processes.append(p)

    # 收集結果
    for p in processes:
        p.join()
```

### 2. 批次處理優化

```python
def batch_process_frames(frames: List[np.ndarray], batch_size: int = 8):
    """批次處理影像幀"""
    results = []

    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        # 批次推理
        batch_results = model.predict_batch(batch)
        results.extend(batch_results)

    return results
```

### 3. 模型量化

```python
import torch

def quantize_model(model_path: str, output_path: str):
    """量化模型以減少大小和提升速度"""
    model = torch.load(model_path)
    model.eval()

    # 動態量化
    quantized_model = torch.quantization.quantize_dynamic(
        model, {torch.nn.Linear}, dtype=torch.qint8
    )

    torch.save(quantized_model, output_path)
```

## 最佳實踐

### 1. 程式碼風格

遵循PEP 8標準：
```bash
# 格式化程式碼
black src/

# 檢查風格
flake8 src/
```

### 2. 日誌記錄

```python
import logging

# 設定日誌
logger = logging.getLogger(__name__)

# 使用適當的日誌等級
logger.debug("詳細的除錯資訊")
logger.info("一般資訊訊息")
logger.warning("警告訊息")
logger.error("錯誤訊息")
logger.critical("嚴重錯誤")
```

### 3. 錯誤處理

```python
def process_with_error_handling():
    try:
        # 主要邏輯
        result = risky_operation()
        return result
    except SpecificException as e:
        # 處理特定錯誤
        logger.error(f"發生特定錯誤: {e}")
        return None
    except Exception as e:
        # 處理通用錯誤
        logger.exception("發生未預期的錯誤")
        return None
    finally:
        # 清理資源
        cleanup_resources()
```

### 4. 配置管理

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class DetectionConfig:
    """檢測設定"""
    confidence_threshold: float = 0.7
    processing_fps: int = 2
    model_path: Optional[str] = None

    def validate(self):
        """驗證設定"""
        if not 0 < self.confidence_threshold < 1:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if self.processing_fps <= 0:
            raise ValueError("processing_fps must be positive")
```

## 貢獻指南

### 提交Pull Request流程

1. Fork專案
2. 創建功能分支：`git checkout -b feature/new-detection`
3. 提交變更：`git commit -m "Add fire detection feature"`
4. 推送分支：`git push origin feature/new-detection`
5. 創建Pull Request

### 程式碼審查清單

- [ ] 程式碼遵循PEP 8風格
- [ ] 添加了適當的測試
- [ ] 測試全部通過
- [ ] 更新了文件
- [ ] 添加了適當的日誌
- [ ] 處理了錯誤情況
- [ ] 效能考量

## 常見開發問題

### Q: 如何調試AI模型？

```python
# 啟用詳細日誌
logging.basicConfig(level=logging.DEBUG)

# 儲存中間結果
cv2.imwrite("debug_frame.jpg", frame)
cv2.imwrite("debug_detection.jpg", annotated_frame)

# 列印模型輸出
print(f"Detection results: {detections}")
```

### Q: 如何處理記憶體洩漏？

```python
import gc

def process_with_cleanup():
    try:
        # 處理邏輯
        pass
    finally:
        # 強制垃圾回收
        gc.collect()

        # 釋放OpenCV資源
        cv2.destroyAllWindows()
```

## 相關資源

- [OpenCV文件](https://docs.opencv.org/)
- [PyTorch文件](https://pytorch.org/docs/)
- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [FastAPI文件](https://fastapi.tiangolo.com/)
- [SQLAlchemy文件](https://docs.sqlalchemy.org/)

## 下一步

- [使用指南](usage.md) - 了解如何使用系統
- [部署指南](deployment.md) - 了解如何部署系統
- [API文件](api.md) - API接口說明
