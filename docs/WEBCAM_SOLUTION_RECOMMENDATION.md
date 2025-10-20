# Webcam 串流問題解決方案建議

## 問題現況

即使實作了 Lazy Loading，Webcam 串流仍然出現以下問題：
- 長時間顯示 "no frame available"
- 偶爾短暫顯示 webcam 畫面
- 系統不穩定，容易崩潰

## 根本原因分析

問題不只是啟動時的記憶體壓力，而是**運行時的多重問題**：

1. **AI 模型處理阻塞 Webcam 讀取**
   - YOLOv8, MediaPipe, TensorFlow 同時運行
   - 每個模型處理時間 50-200ms
   - Webcam 讀取被阻塞，導致幀丟失

2. **執行緒競爭**
   - OpenCV VideoCapture 在主執行緒
   - AI 模型在多個執行緒並行
   - Windows 平台上的執行緒調度問題

3. **記憶體碎片化**
   - 頻繁的模型推論造成記憶體分配/釋放
   - Windows 記憶體管理不如 Linux 高效

## 推薦解決方案

### ✅ 方案 A: 使用簡化版 Webcam 伺服器（強烈推薦）

**優點：**
- ✅ **已驗證穩定** - 實測無崩潰
- ✅ **即時串流** - 無幀丟失
- ✅ **低資源消耗** - 僅使用 OpenCV
- ✅ **實作簡單** - 無需修改現有系統

**實作步驟：**

1. 啟動簡化版伺服器：
```bash
python start_api_webcam_only.py
```

2. Webcam 串流網址：
```
http://localhost:8283/video
```

3. 主系統串流（含 AI 偵測）：
```
http://localhost:8282/api/streams/{其他串流ID}/video
```

**架構圖：**
```
┌─────────────────────────────────────┐
│ Port 8283: 簡化版 Webcam 伺服器      │
│ - 純 OpenCV 串流                    │
│ - 無 AI 偵測                        │
│ - 穩定、即時                        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Port 8282: 主系統伺服器              │
│ - RTSP 串流 + AI 偵測               │
│ - 完整功能                          │
│ - 用於其他攝影機                    │
└─────────────────────────────────────┘
```

### 方案 B: 使用外部 RTSP 伺服器 + 主系統

**使用 MediaMTX 將 Webcam 轉為 RTSP：**

1. 下載 MediaMTX:
```bash
# Windows
https://github.com/bluenviron/mediamtx/releases
```

2. 建立配置檔 `mediamtx.yml`:
```yaml
paths:
  webcam:
    runOnInit: ffmpeg -f dshow -i video="Integrated Camera" -f rtsp rtsp://localhost:$RTSP_PORT/$MTX_PATH
    runOnInitRestart: yes
```

3. 啟動 MediaMTX:
```bash
./mediamtx
```

4. 更新資料庫串流設定:
```sql
UPDATE stream_sources
SET stream_type = 'RTSP',
    url = 'rtsp://localhost:8554/webcam'
WHERE stream_id = '11223';
```

**優點：**
- 標準 RTSP 協議
- 可被多個客戶端同時讀取
- 獨立服務，可單獨重啟

**缺點：**
- 需要額外安裝 MediaMTX
- 增加系統複雜度
- 有額外的延遲（~200ms）

### 方案 C: 調整偵測頻率（部分緩解）

如果堅持使用主系統處理 Webcam，可以嘗試降低偵測頻率：

修改 `config/config.json`:
```json
{
  "detection_settings": {
    "processing_fps": 1,  // 從 2 降到 1
    "helmet_confidence_threshold": 0.7,
    "face_recognition_threshold": 0.6,
    "drowsiness_duration_threshold": 3.0
  }
}
```

或禁用部分偵測規則：
```sql
-- 只保留人臉辨識，禁用其他
UPDATE detection_rules SET enabled = false WHERE detection_type IN ('helmet', 'drowsiness');
```

**效果：**
- 可能改善但不保證穩定
- 降低了系統功能性
- 仍可能出現間歇性問題

## 實際建議

### 開發/測試階段
**使用方案 A**（簡化版伺服器）
- 快速驗證 Webcam 功能
- 無需擔心穩定性問題
- 可專注於其他功能開發

### 生產環境
**優先順序：**
1. **方案 A**（簡化版伺服器）- 如果不需要 Webcam AI 偵測
2. **方案 B**（RTSP 伺服器）- 如果需要 Webcam AI 偵測
3. **不建議**主系統直接處理 Webcam - 穩定性問題

## 長期解決方案（待開發）

如果未來必須在主系統中整合 Webcam + AI 偵測，需要：

1. **重構架構為微服務**
   - Webcam 捕捉服務（獨立進程）
   - AI 偵測服務（獨立進程）
   - API 服務（協調進程）

2. **使用訊息佇列**
   - Redis/RabbitMQ 作為中介
   - 非同步處理 AI 偵測
   - 不阻塞 Webcam 讀取

3. **換用更高效的實作**
   - 使用 GStreamer 替代 OpenCV
   - CUDA 加速 AI 推論
   - Linux 環境（更好的多執行緒支援）

## 結論

**最務實的做法：**

```bash
# 1. 啟動簡化版 Webcam 伺服器（純串流，穩定）
python start_api_webcam_only.py

# 2. 啟動主系統（處理其他 RTSP 串流 + AI 偵測）
python start_api_with_streaming.py
```

兩個服務並行：
- **Port 8283**: Webcam 即時串流（無 AI）
- **Port 8282**: 其他串流 + AI 偵測（完整功能）

這個方案已經過測試驗證，是目前最穩定的解決方案。

---

**日期**: 2025-10-20
**狀態**: ✅ 推薦使用方案 A
