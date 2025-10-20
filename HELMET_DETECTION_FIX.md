# 安全帽檢測修復說明
# Helmet Detection Fix Documentation

## 問題描述 (Problem Description)

用戶反映以下問題：
1. 影像串流中沒有看到藍色（有安全帽）或紅色（無安全帽）檢測框
2. `violations` 資料表中沒有安全帽違規記錄
3. 沒有截圖被保存到 `screenshots` 目錄

儘管系統日誌顯示：
- ✅ 安全帽檢測模型已成功載入
- ✅ 檢測規則已啟用（`helmet` 類型）
- ✅ 人臉檢測正常運作（綠色人臉框顯示正常）

## 根本原因 (Root Cause)

在 `src/monitoring_system.py` 中，安全帽違規檢測的處理流程與其他違規類型不一致：

### 其他違規類型（正確實現）

```python
# 不活動檢測
if 'inactivity' in enabled_detection_types and self.inactivity_detection_manager:
    inactivity_detections = self.inactivity_detection_manager.process_frame(...)
    for violation in inactivity_detections:
        self._handle_violation(...)  # ✅ 呼叫完整的違規處理流程

# 瞌睡檢測
if 'drowsiness' in enabled_detection_types and self.drowsiness_detector:
    drowsiness_detections = self.drowsiness_detector.detect(frame)
    for violation in drowsiness_detections:
        self._handle_violation(...)  # ✅ 呼叫完整的違規處理流程
```

### 安全帽檢測（問題實現）

```python
# 安全帽檢測 - 原始程式碼
if 'helmet' in enabled_detection_types and self.helmet_violation_manager:
    helmet_violation_results = self.helmet_violation_manager.process_frame(...)
    if helmet_violation_results:
        logger.debug(...)  # ❌ 只記錄日誌，沒有呼叫 _handle_violation()
```

## 影響 (Impact)

因為沒有呼叫 `_handle_violation()`，安全帽違規：
- ❌ 不會被寫入資料庫 `violations` 表
- ❌ 不會創建 `alert_event` 記錄
- ❌ 不會透過 WebSocket 廣播
- ✅ 只會被保存到 JSON 文件（`data/helmet_violations/`）
- ✅ 只會在違規管理器內部處理

## 解決方案 (Solution)

### 修改檔案：`src/monitoring_system.py`

在第 373-395 行，將安全帽違規檢測改為與其他違規類型一致的處理方式：

```python
# Process helmet detection only if 'helmet' is in enabled types
if 'helmet' in enabled_detection_types and self.helmet_violation_manager:
    helmet_violation_results = self.helmet_violation_manager.process_frame(
        frame, camera_id, face_detections
    )
    if helmet_violation_results:
        logger.debug(
            f"Helmet violation results: {len(helmet_violation_results)} "
            f"violations processed with interval control"
        )
        # Handle helmet violations (create database records, alerts, etc.)
        # Only process violations that took screenshots (interval control)
        for violation_data in helmet_violation_results:
            if violation_data.get("screenshot_taken", False):
                # Create a DetectionResult object for the violation
                from .detectors.base_detector import DetectionResult
                violation = DetectionResult(
                    detection_type="helmet_violation",
                    confidence=violation_data.get("confidence", 0.0),
                    bbox=violation_data.get("bbox", (0, 0, 0, 0)),
                    additional_data=violation_data
                )
                self._handle_violation(camera_id, frame, violation, face_detections, timestamp)
```

### 修改檔案：`start_api.py`

移除對已廢棄的 `database_manager` 的引用：

```python
# 移除這行
from src.managers.database_manager import CameraRecord

# 移除這段程式碼
camera_record = CameraRecord(...)
monitoring_system.database_manager.add_camera(camera_record)
```

## 工作原理 (How It Works)

### 1. `helmet_violation_manager.process_frame()` 回傳格式

```python
{
    "person_id": "unknown_123456",
    "violation_type": "helmet_violation",
    "confidence": 0.85,
    "bbox": (x, y, w, h),
    "screenshot_taken": True,  # 是否通過間隔檢查
    "record_saved": True,
    "image_path": "/path/to/screenshot.jpg"
}
```

### 2. 只處理有截圖的違規

透過檢查 `screenshot_taken` 欄位，確保遵守截圖間隔控制（預設 5 秒）：
- 同一人員首次違規：立即處理
- 同一人員重複違規：需等待 5 秒間隔

### 3. 轉換為 `DetectionResult` 物件

將 `helmet_violation_manager` 回傳的字典轉換為 `DetectionResult` 物件，以便傳遞給 `_handle_violation()`。

### 4. 完整的違規處理流程

`_handle_violation()` 會執行：
1. ✅ 檢查規則引擎（Rule Engine）
2. ✅ 截圖（透過 `screenshot_manager`）
3. ✅ 寫入資料庫（`violations` 表）
4. ✅ 創建警報事件（`alert_event` 表）
5. ✅ 發送通知（如果規則啟用）
6. ✅ WebSocket 廣播

## 測試步驟 (Testing Steps)

### 1. 重啟系統

```bash
# 停止現有程序
taskkill //F //IM python.exe

# 啟動 API 服務
python start_api.py
```

