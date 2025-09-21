# RTSP影像監控系統開發規格書

## 專案概述
開發一個後端監控系統，持續從RTSP串流收集影像，並使用AI模型進行安全帽檢測、瞌睡檢測和人臉識別，在檢測到違規情況時進行截圖並發送API通知。

## 核心功能需求

### 1. RTSP影像串流處理
- **功能**：持續從RTSP來源接收影像串流
- **技術要求**：
  - 支援多個RTSP串流同時處理
  - 處理網路中斷重連機制
  - 支援常見的RTSP格式 (H.264, H.265)
  - 影像幀率可配置 (建議1-5 FPS用於AI分析)

### 2. AI視覺檢測模組

#### 2.1 安全帽檢測
- **輸入**：影像幀
- **輸出**：每個人員的安全帽狀態 (有戴/未戴)
- **觸發條件**：檢測到未戴安全帽
- **建議模型**：YOLO系列或專門的安全帽檢測模型

#### 2.2 瞌睡檢測  
- **輸入**：人臉區域影像
- **輸出**：瞌睡狀態 (清醒/瞌睡)
- **檢測指標**：
  - 眼睛閉合時間 (EAR - Eye Aspect Ratio)
  - 頭部姿態角度
  - 持續時間閾值 (建議3-5秒)
- **觸發條件**：檢測到持續瞌睡狀態

#### 2.3 人臉身份識別
- **功能**：識別並記錄人員身份
- **技術要求**：
  - 人臉檢測與特徵提取
  - 身份比對資料庫
  - 支援新人員註冊
  - 識別信心度閾值設定

### 3. 截圖與通知系統

#### 3.1 自動截圖
- **觸發時機**：檢測到違規行為時
- **圖片要求**：
  - 高解析度原始畫面
  - 標註檢測結果 (邊界框、標籤)
  - 時間戳記疊加
  - 儲存格式：JPEG/PNG
  - 檔名格式：`{timestamp}_{camera_id}_{violation_type}.jpg`

#### 3.2 API通知機制
- **通知時機**：違規檢測 + 截圖完成後
- **API格式**：RESTful HTTP POST
- **資料結構**：
```json
{
  "timestamp": "2024-03-15T10:30:45Z",
  "camera_id": "camera_001",
  "violation_type": "no_helmet" | "drowsiness",
  "person_id": "person_123",
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

## 技術架構建議

### 後端框架
- **Python**: FastAPI 或 Flask
- **Node.js**: Express.js
- **非同步處理**: 多線程或協程處理多個RTSP串流

### AI/ML 函式庫
- **OpenCV**: 影像處理與RTSP串流
- **深度學習框架**: 
  - PyTorch + torchvision
  - TensorFlow + Keras
  - ONNX Runtime (模型推理最佳化)
- **人臉識別**: 
  - face_recognition
  - DeepFace
  - InsightFace

### 資料庫
- **人員資料**: SQLite/PostgreSQL/MySQL
- **檢測記錄**: 時序資料庫 (InfluxDB) 或關聯式資料庫
- **人臉特徵**: 向量資料庫 (Faiss, Pinecone)

### 儲存系統
- **截圖儲存**: 本地檔案系統或雲端儲存 (AWS S3, MinIO)
- **日誌記錄**: 結構化日誌 (JSON格式)

## 系統配置參數

### config.json 範例
```json
{
  "rtsp_sources": [
    {
      "id": "camera_001",
      "url": "rtsp://192.168.1.100:554/stream1",
      "location": "工廠入口"
    },
    {
      "id": "camera_002", 
      "url": "rtsp://192.168.1.101:554/stream1",
      "location": "生產線A"
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
  },
  "storage": {
    "screenshot_path": "./screenshots/",
    "max_storage_days": 30,
    "image_quality": 95
  }
}
```

## 核心程式結構

### 主要模組
1. **RTSPManager**: RTSP串流管理
2. **AIDetector**: AI檢測引擎整合
3. **HelmetDetector**: 安全帽檢測
4. **DrowsinessDetector**: 瞌睡檢測  
5. **FaceRecognizer**: 人臉識別
6. **ScreenshotManager**: 截圖處理
7. **NotificationSender**: API通知發送
8. **ConfigManager**: 設定檔管理
9. **DatabaseManager**: 資料庫操作

### 執行流程
1. 載入設定檔與AI模型
2. 初始化RTSP連接
3. 啟動影像處理循環：
   - 讀取影像幀
   - AI檢測處理
   - 違規判斷與記錄
   - 截圖與通知發送
4. 錯誤處理與重連機制
5. 資源清理與關閉

## 效能與擴展考量

### 效能優化
- **GPU加速**: CUDA支援用於AI推理
- **模型量化**: 減少記憶體使用並加速推理
- **多進程處理**: 每個攝影機使用獨立進程
- **記憶體管理**: 及時釋放處理過的影像幀

### 可擴展性
- **水平擴展**: 支援分散式部署
- **攝影機數量**: 動態新增/移除RTSP來源
- **模型更新**: 熱更新AI模型
- **API擴展**: 支援更多通知方式 (Webhook, 消息隊列)

## 開發階段規劃

### Phase 1: 基礎架構 (1-2週)
- RTSP串流處理
- 基本影像擷取與儲存
- 設定檔系統

### Phase 2: AI檢測整合 (2-3週)  
- 整合安全帽檢測模型
- 實作瞌睡檢測演算法
- 基礎人臉識別功能

### Phase 3: 通知與優化 (1-2週)
- API通知系統
- 截圖自動化
- 效能調優與測試

### Phase 4: 進階功能 (1週)
- 多攝影機支援
- 錯誤處理強化
- 監控面板 (可選)

## 測試與驗證

### 單元測試
- AI模型準確率測試
- RTSP連接穩定性測試
- API通知可靠性測試

### 整合測試
- 多攝影機並發處理
- 長時間運行穩定性
- 網路中斷恢復測試

### 效能測試
- CPU/GPU使用率監控
- 記憶體洩漏檢測
- 處理延遲測量

## 部署環境需求

### 硬體需求
- **CPU**: 多核心處理器 (建議8核心以上)
- **記憶體**: 16GB RAM 以上
- **GPU**: NVIDIA GPU (建議RTX 4060以上) 用於AI加速
- **儲存**: SSD 500GB以上 (用於截圖與日誌)
- **網路**: 千兆網路 (支援多個RTSP串流)

### 軟體環境
- **作業系統**: Ubuntu 20.04+ 或 CentOS 8+
- **Python**: 3.8+
- **CUDA**: 11.0+ (如使用GPU加速)
- **Docker**: 支援容器化部署

這份規格書提供了完整的開發指引，Claude Code可以根據這些需求協助你實作各個模組。你想要先從哪個部分開始開發呢？