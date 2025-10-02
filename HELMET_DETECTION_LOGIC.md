# 安全帽檢測邏輯說明

## 📋 檢測規則

### 1. 人臉前置條件
**安全帽檢測只在偵測到人臉時才會進行**

- ✅ 有人臉檢測結果 → 進行安全帽檢測
- ❌ 沒有人臉檢測結果 → 跳過安全帽檢測

**原因**: 確保安全帽違規能夠關聯到具體的人員，提高檢測準確性。

### 2. 20秒間隔控制
**同一人員的安全帽違規記錄間隔為20秒**

- 第1次檢測到違規 → 立即記錄並截圖
- 20秒內再次檢測到同一人違規 → 不記錄、不截圖
- 20秒後再次檢測到同一人違規 → 記錄並截圖

**目的**:
- 避免對同一人產生過多重複記錄
- 降低儲存空間和通知頻率
- 保持合理的違規追蹤

## 🔧 技術實作

### 檢測流程

```
1. 接收影像幀
   ↓
2. 檢查是否有人臉檢測結果
   ↓ 有              ↓ 沒有
3a. 進行安全帽檢測    3b. 跳過檢測，返回空結果
   ↓
4. 將違規與人臉關聯
   ↓
5. 檢查是否超過20秒間隔
   ↓ 是              ↓ 否
6a. 記錄+截圖+通知    6b. 僅記錄（不截圖/通知）
```

### 人臉關聯邏輯

```python
def _associate_violation_with_person(violation, face_detections):
    """
    計算違規框與人臉框的重疊度
    重疊度閾值: 30%
    """
    for face in face_detections:
        overlap_ratio = calculate_overlap(violation.bbox, face.bbox)
        if overlap_ratio > 0.3:
            return face.person_id

    return None  # 沒有足夠重疊的人臉
```

### 間隔控制邏輯

```python
def _should_take_screenshot(person_id, current_time):
    """
    檢查是否應該截圖
    """
    last_time = last_screenshot_time.get(person_id)

    if last_time is None:
        return True  # 第一次檢測

    time_diff = current_time - last_time
    return time_diff.total_seconds() >= 20  # 20秒間隔
```

## 📊 範例情境

### 情境1: 單人違規

```
時間軸:
00:00 - 檢測到人臉A + 未戴安全帽 → ✅ 記錄+截圖
00:05 - 檢測到人臉A + 未戴安全帽 → ⏭️ 跳過（未滿20秒）
00:15 - 檢測到人臉A + 未戴安全帽 → ⏭️ 跳過（未滿20秒）
00:21 - 檢測到人臉A + 未戴安全帽 → ✅ 記錄+截圖（已滿20秒）
```

### 情境2: 多人違規

```
時間軸:
00:00 - 檢測到人臉A + 未戴安全帽 → ✅ 記錄A+截圖
00:00 - 檢測到人臉B + 未戴安全帽 → ✅ 記錄B+截圖
00:10 - 檢測到人臉A + 未戴安全帽 → ⏭️ 跳過A（未滿20秒）
00:10 - 檢測到人臉B + 未戴安全帽 → ⏭️ 跳過B（未滿20秒）
00:25 - 檢測到人臉A + 未戴安全帽 → ✅ 記錄A+截圖（A已滿20秒）
00:25 - 檢測到人臉B + 未戴安全帽 → ✅ 記錄B+截圖（B已滿20秒）
```

**說明**: 每個人員獨立追蹤間隔時間

### 情境3: 沒有人臉

```
時間軸:
00:00 - 未檢測到人臉，檢測到安全帽違規 → ❌ 完全跳過
00:05 - 檢測到人臉A，檢測到安全帽違規 → ✅ 記錄+截圖
```

## 🎯 配置參數

### 間隔時間調整

在 `src/monitoring_system.py` 中:

```python
self.helmet_violation_manager = HelmetViolationManager(
    helmet_detector=self.helmet_detector,
    notification_sender=self.notification_sender,
    screenshot_manager=self.screenshot_manager,
    screenshot_interval=20  # 調整這個值（秒）
)
```

### 重疊度閾值調整

在 `src/managers/helmet_violation_manager.py` 中:

```python
def _associate_violation_with_person(self, violation, face_detections):
    # ...
    if best_overlap > 0.3:  # 調整這個閾值 (0.0 - 1.0)
        return best_person_id
```

**建議值**:
- `0.2` - 較寬鬆，可能關聯到較遠的人臉
- `0.3` - 預設值，平衡準確性
- `0.5` - 較嚴格，要求違規與人臉有明顯重疊

## 📈 統計資訊

可以透過API查詢統計資訊:

```python
stats = helmet_violation_manager.get_stats()

# 回傳內容:
{
    "total_violations": 150,        # 總違規次數
    "screenshots_taken": 45,        # 實際截圖次數
    "unique_violators": 12,         # 唯一違規人員數
    "screenshot_interval_seconds": 20,
    "known_violators": 12,          # 已知違規人員數
    "runtime_hours": 2.5
}
```

## 🧪 測試

執行測試腳本驗證邏輯:

```bash
python test_helmet_detection_with_face.py
```

測試項目:
1. ✅ 沒有人臉時不檢測
2. ✅ 有人臉時進行檢測
3. ✅ 20秒間隔控制
4. ✅ 多人獨立追蹤

## 💡 最佳實踐

### 1. 人臉識別準確性
- 確保攝影機角度能清楚拍到人臉
- 適當的光線條件
- 人員不要戴口罩或遮擋臉部

### 2. 間隔時間設定
- **5-10秒**: 高頻率監控，適合高風險區域
- **20秒**: 預設值，平衡監控和儲存
- **30-60秒**: 低頻率監控，適合一般區域

### 3. 儲存管理
```python
# 定期清理舊記錄
manager.cleanup_old_records(days=30)

# 重置特定人員的間隔
manager.reset_screenshot_history(person_id="person_001")

# 重置所有人員的間隔
manager.reset_screenshot_history()
```

## 🔄 與Rule Engine整合

Rule Engine可以進一步控制檢測行為:

```json
{
  "rule_id": "helmet_rule_001",
  "detection_types": ["helmet"],
  "stream_source_ids": ["camera_001"],
  "person_ids": null,  // 所有人員
  "confidence_threshold": 0.75,
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],  // 週一到週五
    "time_ranges": [
      {"start": "08:00", "end": "17:00"}  // 上班時間
    ]
  }
}
```

## 📞 相關檔案

- 實作: `src/managers/helmet_violation_manager.py`
- 監控系統整合: `src/monitoring_system.py`
- 測試: `test_helmet_detection_with_face.py`
- 間隔測試: `test_helmet_interval.py`

## ⚙️ 技術細節

### 執行緒安全
- 使用 `threading.Lock` 保護共享資料
- 多攝影機並行處理時的資料一致性

### 記憶體管理
- 違規記錄限制在1000筆（記憶體中）
- 超過後自動保留最近500筆
- 完整記錄儲存在檔案系統

### 檔案組織
```
data/helmet_violations/
├── violations_2024-10-01.json
├── violations_2024-10-02.json
└── violations_2024-10-03.json
```

每天一個檔案，方便管理和查詢。

---

**版本**: 1.0.0
**最後更新**: 2025-10-02
**間隔時間**: 20秒
**人臉前置條件**: 必須
