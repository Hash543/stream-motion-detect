# 使用指南

## 快速開始

### 啟動系統

#### 方法1: 使用簡化啟動腳本（推薦）
```bash
python start_system.py
```

系統會自動：
1. 驗證設定檔
2. 檢查必要目錄
3. 載入AI模型
4. 啟動監控系統

#### 方法2: 使用完整啟動腳本
```bash
python main.py
```

### 基本命令

```bash
# 驗證設定檔格式
python main.py --validate-config

# 測試API連接
python main.py --test-connection

# 顯示系統狀態
python main.py --status

# 使用自訂設定檔
python main.py --config custom_config.json

# 設定日誌等級
python main.py --log-level DEBUG
```

## 系統配置

### 設定RTSP攝影機

編輯 `config/config.json`：

```json
{
  "rtsp_sources": [
    {
      "id": "camera_001",
      "url": "rtsp://192.168.1.100:554/stream1",
      "location": "工廠入口",
      "enabled": true
    },
    {
      "id": "camera_002",
      "url": "rtsp://192.168.1.101:554/stream1",
      "location": "生產線A",
      "enabled": true
    }
  ]
}
```

#### RTSP URL格式
```
rtsp://[username:password@]host:port/path

範例：
- rtsp://192.168.1.100:554/stream1
- rtsp://admin:password123@192.168.1.100:554/h264/ch1/main/av_stream
- rtsp://camera.example.com:8554/live
```

### 支援的串流格式

除了RTSP外，系統還支援多種串流格式（參考 `streamSource.json`）：

#### 本地攝影機
```json
{
  "id": "webcam_local",
  "type": "WEBCAM",
  "config": {
    "device_index": 0,
    "resolution": {"width": 1280, "height": 720},
    "fps": 30
  }
}
```

#### HTTP MJPEG
```json
{
  "id": "http_camera",
  "type": "HTTP_MJPEG",
  "config": {
    "url": "http://192.168.1.100/mjpeg",
    "auth": {"username": "admin", "password": "password"}
  }
}
```

#### HLS串流
```json
{
  "id": "hls_stream",
  "type": "HLS",
  "config": {
    "url": "https://example.com/stream.m3u8"
  }
}
```

### 檢測設定

```json
{
  "detection_settings": {
    "helmet_confidence_threshold": 0.7,
    "drowsiness_duration_threshold": 3.0,
    "face_recognition_threshold": 0.6,
    "processing_fps": 2
  }
}
```

#### 參數說明
- `helmet_confidence_threshold`: 安全帽檢測信心度（0-1），建議0.7-0.8
- `drowsiness_duration_threshold`: 瞌睡持續時間閾值（秒），建議3-5秒
- `face_recognition_threshold`: 人臉識別相似度閾值（0-1），建議0.6
- `processing_fps`: 處理幀率，建議1-2 FPS以平衡效能

### 通知API設定

```json
{
  "notification_api": {
    "endpoint": "https://your-server.com/api/violations",
    "timeout": 10,
    "retry_attempts": 3,
    "retry_delay": 5
  }
}
```

## 人臉識別管理

### 新增人員

```python
from src.managers.face_detection_manager import FaceDetectionManager
import cv2

# 初始化人臉識別器
face_manager = FaceDetectionManager()

# 準備人員照片（建議多張不同角度）
person_images = [
    cv2.imread("photos/person1_front.jpg"),
    cv2.imread("photos/person1_side.jpg"),
    cv2.imread("photos/person1_smile.jpg")
]

# 新增人員到資料庫
face_manager.add_person(
    person_id="emp_001",
    name="張三",
    images=person_images,
    metadata={"department": "生產部", "position": "技術員"}
)
```

### 查詢人員資訊

```python
from src.managers.database_manager import DatabaseManager

db = DatabaseManager()

# 取得所有人員
persons = db.get_all_persons()

# 取得特定人員
person = db.get_person("emp_001")

# 更新人員資訊
db.update_person("emp_001", {"status": "active"})

# 刪除人員
db.delete_person("emp_001")
```

## 違規記錄管理

### 查詢違規記錄

```python
from src.managers.database_manager import DatabaseManager
from datetime import datetime, timedelta

db = DatabaseManager()

# 查詢最近100筆違規記錄
violations = db.get_violations(limit=100)

# 查詢特定時間範圍
start_date = datetime.now() - timedelta(days=7)
violations = db.get_violations(
    start_time=start_date,
    camera_id="camera_001",
    violation_type="no_helmet"
)

# 取得違規統計
stats = db.get_violation_statistics(days=7)
print(f"安全帽違規: {stats['no_helmet']}")
print(f"瞌睡違規: {stats['drowsiness']}")
```

### 匯出違規報告

```python
import pandas as pd

# 將違規記錄匯出為CSV
violations = db.get_violations(limit=1000)
df = pd.DataFrame(violations)
df.to_csv("violations_report.csv", index=False)
```

## 監控與維護

### 查看系統日誌

```bash
# 即時查看日誌（Linux/macOS）
tail -f logs/monitoring.log

# Windows使用PowerShell
Get-Content logs/monitoring.log -Wait -Tail 50

# 查看特定日期的日誌
grep "2024-03-15" logs/monitoring.log

# 查看錯誤日誌
grep "ERROR" logs/monitoring.log
```

