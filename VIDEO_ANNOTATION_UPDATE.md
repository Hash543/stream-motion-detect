# 影像標註功能更新

## 更新日期
2025-01-XX

## 更新內容

### 1. 人臉辨識標籤顯示改善
- **問題**: 前端影像未顯示人臉辨識的信心度
- **原因**: 條件判斷 `if face.confidence:` 當 confidence 為 0 時會被視為 False
- **修改**: 改為 `if face.confidence is not None:` 確保即使信心度為 0 也會顯示

**修改檔案**: `api/routers/streams.py` (第 429-435 行)

```python
# 修改前
label = f"{face.person_id or 'Unknown'}"
if face.confidence:
    label += f" ({face.confidence:.2f})"

# 修改後
person_name = face.person_id or 'Unknown'
# 始終顯示信心度（即使是0也顯示）
if face.confidence is not None:
    label = f"{person_name} ({face.confidence:.2f})"
else:
    label = person_name
```

### 2. 安全帽檢測標籤修正
- **問題**: 程式碼使用字典格式存取 `helmet['bbox']`，但實際上 `helmet_detector.detect()` 返回 `DetectionResult` 物件
- **修改**: 改為使用物件屬性 `helmet.bbox` 和 `helmet.detection_type`

**修改檔案**: `api/routers/streams.py` (第 447-475 行)

```python
# 修改前
x, y, w, h = helmet['bbox']
has_helmet = helmet['has_helmet']
confidence = helmet['confidence']

# 修改後
x, y, w, h = helmet.bbox
is_helmet = helmet.detection_type == "helmet"
is_no_helmet = helmet.detection_type == "no_helmet"
```

## 顯示格式

### 人臉辨識標籤
- **已知人員**: `{person_id} ({confidence})`
  - 例如: `EMP001 (0.85)`
- **未知人員**: `Unknown ({confidence})`
  - 例如: `Unknown (0.45)` 或 `Unknown (0.00)`
- **框顏色**: 綠色 (0, 255, 0)
- **標籤背景**: 綠色
- **文字顏色**: 黑色

### 安全帽檢測標籤
- **有戴安全帽**: `Helmet ({confidence})`
  - 例如: `Helmet (0.92)`
  - **框顏色**: 藍色 (255, 0, 0)
- **未戴安全帽**: `No Helmet ({confidence})`
  - 例如: `No Helmet (0.88)`
  - **框顏色**: 紅色 (0, 0, 255)
- **標籤背景**: 與框同色
- **文字顏色**: 白色

### 瞌睡檢測標籤
- **瞌睡狀態**: `Drowsy ({confidence})`
  - 例如: `Drowsy (0.75)`
- **框顏色**: 橘色 (0, 165, 255)
- **標籤背景**: 橘色
- **文字顏色**: 白色

## 測試建議

### 1. 人臉辨識信心度顯示測試
```bash
# 測試場景 1: 已登記人員（高信心度）
# 預期結果: 顯示 "person_id (0.7x - 0.9x)"

# 測試場景 2: 未登記人員（低信心度）
# 預期結果: 顯示 "Unknown (0.00)" 或 "Unknown (0.xx)"

# 測試場景 3: MediaPipe fallback
# 預期結果: 顯示 "unknown (0.5x - 0.9x)"
```

### 2. 安全帽檢測顯示測試
```bash
# 測試場景 1: 正確佩戴安全帽
# 預期結果: 藍色框 + "Helmet (0.xx)"

# 測試場景 2: 未佩戴安全帽
# 預期結果: 紅色框 + "No Helmet (0.xx)"
```

### 3. 前端影像串流測試
```javascript
// 帶檢測標註的影像
fetch('/api/streams/{stream_id}/video?detection=true')

// 檢查標籤是否正確顯示：
// 1. 所有檢測類型都有信心度數值
// 2. 標籤背景顏色正確
// 3. 文字清晰可讀
```

## API 端點

### 獲取帶檢測框的影像串流
```
GET /api/streams/{stream_id}/video?detection=true
```

**參數**:
- `stream_id`: 串流ID
- `detection`: 是否顯示檢測框 (true/false)

**前端使用範例**:
```html
<!-- 帶檢測框的影像 -->
<img src="http://localhost:8282/api/streams/camera1/video?detection=true" />
```

## 相關檔案
- `api/routers/streams.py`: 影像標註邏輯
- `src/detectors/face_recognizer.py`: 人臉辨識檢測器
- `src/detectors/helmet_detector.py`: 安全帽檢測器
- `src/detectors/drowsiness_detector.py`: 瞌睡檢測器

## 注意事項

1. **信心度範圍**: 所有檢測的信心度範圍為 0.00 - 1.00
2. **標籤位置**: 標籤顯示在檢測框上方，如果空間不足則可能重疊
3. **性能影響**: 啟用 `detection=true` 會增加 CPU 負載，建議控制串流解析度和幀率
4. **顏色編碼**: OpenCV 使用 BGR 格式，注意顏色定義

## 已知問題

1. **標籤重疊**: 當多個檢測框靠近時，標籤可能會重疊
2. **字體大小**: 目前字體大小固定為 0.5，高解析度影像可能顯示過小

## 未來改進

1. 標籤位置智能調整，避免重疊
2. 根據影像解析度動態調整字體大小
3. 支援自定義顏色配置
4. 添加檢測框編號或追蹤ID
