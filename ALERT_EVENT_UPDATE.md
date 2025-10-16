# Alert Event 功能更新說明

## 更新日期
2025-10-16

## 更新內容

### 1. 自動插入 Alert Event

違規發生時，系統現在會自動將資料插入到 `alert_event` 表。

#### 修改的檔案
- `src/managers/alert_event_manager.py` (新增)
- `src/monitoring_system.py`
- `api/routers/alert_event.py`

#### 違規類型映射

| 違規類型 | type 代碼 | 說明 | 觸發條件 |
|---------|----------|------|---------|
| helmet | 1 | 未戴安全帽 | 即時偵測 |
| drowsiness | 2 | 瞌睡偵測 | 即時偵測 |
| face | 3 | 人臉識別 | 即時偵測 |
| inactivity | 7 | 靜止偵測 | 10分鐘無人臉且無動作 |
| unknown | 99 | 未知類型 | - |

### 2. Alert Event API 格式更新

#### 新增事件 (POST /api/alertEvent/add)

**請求格式**:
```json
{
  "camera_id": "camera_id",
  "code": 101,
  "type": 7,
  "length": 120,
  "area": 450,
  "time": "2025-08-31 13:50:43",
  "severity": "中等",
  "image": "screenshots/violation.jpg",
  "lat": 25.0330,
  "lng": 121.5654,
  "address": "",  // 空字串時會自動依照經緯度解析地址
  // 以下為可選的自動分配參數
  "uIds": [5, 11, 12],
  "oIds": [6, 7],
  "report_status": 2  // 1:未處理, 2:處理中, 3:已處理
}
```

**回應格式**:
```json
{
  "status": "success",
  "data": {
    "id": 123,
    "created_at": "2025-10-16T17:30:00"
  }
}
```

#### 搜尋事件 (GET /api/alertEvent/search)

**新的回應格式**:
```json
{
  "status": "success",
  "data": {
    "msg": "success",
    "list": [
      {
        "id": 1,
        "camera_id": "CAM001",
        "type": "7",
        "severity": "中等",
        ...
      }
    ],
    "total": 100,
    "page": 1,
    "pageSize": 10
  }
}
```

### 3. 列表 API 格式統一

所有列表類的 API 回應格式已統一為：

```json
{
  "status": "success",
  "data": {
    "msg": "success",
    "list": [...]
  }
}
```

#### 受影響的 API
- `GET /api/alertEvent/search`
- `GET /api/violations/`
- `GET /api/alertEvent/assignedAlertEvents`

### 4. AlertEventManager 使用方式

#### 在違規處理中自動建立

違規發生時會自動調用 `AlertEventManager.create_alert_event()`：

```python
# monitoring_system.py 中
if self.alert_event_manager and image_path:
    alert_success = self.alert_event_manager.create_alert_event(
        camera_id=camera_id,
        violation_type=violation.detection_type,  # helmet, drowsiness, inactivity
        confidence=violation.confidence,
        image_path=image_path,
        bbox=violation.bbox,
        person_id=person_id
    )
```

#### 手動建立特定類型的事件

```python
from src.managers.alert_event_manager import AlertEventManager

alert_manager = AlertEventManager()

# 安全帽違規
alert_manager.create_helmet_violation_event(
    camera_id="CAM001",
    confidence=0.85,
    image_path="./screenshots/violation.jpg",
    bbox=(100, 100, 200, 200),
    person_id="PERSON001",
    severity="高等"
)

# 瞌睡違規
alert_manager.create_drowsiness_violation_event(
    camera_id="CAM001",
    confidence=0.90,
    image_path="./screenshots/drowsy.jpg",
    bbox=(100, 100, 200, 200),
    person_id="PERSON001",
    severity="高等"
)

# 靜止偵測
alert_manager.create_inactivity_violation_event(
    camera_id="CAM001",
    confidence=0.95,
    image_path="./screenshots/inactive.jpg",
    bbox=(100, 100, 200, 200),
    severity="中等"
)
```

## 配置

### 環境變數

在 `.env` 或環境變數中設定：

```env
# API 基礎 URL (AlertEventManager 使用)
API_BASE_URL=http://localhost:8282

# API 認證 Token (可選)
API_TOKEN=your_token_here
```

## 測試

執行測試腳本來驗證功能：

```bash
python scripts/test/test_alert_event_creation.py
```

測試內容包括：
1. 基本 Alert Event 建立
2. 帶自動分配的 Alert Event 建立
3. 搜尋 Alert Events (新格式)
4. Violations API 列表格式

## 嚴重程度說明

| 嚴重程度 | 說明 | 適用場景 |
|---------|------|---------|
| 低等 | 輕微違規 | 輕微不當行為 |
| 中等 | 一般違規 | 靜止偵測、輕度瞌睡 |
| 高等 | 嚴重違規 | 未戴安全帽、嚴重瞌睡 |

## 資料庫欄位對應

Alert Event 表欄位：

| 欄位 | 類型 | 說明 |
|------|------|------|
| camera_id | TEXT | 攝影機 ID |
| code | INT | 信心度 (0-100) |
| type | INT | 違規類型代碼 |
| length | INT | 邊界框長度 |
| area | INT | 邊界框面積 |
| time | DATETIME | 違規時間 |
| severity | TEXT | 嚴重程度 |
| image | TEXT | 截圖路徑 |
| lat | FLOAT | 緯度 |
| lng | FLOAT | 經度 |
| address | TEXT | 地址 |
| report_status | INT | 報告狀態 (1/2/3) |

## 注意事項

1. **地址自動解析**: 目前地址自動解析功能尚未實作 (TODO)，需要額外整合地理編碼 API

2. **API 認證**: 如果 API 需要認證，請在 `.env` 中設定 `API_TOKEN`

3. **API 可用性**: AlertEventManager 會嘗試連接 API，如果 API 不可用會記錄錯誤但不會中斷違規處理流程

4. **分配功能**: 當同時提供 `uIds`、`oIds` 和 `report_status` 時，會自動建立分配記錄到 `alert_event_assign_user` 表

## 向後兼容性

- 原有的 `Violation` 表仍然保留
- 原有的 API 端點仍然可用
- 列表 API 格式已更新，前端可能需要調整

## 遷移建議

如果前端正在使用舊的列表 API 格式，需要修改以適應新格式：

**舊格式**:
```javascript
const violations = response.data;  // 直接是陣列
```

**新格式**:
```javascript
const violations = response.data.data.list;  // 需要多層取值
```

或者統一使用：
```javascript
if (response.status === "success") {
    const violations = response.data.list;
}
```
