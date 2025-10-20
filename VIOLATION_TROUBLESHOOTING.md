# 違規記錄故障排除指南

## 問題：沒有新的違規記錄產生

### 檢查清單

#### 1. 確認監控系統正在運行
```bash
# 檢查 API 狀態
curl http://localhost:8282/api/health

# 應該顯示:
# {"status": "healthy", "database": "connected"}
```

#### 2. 確認檢測規則已啟用
```bash
# 查詢檢測規則
curl http://localhost:8282/api/rules/

# 確認至少有一個規則的 enabled: true
```

#### 3. 確認串流正在運行
```bash
# 查詢串流狀態
curl http://localhost:8282/api/streams/

# 檢查影像串流
# 在瀏覽器開啟: http://localhost:8282/api/streams/camera_001/video?detection=true
```

#### 4. 檢查截圖間隔設定

**當前設定**:
- 安全帽違規: **20 秒** (同一人員)
- 不活動檢測: **600 秒** (10 分鐘)

這表示：
- 如果同一個人未戴安全帽，系統會在第一次檢測到後記錄，然後 **20 秒內不會再記錄同一個人**
- 如果是不同人，會立即記錄
- 不活動檢測需要 **10 分鐘沒有人臉或動作** 才會觸發

### 調整截圖間隔

#### 方法 1: 透過 API 調整（推薦）

創建測試 API 端點來調整間隔：

```python
# 在 api/routers/streams.py 或創建新的 router

@router.post("/api/debug/set-screenshot-interval")
def set_screenshot_interval(interval: int = 5):
    """調整截圖間隔（用於測試）"""
    from api.routers.streams import _monitoring_system

    if not _monitoring_system:
        return {"error": "Monitoring system not initialized"}

    if hasattr(_monitoring_system, 'helmet_violation_manager'):
        _monitoring_system.helmet_violation_manager.set_screenshot_interval(interval)
        return {
            "message": f"Screenshot interval set to {interval} seconds",
            "current_interval": interval
        }

    return {"error": "Helmet violation manager not found"}
```

使用:
```bash
# 設定為 5 秒間隔（測試用）
curl -X POST "http://localhost:8282/api/debug/set-screenshot-interval?interval=5"
```

#### 方法 2: 修改程式碼

編輯 `src/monitoring_system.py` 第 189 行:
```python
# 修改前
screenshot_interval=20  # 20 seconds

# 修改後（測試用）
screenshot_interval=5   # 5 seconds
```

重啟系統後生效。

### 測試步驟

1. **調整間隔為 5 秒**（測試用）

2. **確認有人臉檢測**
   ```bash
   # 查看影像串流，確認有綠色人臉框
   http://localhost:8282/api/streams/camera_001/video?detection=true
   ```

   ⚠️ **重要**: 安全帽檢測只在偵測到人臉時才執行

3. **測試安全帽檢測**
   - 在鏡頭前不戴安全帽
   - 觀察是否有藍色或紅色框（安全帽/無安全帽）
   - 檢查資料庫是否有新記錄

4. **查詢最近的違規記錄**
   ```bash
   curl "http://localhost:8282/api/violations/?limit=10"
   ```

5. **查看系統日誌**
   ```bash
   # 查看是否有錯誤訊息
   tail -f logs/monitoring.log
   ```

### 常見問題

#### Q1: 為什麼看不到安全帽檢測框？

**可能原因**:
1. 沒有偵測到人臉（安全帽檢測依賴人臉檢測）
2. 安全帽模型未正確載入
3. 信心度閾值太高

**解決方案**:
```bash
# 檢查模型路徑
cat config/config.json | grep helmet_model_path

# 應該是空字串（使用預設 YOLOv8）或有效路徑
```

#### Q2: 為什麼同一個人一直不記錄？

**原因**: 截圖間隔保護機制

**解決方案**: 調整間隔為較短時間（測試時可設為 5 秒）

#### Q3: 為什麼資料庫沒有記錄但檔案系統有？

**可能原因**: 違規記錄保存失敗

**檢查**:
```bash
# 檢查檔案系統記錄
ls -la data/helmet_violations/

# 檢查資料庫記錄
psql -h localhost -U face-motion -d motion-detector -c "SELECT COUNT(*) FROM violations WHERE timestamp > NOW() - INTERVAL '1 hour';"
```

#### Q4: 如何測試不活動檢測？

**方法**:
1. 調整閾值為較短時間（例如 30 秒）
2. 或等待 10 分鐘看是否觸發

編輯 `src/monitoring_system.py` 第 195-197 行:
```python
inactivity_threshold=30,  # 30 seconds (測試用)
check_interval=30         # 30 seconds (測試用)
```

### 監控指令

#### 即時監控違規記錄
```bash
# 每 5 秒查詢一次最新違規
while true; do
    echo "=== $(date) ==="
    curl -s "http://localhost:8282/api/violations/?limit=5" | python -m json.tool
    sleep 5
done
```

#### 查看檢測統計
```bash
curl http://localhost:8282/api/system/stats
```

#### 查看 WebSocket 連線
```bash
# 使用 wscat 或瀏覽器 console
wscat -c ws://localhost:8282/ws/violations

# 或在瀏覽器 console:
const ws = new WebSocket('ws://localhost:8282/ws/violations');
ws.onmessage = (e) => console.log('Violation:', JSON.parse(e.data));
```

### 建議的生產環境設定

```json
{
  "detection_settings": {
    "helmet_confidence_threshold": 0.7,
    "processing_fps": 2,
    "screenshot_intervals": {
      "helmet_violation": 60,      // 同一人 60 秒記錄一次
      "drowsiness": 30,             // 瞌睡 30 秒記錄一次
      "inactivity": 300            // 不活動 5 分鐘檢查一次
    }
  }
}
```

### 測試用設定

```json
{
  "detection_settings": {
    "helmet_confidence_threshold": 0.5,  // 降低閾值以增加檢測靈敏度
    "processing_fps": 3,                  // 提高處理頻率
    "screenshot_intervals": {
      "helmet_violation": 5,             // 5 秒測試用
      "inactivity": 30                   // 30 秒測試用
    }
  }
}
```

### 除錯技巧

1. **啟用詳細日誌**
   ```python
   # 在 src/monitoring_system.py 開頭
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **添加測試端點**
   ```python
   @router.get("/api/debug/last-detections")
   def get_last_detections():
       """查看最後的檢測結果"""
       # 返回最後幾幀的檢測結果
       pass
   ```

3. **檢查記憶體中的違規記錄**
   ```python
   # 在監控系統中添加
   def get_recent_violations(self, limit=10):
       return self.helmet_violation_manager.violation_records[-limit:]
   ```

### 聯絡資訊

如果以上方法都無法解決問題，請檢查：
1. 系統日誌: `logs/monitoring.log`
2. API 日誌: uvicorn 輸出
3. 資料庫連線狀態
4. 影像串流是否正常