### 系統狀態監控

```bash
# 查看系統狀態
python main.py --status
```

輸出範例：
```
系統狀態:
- 運行時間: 2小時30分
- 處理攝影機數: 3
- 總處理幀數: 10,800
- 違規檢測數: 15
- API通知成功率: 98.5%
- CPU使用率: 45%
- 記憶體使用: 8.2GB / 16GB
```

### 清理舊資料

```python
from src.managers.database_manager import DatabaseManager

db = DatabaseManager()

# 刪除30天前的違規記錄
db.cleanup_old_violations(days=30)

# 刪除舊截圖
import os
import time
from pathlib import Path

screenshot_path = Path("screenshots")
cutoff_time = time.time() - (30 * 24 * 3600)  # 30天

for file in screenshot_path.glob("*.jpg"):
    if file.stat().st_mtime < cutoff_time:
        file.unlink()
```

## 效能調校

### GPU加速

檢查CUDA是否可用：
```bash
python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"
```

在設定檔中啟用GPU：
```json
{
  "system": {
    "use_gpu": true,
    "gpu_device": 0
  }
}
```

### 記憶體最佳化

降低處理頻率：
```json
{
  "detection_settings": {
    "processing_fps": 1
  }
}
```

調整影像解析度：
```json
{
  "rtsp_sources": [
    {
      "config": {
        "resize_width": 640,
        "resize_height": 480
      }
    }
  ]
}
```

### 網路最佳化

調整RTSP緩衝區：
```json
{
  "rtsp_settings": {
    "buffer_size": 1,
    "tcp_transport": true,
    "timeout": 10
  }
}
```

## API通知格式

### 違規通知

系統檢測到違規時會發送HTTP POST請求：

```json
{
  "timestamp": "2024-03-15T10:30:45Z",
  "camera_id": "camera_001",
  "violation_type": "no_helmet",
  "person_id": "emp_001",
  "person_name": "張三",
  "confidence": 0.95,
  "image_path": "/screenshots/20240315_103045_camera001_nohelmet.jpg",
  "image_url": "https://your-server.com/screenshots/20240315_103045_camera001_nohelmet.jpg",
  "location": {
    "x": 100,
    "y": 150,
    "width": 200,
    "height": 300
  },
  "metadata": {
    "camera_location": "工廠入口",
    "weather": "晴天"
  }
}
```

### 違規類型

- `no_helmet`: 未佩戴安全帽
- `drowsiness`: 瞌睡
- `unknown_person`: 未知人員
- `face_detected`: 人臉檢測（僅記錄）

## 測試功能

### 測試RTSP連接

```bash
python test_streams.py
```

### 測試人臉檢測

```bash
python test_face_detection.py
```

### 測試安全帽檢測間隔

```bash
python test_helmet_interval.py
```

### 測試人臉歸檔

```bash
python test_face_filing.py
```

## 常見使用情境

### 情境1: 工廠安全帽監控

設定多個攝影機監控工廠各區域：
```json
{
  "rtsp_sources": [
    {"id": "entrance", "location": "入口"},
    {"id": "production_a", "location": "生產線A"},
    {"id": "production_b", "location": "生產線B"},
    {"id": "warehouse", "location": "倉庫"}
  ],
  "detection_settings": {
    "helmet_confidence_threshold": 0.8,
    "processing_fps": 2
  }
}
```

### 情境2: 司機瞌睡監控

專注於瞌睡檢測：
```json
{
  "rtsp_sources": [
    {"id": "driver_cam", "location": "駕駛艙"}
  ],
  "detection_settings": {
    "drowsiness_duration_threshold": 2.0,
    "processing_fps": 5
  }
}
```

### 情境3: 門禁人臉識別

使用人臉識別管理進出：
```json
{
  "rtsp_sources": [
    {"id": "main_gate", "location": "主門"}
  ],
  "detection_settings": {
    "face_recognition_threshold": 0.7,
    "processing_fps": 3
  },
  "notification_api": {
    "endpoint": "https://access-control.com/api/entry"
  }
}
```

## 故障排除

### RTSP連接失敗

1. 檢查攝影機IP和連接埠
2. 確認網路連通性：`ping 192.168.1.100`
3. 測試RTSP URL：`ffplay rtsp://192.168.1.100:554/stream1`
4. 檢查防火牆設定

### AI檢測不準確

1. 調整信心度閾值
2. 檢查攝影機畫質和角度
3. 確認光線條件
4. 考慮使用自訂訓練模型

### API通知失敗

1. 測試API端點：`curl -X POST https://your-server.com/api/violations`
2. 檢查網路連接
3. 驗證API格式和認證
4. 查看日誌檔案

### 記憶體洩漏

1. 降低處理頻率
2. 減少同時處理的攝影機數量
3. 定期重啟系統
4. 檢查日誌中的異常

## 下一步

- [配置說明](configuration.md) - 詳細的配置選項
- [開發指南](development.md) - 擴充功能開發
- [API文件](api.md) - API接口說明
- [故障排除](troubleshooting.md) - 常見問題解決
