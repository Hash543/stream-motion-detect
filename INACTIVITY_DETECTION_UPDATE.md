# 靜止偵測時間調整說明

## 更新日期
2025-10-16

## 變更內容

### 靜止偵測 (Inactivity Detection) 時間閾值調整

**原設定**: 30 秒
**新設定**: 10 分鐘 (600 秒)

## 修改的檔案

1. `src/monitoring_system.py`
   - Line 195: `inactivity_threshold=600` (原 30)
   - Line 197: `check_interval=600` (原 30)

2. `src/managers/inactivity_detection_manager.py`
   - Line 3: 文檔說明更新為「檢測10分鐘內...」
   - Line 33-34: 類別文檔更新
   - Line 40: 預設值改為 `600`
   - Line 42: 預設值改為 `600`

## 檢測邏輯

靜止偵測觸發條件（兩個條件必須同時滿足）：

1. **無人臉**: 10 分鐘內沒有偵測到任何人臉
2. **無動作**: 10 分鐘內畫面沒有明顯動作（動作分數 < 5%）

### 檢測間隔

系統會每 10 分鐘檢查一次，避免重複觸發相同的靜止事件。

## 觸發流程

```
時間軸:
0:00 - 開始監控
0:30 - 最後一次看到人臉
1:00 - 畫面開始靜止
...
10:30 - 符合條件（距離最後人臉 10分鐘，距離最後動作 9.5分鐘）
      → 觸發靜止偵測警報
      → 建立 Alert Event (type=7)
      → 發送通知
20:30 - 若持續靜止，再次觸發（間隔 10 分鐘）
```

## Alert Event 資料

當靜止偵測觸發時，會自動建立 Alert Event：

```json
{
  "camera_id": "CAM001",
  "code": 100,  // 信心度 100% (靜止偵測必定是 1.0)
  "type": 7,    // 靜止偵測
  "length": 1920,  // 畫面寬度
  "area": 2073600, // 全畫面面積
  "time": "2025-10-16 17:30:00",
  "severity": "中等",
  "image": "./screenshots/inactivity_CAM001_20251016_173000.jpg",
  "bbox": [0, 0, 1920, 1080]  // 全畫面
}
```

## 動態調整閾值

如果需要在運行時調整靜止偵測時間，可以使用：

```python
# 透過 monitoring system
monitoring_system.inactivity_detection_manager.set_thresholds(
    inactivity_threshold=300,  # 改為 5 分鐘
    check_interval=300
)

# 或直接修改
manager = InactivityDetectionManager(
    inactivity_threshold=1800,  # 30 分鐘
    motion_threshold=5.0,
    check_interval=1800
)
```

## 測試建議

由於時間閾值從 30 秒增加到 10 分鐘，建議測試時：

### 方法 1: 使用較短的測試時間

```python
# 僅用於測試
test_manager = InactivityDetectionManager(
    inactivity_threshold=60,  # 測試用: 1 分鐘
    motion_threshold=5.0,
    check_interval=60
)
```

### 方法 2: 手動重置檢測狀態

```python
# 重置特定攝影機的檢測狀態
monitoring_system.inactivity_detection_manager.reset_camera_state("CAM001")

# 這會立即允許重新檢測，不需要等待間隔時間
```

### 方法 3: 查看檢測狀態

```python
# 取得統計資訊
stats = monitoring_system.inactivity_detection_manager.get_stats()
print(stats)

# 輸出範例:
# {
#   "total_detections": 5,
#   "tracked_cameras": 3,
#   "inactivity_threshold_seconds": 600,
#   "motion_threshold": 5.0,
#   "check_interval_seconds": 600,
#   "runtime_hours": 2.5
# }
```

## 常見問題

### Q: 為什麼要從 30 秒改為 10 分鐘？
A: 30 秒太短，容易產生誤報。10 分鐘的靜止才更符合真正的異常情況（如人員離開、設備故障等）。

### Q: 10 分鐘會不會太長？
A: 可以根據實際需求調整。建議：
- **一般監控**: 10 分鐘（600 秒）
- **重要區域**: 5 分鐘（300 秒）
- **測試環境**: 1-2 分鐘（60-120 秒）

### Q: 如果需要更快的響應時間怎麼辦？
A: 在初始化時傳入較小的值：

```python
InactivityDetectionManager(
    inactivity_threshold=180,  # 3 分鐘
    check_interval=180
)
```

### Q: 動作偵測的靈敏度如何調整？
A: 調整 `motion_threshold` 參數：
- **較低值 (2-3%)**: 更敏感，小動作也會偵測到
- **預設值 (5%)**: 平衡設定
- **較高值 (8-10%)**: 只偵測明顯動作

### Q: 檢測間隔和無活動閾值的區別？
A:
- **inactivity_threshold**: 判斷是否靜止的時間（多久沒人臉/動作算靜止）
- **check_interval**: 避免重複觸發的間隔（觸發後多久才能再次觸發）

通常這兩個值設為相同。

## 影響範圍

此變更影響：
- ✅ 靜止偵測的觸發頻率（減少誤報）
- ✅ Alert Event 的建立數量
- ✅ 通知發送頻率
- ❌ 不影響其他類型的違規偵測（helmet, drowsiness, face）

## 向後兼容性

此變更不影響 API 或資料格式，僅改變檢測邏輯的時間參數。
