# RTSP影像監控系統

一個基於Python的即時影像監控系統，支援RTSP串流處理、AI視覺檢測（安全帽檢測、瞌睡檢測、人臉識別）、自動截圖與API通知功能。

## 主要功能

### 🎥 RTSP串流處理
- 支援多個RTSP串流同時處理
- 自動重連機制處理網路中斷
- 支援H.264、H.265格式
- 可配置處理幀率

### 🤖 AI視覺檢測
- **安全帽檢測**: 使用YOLO模型檢測工作人員是否佩戴安全帽
- **瞌睡檢測**: 基於眼部閉合率(EAR)和頭部姿態檢測瞌睡狀態
- **人臉識別**: 支援人員身份識別和註冊管理

### 📸 自動截圖與通知
- 違規行為自動截圖並標註
- RESTful API即時通知
- 可配置重試機制
- 支援同步/非同步發送模式

### 💾 資料管理
- SQLite資料庫儲存違規記錄
- 人員資訊管理
- 攝影機設定管理
- 統計資料分析

## 系統架構

```
stream-motion-detect/
├── config/                 # 設定檔
│   └── config.json
├── src/                    # 原始碼
│   ├── managers/           # 管理模組
│   │   ├── config_manager.py
│   │   ├── rtsp_manager.py
│   │   ├── screenshot_manager.py
│   │   ├── notification_sender.py
│   │   └── database_manager.py
│   ├── detectors/          # AI檢測模組
│   │   ├── base_detector.py
│   │   ├── helmet_detector.py
│   │   ├── drowsiness_detector.py
│   │   └── face_recognizer.py
│   └── monitoring_system.py
├── screenshots/            # 截圖儲存目錄
├── logs/                   # 日誌檔案
├── models/                 # AI模型檔案
├── data/                   # 資料庫檔案
├── main.py                 # 主程式進入點
├── requirements.txt        # Python套件需求
└── README.md
```

## 安裝步驟

### 1. 系統需求
- Python 3.8+
- NVIDIA GPU (建議，用於AI加速)
- 16GB RAM 以上
- 500GB+ 儲存空間

### 2. 安裝Python套件
```bash
pip install -r requirements.txt
```

### 3. 下載AI模型 (可選)
- 安全帽檢測模型: 放置於 `models/helmet_detection.pt`
- 人臉識別模型: 系統會自動使用 face_recognition 套件

### 4. 設定系統配置
編輯 `config/config.json` 設定檔：

```json
{
  "rtsp_sources": [
    {
      "id": "camera_001",
      "url": "rtsp://192.168.1.100:554/stream1",
      "location": "工廠入口"
    }
  ],
  "detection_settings": {
    "helmet_confidence_threshold": 0.7,
    "drowsiness_duration_threshold": 3.0,
    "face_recognition_threshold": 0.6,
    "processing_fps": 2
  },
  "notification_api": {
    "endpoint": "https://your-server.com/api/violations",
    "timeout": 10,
    "retry_attempts": 3
  }
}
```

## 使用方法

### 基本使用
```bash
# 啟動監控系統
python main.py

# 使用自訂設定檔
python main.py --config custom_config.json

# 設定日誌等級
python main.py --log-level DEBUG
```

### 系統管理指令
```bash
# 驗證設定檔格式
python main.py --validate-config

# 測試通知API連接
python main.py --test-connection

# 顯示系統狀態
python main.py --status
```

### 人臉識別設定
```python
from src.detectors.face_recognizer import FaceRecognizer
import cv2

# 初始化人臉識別器
face_recognizer = FaceRecognizer()
face_recognizer.load_model()

# 新增人員
person_images = [cv2.imread("person1_photo1.jpg"), cv2.imread("person1_photo2.jpg")]
face_recognizer.add_person("emp_001", "張三", person_images, {"department": "生產部"})
```

## API通知格式

系統檢測到違規時會發送以下格式的HTTP POST請求：

```json
{
  "timestamp": "2024-03-15T10:30:45Z",
  "camera_id": "camera_001",
  "violation_type": "no_helmet",
  "person_id": "emp_001",
  "confidence": 0.95,
  "image_path": "/screenshots/20240315_103045_camera001_nohelmet.jpg",
  "location": {
    "x": 100,
    "y": 150,
    "width": 200,
    "height": 300
  }
}
```

## 檢測類型

### 安全帽檢測
- `helmet_violation`: 檢測到未佩戴安全帽的人員
- 置信度閾值可調整
- 支援多人同時檢測

### 瞌睡檢測
- `drowsiness`: 檢測到瞌睡狀態
- 基於眼部閉合率(EAR)和持續時間
- 可調整瞌睡判定時間閾值

### 人臉識別
- `face`: 識別到的人臉
- 支援未知人員檢測
- 可管理人員資料庫

## 資料庫結構

系統使用SQLite資料庫儲存以下資料：

- **violations**: 違規記錄
- **persons**: 人員資訊
- **cameras**: 攝影機設定

### 查詢範例
```python
from src.managers.database_manager import DatabaseManager

db = DatabaseManager()

# 查詢最近7天的違規記錄
violations = db.get_violations(limit=100)

# 查詢特定攝影機的違規統計
stats = db.get_violation_statistics(days=7)
```

## 效能調校

### GPU加速
```bash
# 檢查CUDA是否可用
python -c "import torch; print(torch.cuda.is_available())"
```

### 記憶體最佳化
- 調整 `processing_fps` 降低處理頻率
- 定期清理舊的截圖檔案
- 設定合適的資料庫清理週期

### 網路最佳化
- 使用較低的RTSP串流解析度
- 調整 `notification_api.timeout` 設定
- 啟用非同步通知模式

## 故障排除

### 常見問題

1. **RTSP連接失敗**
   ```
   解決方案：檢查網路連接、RTSP URL格式、攝影機設定
   ```

2. **AI模型載入失敗**
   ```
   解決方案：確認模型檔案路徑、檢查Python套件版本
   ```

3. **通知API發送失敗**
   ```
   解決方案：測試API端點、檢查網路連接、驗證API格式
   ```

### 日誌檔案位置
- 系統日誌: `logs/monitoring.log`
- 錯誤追蹤: 程式會輸出詳細的錯誤資訊

## 開發資訊

### 擴展功能
系統採用模組化設計，可以輕鬆添加新的檢測功能：

1. 繼承 `AIDetector` 基礎類別
2. 實作 `detect()` 方法
3. 在 `MonitoringSystem` 中註冊新檢測器

### 測試
```bash
# 驗證設定檔
python main.py --validate-config

# 測試單一模組
python -m pytest tests/
```

## 授權條款

本專案採用 MIT 授權條款，詳見 LICENSE 檔案。

## 技術支援

如有問題或建議，請透過以下方式聯絡：
- 建立 GitHub Issue
- 提交 Pull Request
- 聯絡系統開發團隊

---

**注意**: 首次使用前請務必測試RTSP連接和API通知功能，確保系統正常運作。