### 2. 確認系統啟動

檢查日誌中是否有：
```
INFO - Helmet detection model loaded successfully from: default
INFO - Helmet Violation Manager initialized with 5s screenshot interval
INFO - RTSP Monitoring System started successfully
```

### 3. 測試安全帽檢測

1. **在攝影機前不戴安全帽**
2. **等待 5 秒**（截圖間隔）
3. **檢查資料庫**：
   ```bash
   curl "http://localhost:8282/api/violations/?limit=10"
   ```

### 4. 檢查影像串流

開啟瀏覽器：
```
http://localhost:8282/api/streams/camera_001/video?detection=true
```

應該看到：
- ✅ 綠色框：人臉檢測
- ✅ 藍色框：有戴安全帽
- ✅ 紅色框：沒戴安全帽

### 5. 檢查截圖

查看是否有新截圖：
```bash
ls -la screenshots/helmet_violation/
```

## 預期結果 (Expected Results)

### 資料庫記錄範例

```json
{
  "id": 1,
  "violation_type": "helmet_violation",
  "camera_id": "camera_001",
  "person_id": "unknown_123456",
  "confidence": 0.85,
  "timestamp": "2025-10-20T07:55:00",
  "image_path": "screenshots/helmet_violation/camera_001_20251020_075500_123.jpg",
  "severity": "高等",
  "bbox": {"x": 100, "y": 50, "width": 200, "height": 300}
}
```

### JSON 文件記錄

同時也會保存到 `data/helmet_violations/violations_2025-10-20.json`：
```json
{
  "person_id": "unknown_123456",
  "violation_type": "helmet_violation",
  "detection_time": "2025-10-20T07:55:00.123456",
  "confidence": 0.85,
  "camera_id": "camera_001",
  "image_path": "screenshots/helmet_violation/camera_001_20251020_075500_123.jpg",
  "bbox": [100, 50, 200, 300]
}
```

## 重要注意事項 (Important Notes)

### 1. 人臉檢測依賴

安全帽檢測**必須**先檢測到人臉才會執行：
```python
if not face_detections or len(face_detections) == 0:
    logger.debug("No faces detected, skipping helmet detection")
    return []
```

如果沒有看到藍色/紅色框，請先確認：
- ✅ 綠色人臉框是否正常顯示
- ✅ `face_recognizer` 是否正常運作

### 2. 截圖間隔控制

預設間隔為 **5 秒**（測試用），生產環境建議：
- 安全帽違規：**60 秒**
- 瞌睡檢測：**30 秒**
- 不活動檢測：**300 秒**（5 分鐘）

修改方式：
```python
# src/monitoring_system.py 第 189 行
self.helmet_violation_manager = HelmetViolationManager(
    helmet_detector=self.helmet_detector,
    notification_sender=self.notification_sender,
    screenshot_manager=self.screenshot_manager,
    screenshot_interval=60  # 改為 60 秒
)
```

### 3. 檢測信心度閾值

預設信心度閾值為 **0.7**，可以在 `config/config.json` 中調整：
```json
{
  "detection_settings": {
    "helmet_confidence_threshold": 0.7
  }
}
```

較低的閾值（如 0.5）會增加檢測靈敏度，但可能產生誤報。

## 故障排除 (Troubleshooting)

### 問題 1：仍然沒有資料庫記錄

**檢查**：
```bash
# 查看系統日誌
tail -f logs/monitoring.log | grep -i "helmet"

# 查看 API 日誌
# 在 start_api.py 的輸出中查看
```

**可能原因**：
1. 規則引擎過濾了違規（信心度太低）
2. 沒有檢測到人臉
3. 違規與人臉區域重疊度不足（< 0.3）

### 問題 2：影像串流沒有顯示檢測框

**檢查**：
```python
# api/routers/streams.py 第 448-475 行
# 確認 _draw_detections() 函數正常運作
```

**測試**：
```bash
# 直接測試檢測器
python -c "
from src.detectors.helmet_detector import HelmetDetector
import cv2
detector = HelmetDetector()
detector.load_model()
frame = cv2.imread('test_image.jpg')
detections = detector.detect(frame)
print(f'Detections: {len(detections)}')
for d in detections:
    print(f'  {d.detection_type}: {d.confidence:.2f}')
"
```

### 問題 3：監控循環崩潰

錯誤訊息：`dictionary changed size during iteration`

**原因**：在處理幀時添加新串流

**解決方案**：已在 `load_database_streams()` 中實現串流載入前檢查

## 相關文件 (Related Documentation)

- `VIOLATION_TROUBLESHOOTING.md` - 違規檢測故障排除完整指南
- `DATABASE_CONNECTION_FIX.md` - 資料庫連線問題修復
- `VIDEO_ANNOTATION_UPDATE.md` - 影像標註更新說明

## 修改歷史 (Change History)

- **2025-10-20**: 修復安全帽違規未呼叫 `_handle_violation()` 的問題
- **2025-10-20**: 移除 `start_api.py` 中對 `database_manager` 的依賴
- **2025-10-20**: 將截圖間隔從 20 秒降低到 5 秒（測試用）
