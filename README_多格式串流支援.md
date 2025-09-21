# 多格式串流支援系統

本系統已成功擴展為支援多種串流格式，包括 HTTP/HTTPS、WebRTC、HLS、DASH 和 ONVIF 等協定。

## 支援的串流格式

### 1. WEBCAM - 本地攝影機
- **描述**: 本地攝影機設備
- **用途**: 筆記本攝影機、USB 攝影機
- **狀態**: ✅ 已實作並測試通過

### 2. RTSP - 即時串流協定
- **描述**: Real Time Streaming Protocol
- **用途**: 傳統 IP 攝影機
- **狀態**: ✅ 已實作並測試通過

### 3. HTTP_MJPEG - HTTP Motion JPEG
- **描述**: HTTP Motion JPEG 串流
- **用途**: 簡單的 HTTP 串流攝影機
- **狀態**: ✅ 已實作

### 4. HLS - HTTP Live Streaming
- **描述**: Apple 開發的串流協定
- **用途**: 適應性串流，廣播應用
- **狀態**: ✅ 已實作 (需要 m3u8 套件)

### 5. DASH - Dynamic Adaptive Streaming
- **描述**: 適應性串流協定
- **用途**: 高效率串流，品質自適應
- **狀態**: ✅ 已實作

### 6. WebRTC - Web Real-Time Communication
- **描述**: 即時通訊協定，低延遲
- **用途**: 視訊會議、即時通訊
- **狀態**: ✅ 已實作 (需要 aiortc 和 websockets 套件)

### 7. ONVIF - 開放網路影像介面
- **描述**: 開放網路影像介面標準
- **用途**: 標準化 IP 攝影機連接
- **狀態**: ✅ 已實作 (需要 onvif-zeep 套件)

## 設定檔案

### streamSource.json
主要的串流來源設定檔，包含所有串流格式的設定範例：

```json
{
  "stream_sources": [
    {
      "id": "webcam_local",
      "name": "本地攝影機",
      "type": "WEBCAM",
      "location": "筆記本電腦",
      "enabled": true,
      "config": {
        "device_index": 0,
        "resolution": {"width": 1280, "height": 720},
        "fps": 30
      }
    }
    // ... 更多串流設定
  ],
  "global_settings": {
    "max_reconnect_attempts": 5,
    "reconnect_delay": 5,
    "processing_fps": 2
  }
}
```

## 安裝需求

### 基本需求 (已包含)
```bash
pip install opencv-python numpy requests
```

### 額外功能套件 (可選)
```bash
# HLS 串流支援
pip install m3u8

# WebRTC 串流支援
pip install aiortc websockets

# ONVIF 串流支援
pip install onvif-zeep
```

## 使用方式

### 1. 基本使用
```python
from src.managers.universal_stream_manager import UniversalStreamManager

# 創建串流管理器
stream_manager = UniversalStreamManager("streamSource.json")

# 載入設定
stream_manager.load_config()

# 初始化串流
stream_manager.initialize_streams()

# 啟動所有串流
stream_manager.start_all_streams()
```

### 2. 與主監控系統整合
主監控系統已更新為同時支援舊的 RTSP 管理器和新的通用串流管理器：

```python
python start_system.py
```

### 3. 測試串流
```bash
# 執行測試腳本
python test_streams_en.py
```

## 測試結果

根據最新測試：
- ✅ 本地攝影機 (WEBCAM): 成功連接並擷取畫面
- ✅ 串流管理器: 成功載入設定並管理串流
- ✅ 系統統計: 正確回報串流狀態
- ✅ 優雅停止: 正確停止所有串流

## 架構設計

### 基礎類別層次
```
BaseStream (抽象基類)
├── WebcamStream (本地攝影機)
├── RTSPStream (RTSP 協定)
├── HTTPStream (HTTP/MJPEG)
├── HLSStream (HLS 協定)
├── DASHStream (DASH 協定)
├── WebRTCStream (WebRTC 協定)
└── ONVIFStream (ONVIF 協定)
```

### 管理器層次
```
UniversalStreamManager
├── StreamFactory (串流工廠)
├── 設定載入
├── 串流生命週期管理
└── 狀態監控
```

## 新增功能

1. **統一的串流介面**: 所有串流類型使用相同的 API
2. **自動重連機制**: 網路中斷時自動嘗試重連
3. **設定驗證**: 載入前驗證串流設定的正確性
4. **詳細狀態回報**: 提供串流連接、運行狀態等詳細資訊
5. **Mock 串流**: 在缺少依賴套件時提供 Mock 串流測試
6. **靈活的設定**: 支援啟用/停用個別串流
7. **統計資訊**: 提供系統運行統計

## 相容性

- ✅ 與現有 RTSP 系統相容
- ✅ 支援舊的設定格式
- ✅ 新舊串流管理器並行運作
- ✅ 既有檢測功能不受影響

## 未來擴展

1. **串流發現**: 自動發現網路上的攝影機
2. **品質自適應**: 根據網路狀況調整串流品質
3. **負載平衡**: 在多個串流源間分配負載
4. **進階認證**: 支援更多認證機制
5. **雲端串流**: 支援雲端串流服務