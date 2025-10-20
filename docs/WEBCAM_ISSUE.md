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

### 方案 4: 優化完整系統（待開發）

可能的優化方向：

1. **延遲載入模型**
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

### 開發/測試環境
使用 **方案 1** (簡化版伺服器) 或 **方案 3** (分離服務)

### 生產環境
使用 **方案 2** (外部 RTSP 伺服器)
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
