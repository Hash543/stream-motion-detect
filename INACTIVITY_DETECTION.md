# 無活動檢測說明

## 📋 檢測規則

### 雙重條件檢測
**必須同時滿足兩個條件才會觸發通知**

1. ❌ **30秒沒有偵測到人臉**
2. ❌ **30秒沒有任何動作**

只有當這兩個條件**同時**持續30秒以上，系統才會：
- 📸 截圖保存
- 📢 發送通知
- 💾 記錄事件

### 檢測邏輯

```
時間線範例：

00:00 - 偵測到人臉 + 有動作          → ✅ 正常狀態
00:10 - 沒有人臉 + 有動作            → ⏳ 累積無人臉時間
00:20 - 沒有人臉 + 沒有動作          → ⏳ 開始累積雙重條件時間
00:30 - 沒有人臉 + 沒有動作（30秒）  → 🚨 觸發無活動檢測！
00:35 - 偵測到動作                  → ✅ 重置動作計時器
01:05 - 沒有動作（30秒）但有人臉     → ⏭️ 不觸發（有人臉）
```

## 🔧 技術實作

### 動作檢測方法

使用 **Frame Differencing（幀差法）** 進行動作檢測：

```python
def _calculate_motion(self, frame, camera_state):
    """
    計算影像中的動作程度

    步驟：
    1. 轉換為灰階影像
    2. 高斯模糊（降噪）
    3. 計算與前一幀的差異
    4. 二值化處理
    5. 計算變化像素百分比
    """
    # 轉灰階
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 高斯模糊
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # 計算差異
    frame_delta = cv2.absdiff(previous_frame, gray)

    # 二值化
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

    # 計算變化百分比
    motion_score = (cv2.countNonZero(thresh) / total_pixels) * 100

    return motion_score
```

### 檢測流程

```
1. 接收影像幀
   ↓
2. 檢查是否有人臉檢測結果
   ↓ 有人臉           ↓ 無人臉
3a. 更新最後人臉時間  3b. 累積無人臉時間
   ↓                  ↓
4. 計算動作分數
   ↓ 有動作           ↓ 無動作
5a. 更新最後動作時間  5b. 累積無動作時間
   ↓                  ↓
6. 檢查是否同時滿足條件
   ↓ 是               ↓ 否
7a. 截圖+通知+記錄    7b. 繼續監控
```

### 狀態追蹤

系統為每個攝影機獨立追蹤狀態：

```python
camera_state = {
    "camera_id": "camera_001",
    "last_face_time": datetime(2025, 10, 2, 14, 30, 0),
    "last_motion_time": datetime(2025, 10, 2, 14, 29, 45),
    "previous_frame": numpy_array,
    "last_check_time": datetime(2025, 10, 2, 14, 30, 0)
}
```

### 間隔控制

避免重複通知的機制：

```python
def _should_check_inactivity(self, camera_state, current_time):
    """
    檢查是否應該進行無活動檢查

    間隔控制：預設30秒
    """
    last_check = camera_state.get("last_check_time")

    if last_check is None:
        return True

    time_diff = (current_time - last_check).total_seconds()
    return time_diff >= self.check_interval
```

## 📊 使用情境

### 情境1: 正常工作狀態

```
時間軸:
00:00 - 人員在崗位工作（有人臉 + 有動作）  → ✅ 正常
00:30 - 人員持續工作                      → ✅ 正常
01:00 - 人員持續工作                      → ✅ 正常
```

**結果**: 不觸發任何通知

### 情境2: 人員離開且無任何活動

```
時間軸:
00:00 - 人員在崗位                     → ✅ 正常
00:05 - 人員離開（無人臉 + 無動作）     → ⏳ 開始計時
00:35 - 持續無人且無動作（30秒）        → 🚨 觸發通知！
```

**結果**: 觸發無活動檢測，截圖並通知

### 情境3: 人員離開但有其他動作

```
時間軸:
00:00 - 人員在崗位                     → ✅ 正常
00:05 - 人員離開                       → ⏳ 開始計時無人臉
00:15 - 有物體移動（如風吹動簾子）      → ✅ 重置動作計時器
00:45 - 持續有人臉但無動作              → ⏭️ 不觸發（仍有動作）
```

**結果**: 不觸發（有動作跡象）

### 情境4: 人員靜止不動

```
時間軸:
00:00 - 人員在崗位但保持靜止             → ✅ 正常（有人臉）
00:30 - 人員持續靜止（無動作30秒）       → ⏭️ 不觸發（有人臉）
01:00 - 人員持續靜止                    → ⏭️ 不觸發（有人臉）
```

**結果**: 不觸發（因為偵測到人臉）

### 情境5: 多攝影機場景

