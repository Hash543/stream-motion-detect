# WEBCAM 串流問題說明

## 問題描述

在 Windows 環境下使用完整監控系統時，WEBCAM 串流會出現以下問題：

1. 程式會在啟動後不久崩潰（exit code 139 - segmentation fault）
2. 影片串流大部分時間顯示 "No frame available"
3. 單獨測試 webcam 時工作正常

## 原因分析

經過測試確認，問題是由於多個重量級函式庫在同一程序中運行導致的衝突：

- **OpenCV** (webcam 捕捉)
- **YOLOv8** (安全帽偵測)
- **MediaPipe** (瞌睡偵測)
- **TensorFlow Lite** (人臉辨識)

這些庫在多執行緒環境中可能有資源競爭或記憶體管理衝突，特別是在 Windows 平台上。

## 測試結果

### ✅ 成功的測試：
1. **test_webcam.py** - 單獨使用 OpenCV 讀取 webcam ✅
2. **start_api_webcam_only.py** - 簡化版本（僅 webcam，無 AI 模型）✅

### ❌ 失敗的情況：
- **start_api_with_streaming.py** - 完整系統（AI 模型 + webcam）❌
  - 啟動成功但隨後崩潰
  - Exit code: 139 (Segmentation Fault)

## 解決方案

### 方案 1: 使用簡化版 Webcam 伺服器（臨時方案）

使用提供的簡化版本查看 webcam 串流：

```bash
# 啟動簡化版伺服器（port 8283）
python start_api_webcam_only.py

# 訪問串流
http://localhost:8283/video

# 檢查狀態
http://localhost:8283/status
```

**優點**：
- 穩定不崩潰
- 低資源消耗
- 簡單直接

**缺點**：
- 沒有 AI 偵測功能
- 無法與主系統整合

### 方案 2: 使用外部 RTSP 伺服器（推薦）

將 webcam 轉為 RTSP 串流，然後讓主系統連接 RTSP：

#### 2.1 使用 FFmpeg

```bash
# 將 webcam 轉為 RTSP 串流
ffmpeg -f dshow -i video="你的攝影機名稱" \
       -rtsp_transport tcp -f rtsp rtsp://localhost:8554/webcam
```

#### 2.2 使用 MediaMTX (推薦)

1. 下載 [MediaMTX](https://github.com/bluenviron/mediamtx)

2. 設定檔 (mediamtx.yml):
```yaml
paths:
  webcam:
    source: v4l2:/dev/video0  # Linux
    # 或 Windows:
    source: dshow://video="Integrated Camera"
```

3. 啟動:
```bash
./mediamtx
```

4. 在資料庫中設定：
```sql
UPDATE stream_sources
SET stream_type = 'RTSP',
    url = 'rtsp://localhost:8554/webcam'
WHERE stream_id = '11223';
```

### 方案 3: 分離串流捕捉服務

建立專門的 webcam 捕捉服務：

```python
# webcam_service.py
import cv2
from flask import Flask, Response

app = Flask(__name__)
cap = cv2.VideoCapture(0)

@app.route('/stream')
def stream():
    def generate():
        while True:
            ret, frame = cap.read()
            if ret:
                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       buffer.tobytes() + b'\r\n')

    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
```

然後主系統使用 HTTP_MJPEG 類型連接：
```sql
UPDATE stream_sources
SET stream_type = 'HTTP_MJPEG',
    url = 'http://localhost:9000/stream'
WHERE stream_id = '11223';
```

### 方案 4: Lazy Loading (✅ 已實作)

**最新實作方案 - 延遲載入 AI 模型**

透過延遲載入技術,將 AI 模型的載入延後到實際需要時才進行,大幅減少啟動時的記憶體壓力。

#### 實作細節:

1. **新增 `src/detection/lazy_detector.py`**
   - 單例模式管理所有 AI 偵測器
   - 執行緒安全的延遲載入機制
   - 支援獨立卸載各個模型

2. **修改 `src/monitoring_system.py`**
   - `_initialize_detectors()` 不再立即載入模型
   - 在 `_process_frame()` 中根據偵測規則按需載入
   - 僅在需要時才載入對應的偵測器

#### 效益:

✅ **啟動速度**: 系統啟動不再需要等待所有模型載入
✅ **記憶體優化**: 初始記憶體佔用大幅降低
✅ **穩定性提升**: 避免多個重量級庫同時初始化的衝突
✅ **Webcam 穩定**: Webcam 串流可以在模型載入前開始運作

#### 使用方式:

```bash
# 系統會自動使用延遲載入
# 無需額外設定,啟動方式不變
python start_api_with_streaming.py
```

#### 日誌輸出範例:

```
2025-10-20 15:26:39 - INFO - Initializing detection managers with lazy loading...
2025-10-20 15:26:39 - INFO - ✓ Detection managers initialized (models will load on first use)
2025-10-20 15:26:39 - INFO -   - Lazy loading enabled to reduce startup memory pressure
2025-10-20 15:27:15 - INFO - Successfully connected to webcam: 11223
2025-10-20 15:27:15 - INFO - Lazy loading face recognizer for detection...
2025-10-20 15:27:15 - INFO - ✓ Face recognizer loaded successfully
```

### 方案 5: 進一步優化（待開發）

其他可能的優化方向：

1. **✅ 延遲載入模型** (已完成)
   - 只在需要時載入 AI 模型
   - 減少啟動時的記憶體壓力

2. **進程隔離**
   - 將 webcam 捕捉放在獨立進程
   - 使用 multiprocessing 或 subprocess

3. **使用 GStreamer 替代 OpenCV**
   - GStreamer 在多執行緒環境中更穩定
   - 但需要額外安裝和配置

4. **調整 OpenCV 後端**
```python
# 嘗試使用不同的 VideoCapture 後端
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # DirectShow
# 或
cap = cv2.VideoCapture(0, cv2.CAP_MSMF)   # Media Foundation
```

## 建議配置

### ✅ 推薦方案 (2025-10-20 更新)
使用 **方案 4** (Lazy Loading) - 已整合到主系統
- 無需額外設定
- 啟動速度快
- 記憶體優化
- Webcam 串流穩定

### 開發/測試環境
1. **方案 4** (Lazy Loading) - 優先推薦
2. **方案 1** (簡化版伺服器) - 單純測試 webcam
3. **方案 3** (分離服務) - 需要隔離時使用

### 生產環境
1. **方案 4** (Lazy Loading) - 建議先測試
2. **方案 2** (外部 RTSP 伺服器) - 需要更高穩定性時
   - 更穩定
   - 更易於擴展
   - 可獨立重啟串流服務

## 檔案說明

- `test_webcam.py` - Webcam 測試腳本
- `start_api_webcam_only.py` - 簡化版 webcam 伺服器（port 8283）
- `start_api_with_streaming.py` - 完整監控系統（有穩定性問題）

## 相關 Issue

- Windows OpenCV VideoCapture threading issues
- TensorFlow + OpenCV memory conflicts
- MediaPipe + OpenCV segfault

## 參考資料

- [OpenCV VideoCapture Documentation](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html)
- [MediaMTX - RTSP Server](https://github.com/bluenviron/mediamtx)
- [FFmpeg RTSP Streaming](https://trac.ffmpeg.org/wiki/StreamingGuide)
