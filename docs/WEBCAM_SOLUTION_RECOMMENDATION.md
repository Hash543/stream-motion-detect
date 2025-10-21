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

### ✅ 方案 A: 使用外部 RTSP 伺服器（生產環境推薦）

**使用 MediaMTX 將 Webcam 轉為 RTSP 串流：**

這是最適合生產環境的方案，將 Webcam 標準化為 RTSP 協議，與其他監控串流一致。

**實作步驟：**

1. **下載 MediaMTX**
```bash
# Windows
# 前往 https://github.com/bluenviron/mediamtx/releases
# 下載最新版 Windows 執行檔
```

2. **建立配置檔 `mediamtx.yml`**
```yaml
paths:
  webcam:
    # Windows - 使用 DirectShow
    runOnInit: ffmpeg -f dshow -i video="Integrated Camera" -f rtsp rtsp://localhost:$RTSP_PORT/$MTX_PATH
    runOnInitRestart: yes

    # 或使用 Media Foundation
    # runOnInit: ffmpeg -f dshow -video_size 1280x720 -framerate 30 -i video="你的攝影機名稱" -f rtsp rtsp://localhost:$RTSP_PORT/$MTX_PATH
```

3. **啟動 MediaMTX**
```bash
./mediamtx
```

4. **更新資料庫串流設定**
```sql
UPDATE stream_sources
SET stream_type = 'RTSP',
    url = 'rtsp://localhost:8554/webcam'
WHERE stream_id = '11223';
```

**優點：**
- ✅ 標準 RTSP 協議，與其他串流一致
- ✅ 可被多個客戶端同時讀取
- ✅ 獨立服務，可單獨重啟
- ✅ 支援 AI 偵測（透過主系統）
- ✅ 穩定性高，適合生產環境

**缺點：**
- 需要額外安裝 MediaMTX 和 FFmpeg
- 有額外延遲（約 200ms）

### 方案 B: 使用簡化版 Webcam 伺服器（僅供測試）

**注意：** 此方案僅供快速測試用途，不建議用於生產環境。建議使用方案 A（RTSP）。

**實作步驟：**

1. 啟動簡化版伺服器：
```bash
python start_api_webcam_only.py
```

2. Webcam 串流網址：
```
http://localhost:8283/video
```

**優點：**
- 實作簡單
- 即時串流
- 適合快速測試

**缺點：**
- ❌ 無 AI 偵測功能
- ❌ 無法與主系統整合
- ❌ 不適合生產環境
- ❌ 需要額外運行一個服務

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
**使用方案 B**（簡化版伺服器）
- 快速驗證 Webcam 硬體是否正常
- 測試串流基本功能
- 無 AI 負載的純串流測試

### 生產環境
**強烈推薦：方案 A（RTSP 伺服器）**

**原因：**
1. ✅ 標準化協議 - 所有串流都使用 RTSP
2. ✅ 統一管理 - 與其他監控攝影機一致
3. ✅ 支援 AI 偵測 - 透過主系統完整功能
4. ✅ 穩定可靠 - 獨立服務，故障隔離
5. ✅ 可擴展性 - 多客戶端同時存取

**不推薦：**
- ❌ 簡化版伺服器（方案 B）- 無 AI 功能，不適合生產
- ❌ 主系統直接處理 Webcam - 穩定性問題未解決

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

## 結論與實作步驟

### 生產環境建議配置

**使用 MediaMTX + 主系統的 RTSP 統一架構：**

1. **安裝 MediaMTX**
   - 下載：https://github.com/bluenviron/mediamtx/releases
   - 解壓縮到專用目錄

2. **配置 Webcam 為 RTSP 串流**
   - 建立 `mediamtx.yml` 配置檔
   - 設定 Webcam 輸入源
   - 啟動 MediaMTX 服務

3. **更新資料庫**
   ```sql
   UPDATE stream_sources
   SET stream_type = 'RTSP',
       url = 'rtsp://localhost:8554/webcam'
   WHERE stream_id = '11223';
   ```

4. **啟動主系統**
   ```bash
   python start_api_with_streaming.py
   ```

5. **驗證**
   - 檢查 RTSP 串流：`rtsp://localhost:8554/webcam`
   - 檢查 API 串流：`http://localhost:8282/api/streams/11223/video`
   - 確認 AI 偵測正常運作

### 架構圖

```
┌──────────────────────────────────────────────┐
│ MediaMTX (Port 8554)                         │
│ - 將 Webcam 轉為 RTSP 串流                   │
│ - 獨立服務，穩定可靠                         │
└──────────────────┬───────────────────────────┘
                   │ RTSP
                   ↓
┌──────────────────────────────────────────────┐
│ 主系統 (Port 8282)                           │
│ - 接收所有 RTSP 串流（包含 Webcam）          │
│ - 統一進行 AI 偵測                           │
│ - 提供 API 與串流服務                        │
└──────────────────────────────────────────────┘
```

**優勢：**
- 所有串流都使用標準 RTSP 協議
- Webcam 與其他監控設備一視同仁
- 完整的 AI 偵測功能
- 高穩定性與可維護性

---

**日期**: 2025-10-20
**狀態**: ✅ 推薦使用 RTSP 方案（方案 A）
**備註**: 簡化版伺服器（方案 B）僅供測試用途