```
攝影機A:
00:00 - 有人員工作                   → ✅ 正常
00:30 - 持續有人員                   → ✅ 正常

攝影機B:
00:00 - 無人且無動作                 → ⏳ 計時
00:30 - 持續無人且無動作（30秒）      → 🚨 觸發通知！
```

**結果**: 只有攝影機B觸發通知，攝影機A正常

## 🎯 配置參數

### 基本配置

在 `src/monitoring_system.py` 中：

```python
self.inactivity_detection_manager = InactivityDetectionManager(
    notification_sender=self.notification_sender,
    screenshot_manager=self.screenshot_manager,
    inactivity_threshold=30,  # 無活動閾值（秒）
    motion_threshold=5.0,     # 動作敏感度（%）
    check_interval=30         # 檢查間隔（秒）
)
```

### 參數說明

#### 1. inactivity_threshold（無活動閾值）

**定義**: 觸發通知所需的無活動持續時間

```python
inactivity_threshold=30  # 30秒
```

**建議值**:
- `10-15秒`: 高敏感度，適合需要即時反應的場景
- `30秒`: 預設值，平衡靈敏度和誤報率
- `60秒`: 低敏感度，適合容許短暫離開的場景

#### 2. motion_threshold（動作敏感度）

**定義**: 判定為「有動作」的像素變化百分比閾值

```python
motion_threshold=5.0  # 5% 的像素變化
```

**建議值**:
- `2.0-3.0`: 高敏感度，能偵測到微小動作（可能較多誤報）
- `5.0`: 預設值，適合一般場景
- `8.0-10.0`: 低敏感度，只偵測明顯動作

**調整建議**:
```python
# 環境明亮、穩定
motion_threshold=5.0

# 環境昏暗、雜訊多
motion_threshold=8.0

# 需要偵測細微動作
motion_threshold=2.0
```

#### 3. check_interval（檢查間隔）

**定義**: 兩次無活動通知之間的最小間隔時間

```python
check_interval=30  # 30秒
```

**目的**: 避免在同一場景持續無活動時重複發送通知

**建議值**:
- `與 inactivity_threshold 相同`: 一旦恢復活動再次無活動時立即通知
- `較大值（如60秒）`: 降低通知頻率

## 📈 統計資訊

### 查詢統計

```python
stats = inactivity_detection_manager.get_stats()

# 回傳內容:
{
    "total_detections": 25,              # 總檢測次數
    "screenshots_taken": 20,             # 截圖次數
    "tracked_cameras": 4,                # 追蹤的攝影機數量
    "inactivity_threshold_seconds": 30,  # 無活動閾值
    "motion_threshold": 5.0,             # 動作閾值
    "check_interval_seconds": 30,        # 檢查間隔
    "runtime_hours": 3.5                 # 運行時數
}
```

### 歷史記錄查詢

```python
# 查詢最近7天的記錄
history = inactivity_detection_manager.get_detection_history(days=7)

# 查詢特定攝影機的記錄
history = inactivity_detection_manager.get_detection_history(
    camera_id="camera_001",
    days=30
)
```

## 🧪 測試

### 執行測試腳本

```bash
python test_inactivity_detection.py
```

### 測試項目

測試腳本會驗證以下功能：

1. ✅ **無活動檢測**: 30秒無人臉且無動作時觸發
2. ✅ **動作防止檢測**: 有動作時不觸發
3. ✅ **人臉防止檢測**: 有人臉時不觸發
4. ✅ **間隔控制**: 避免重複通知
5. ✅ **多攝影機追蹤**: 各攝影機獨立追蹤
6. ✅ **統計資訊**: 正確記錄統計數據

### 測試結果範例

```
==================================================================
無活動檢測測試
規則:
1. 30秒沒有偵測到人臉 + 30秒沒有動作 → 觸發通知
2. 有人臉或有動作 → 不觸發
3. 檢測間隔控制（避免重複通知）
4. 多攝影機獨立追蹤
==================================================================

[PASS] 無活動檢測
[PASS] 動作防止檢測
[PASS] 人臉防止檢測
[PASS] 間隔控制
[PASS] 多攝影機追蹤
[PASS] 統計資訊

==================================================================
測試完成: 6/6 通過 (100.0%)
==================================================================
```

## 💡 最佳實踐

### 1. 環境設置

**攝影機位置**:
- 確保攝影機能清楚拍攝到工作區域
- 避免強烈背光或反光
- 固定攝影機位置（避免晃動造成誤判）

**光線條件**:
- 穩定的光源（避免忽明忽暗）
- 避免陰影移動（如窗外樹影）
- 如環境光線變化大，調高 `motion_threshold`

### 2. 參數調優

**初始設定** (適合大多數場景):
```python
InactivityDetectionManager(
    inactivity_threshold=30,
    motion_threshold=5.0,
    check_interval=30
)
```

**高敏感度設定** (重要監控區域):
```python
InactivityDetectionManager(
    inactivity_threshold=15,
    motion_threshold=3.0,
    check_interval=15
)
```

**低誤報設定** (容許短暫離開):
```python
InactivityDetectionManager(
    inactivity_threshold=60,
    motion_threshold=8.0,
    check_interval=60
)
```

### 3. 動作閾值調整策略

**步驟1**: 使用預設值（5.0）開始測試

**步驟2**: 觀察日誌中的 `motion_score` 值
```
DEBUG - Motion detected: score=8.5%
DEBUG - No significant motion: score=2.1%
```

**步驟3**: 根據實際場景調整
```python
# 如果經常誤判為有動作（score 在 3-5% 之間）
motion_threshold=6.0  # 提高閾值

# 如果無法偵測到實際動作（score 在 8-10% 之間）
motion_threshold=3.0  # 降低閾值
```

### 4. 特殊場景處理

**場景: 戶外監控（風吹樹葉）**
```python
# 提高動作閾值，避免環境因素觸發
motion_threshold=10.0
```

**場景: 值班室監控（人員可能靜止）**
```python
# 降低動作閾值，能偵測到微小動作
motion_threshold=2.0
# 但保持較長的無活動閾值
inactivity_threshold=60
```

**場景: 無人倉庫監控**
```python
# 短時間無活動即通知
inactivity_threshold=10
# 低動作閾值
motion_threshold=3.0
```

## 🔄 與其他檢測整合

### 與人臉檢測整合

```python
# 在 monitoring_system.py 中
face_detections = self.face_detection_manager.process_frame(frame)

# 將人臉檢測結果傳入
inactivity_result = self.inactivity_detection_manager.process_frame(
    frame=frame,
    camera_id=camera_id,
    face_detections=face_detections  # 傳入人臉檢測結果
)
```

### 與Rule Engine整合

可透過Rule Engine控制無活動檢測的啟用範圍：

```json
{
  "rule_id": "inactivity_rule_001",
  "detection_types": ["inactivity"],
  "stream_source_ids": ["camera_001", "camera_002"],
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],
    "time_ranges": [
      {"start": "08:00", "end": "18:00"}
    ]
  }
}
```

## 📁 相關檔案

- **實作**: `src/managers/inactivity_detection_manager.py`
- **監控系統整合**: `src/monitoring_system.py`
- **測試**: `test_inactivity_detection.py`
- **說明文件**: 本檔案

## 📊 檔案組織

檢測記錄儲存結構：

```
data/inactivity_detections/
├── detections_2025-10-01.json
├── detections_2025-10-02.json
└── detections_2025-10-03.json
```

每個記錄包含：

```json
{
  "detection_time": "2025-10-02T14:30:45.123456",
  "camera_id": "camera_001",
  "time_since_face_seconds": 35.5,
  "time_since_motion_seconds": 32.1,
  "motion_score": 1.2,
  "image_path": "screenshots/inactivity_camera_001_20251002_143045.jpg"
}
```

## ⚙️ 技術細節

### 執行緒安全

- 使用 `threading.Lock` 保護共享資料
- 多攝影機並行處理時的資料一致性

### 記憶體管理

- 只保留最近一幀用於動作檢測
- 檢測記錄限制在1000筆（記憶體中）
- 完整記錄儲存在檔案系統

### 效能考量

**Frame Differencing 優點**:
- 計算簡單快速
- 低CPU使用率
- 適合即時處理

**潛在問題與解決**:
```python
# 問題: 攝影機晃動造成誤判
# 解決: 使用影像穩定或提高動作閾值

# 問題: 光線變化造成誤判
# 解決: 調整二值化閾值或使用背景減除法
```

## 🔍 故障排除

### 問題1: 一直觸發誤報

**可能原因**:
- 動作閾值太低
- 攝影機不穩定
- 光線變化

**解決方法**:
```python
# 提高動作閾值
motion_threshold=8.0

# 檢查日誌中的 motion_score
# 如果持續在 5-8% 之間，說明環境有持續小幅變化
```

### 問題2: 無法偵測到無活動狀態

**可能原因**:
- 動作閾值太高
- 有持續的微小動作（如風扇、螢幕閃爍）

**解決方法**:
```python
# 降低動作閾值
motion_threshold=3.0

# 檢查攝影機視野中是否有持續移動的物體
```

### 問題3: 有人臉但仍觸發檢測

**可能原因**:
- 人臉檢測失敗
- 人臉被遮擋

**解決方法**:
- 檢查人臉檢測模組是否正常運作
- 確保攝影機角度能清楚拍到人臉
- 確保光線充足

---

**版本**: 1.0.0
**最後更新**: 2025-10-02
**無活動閾值**: 30秒（可配置）
**動作閾值**: 5.0%（可配置）
**檢查間隔**: 30秒（可配置）
