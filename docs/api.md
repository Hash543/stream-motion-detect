# API 文件

## 概述

RTSP影像監控系統提供完整的RESTful API，支援人臉識別管理、影像來源管理、規則引擎配置和違規記錄查詢等功能。

## 基本資訊

- **Base URL**: `http://localhost:8000`
- **API版本**: v1.0.0
- **Content-Type**: `application/json`
- **文件**:
  - Swagger UI: `http://localhost:8000/api/docs`
  - ReDoc: `http://localhost:8000/api/redoc`

## 認證

目前版本暫不需要認證。生產環境建議添加JWT或API Key認證。

## API端點總覽

### 1. 系統資訊
- `GET /` - 根路徑
- `GET /api/health` - 健康檢查
- `GET /api/info` - 系統資訊

### 2. 人臉識別管理 (`/api/persons`)
- `GET /api/persons` - 取得人員列表
- `GET /api/persons/{person_id}` - 取得特定人員
- `POST /api/persons` - 建立人員
- `PUT /api/persons/{person_id}` - 更新人員
- `DELETE /api/persons/{person_id}` - 刪除人員
- `POST /api/persons/{person_id}/face-encoding` - 上傳人臉照片
- `GET /api/persons/{person_id}/face-encoding` - 取得人臉特徵
- `DELETE /api/persons/{person_id}/face-encoding` - 刪除人臉特徵
- `GET /api/persons/statistics/summary` - 人員統計

### 3. 影像來源管理 (`/api/streams`)
- `GET /api/streams` - 取得影像來源列表
- `GET /api/streams/{stream_id}` - 取得特定影像來源
- `POST /api/streams` - 建立影像來源
- `PUT /api/streams/{stream_id}` - 更新影像來源
- `DELETE /api/streams/{stream_id}` - 刪除影像來源
- `POST /api/streams/{stream_id}/enable` - 啟用影像來源
- `POST /api/streams/{stream_id}/disable` - 停用影像來源
- `GET /api/streams/{stream_id}/status` - 取得即時狀態
- `POST /api/streams/{stream_id}/test` - 測試連接
- `GET /api/streams/statistics/summary` - 影像來源統計

### 4. 規則引擎 (`/api/rules`)
- `GET /api/rules` - 取得規則列表
- `GET /api/rules/{rule_id}` - 取得特定規則
- `POST /api/rules` - 建立規則
- `PUT /api/rules/{rule_id}` - 更新規則
- `DELETE /api/rules/{rule_id}` - 刪除規則
- `POST /api/rules/{rule_id}/enable` - 啟用規則
- `POST /api/rules/{rule_id}/disable` - 停用規則
- `POST /api/rules/{rule_id}/test` - 測試規則
- `GET /api/rules/statistics/summary` - 規則統計
- `GET /api/rules/templates/list` - 規則範本列表
- `POST /api/rules/templates/{template_id}/apply` - 應用範本

### 5. 違規記錄 (`/api/violations`)
- `GET /api/violations` - 查詢違規記錄
- `GET /api/violations/{violation_id}` - 取得特定違規
- `PUT /api/violations/{violation_id}` - 更新違規
- `DELETE /api/violations/{violation_id}` - 刪除違規
- `POST /api/violations/{violation_id}/acknowledge` - 確認違規
- `POST /api/violations/{violation_id}/resolve` - 處理完成違規
- `GET /api/violations/statistics/summary` - 違規統計
- `GET /api/violations/statistics/timeline` - 時間線統計
- `POST /api/violations/cleanup` - 清理舊記錄

---

## 詳細API說明

### 人臉識別管理

#### 取得人員列表
```http
GET /api/persons?skip=0&limit=100&status=active
```

**查詢參數**:
- `skip` (int): 跳過筆數，預設0
- `limit` (int): 限制筆數，預設100
- `status` (string): 篩選狀態 (active/inactive)
- `department` (string): 篩選部門

**回應範例**:
```json
[
  {
    "id": 1,
    "person_id": "emp_001",
    "name": "張三",
    "department": "生產部",
    "position": "技術員",
    "status": "active",
    "face_encoding": null,
    "metadata": {"badge_number": "A12345"},
    "created_at": "2024-01-01T08:00:00",
    "updated_at": "2024-01-01T08:00:00"
  }
]
```

#### 建立人員
```http
POST /api/persons
Content-Type: application/json

{
  "person_id": "emp_001",
  "name": "張三",
  "department": "生產部",
  "position": "技術員",
  "status": "active",
  "metadata": {"badge_number": "A12345"}
}
```

#### 上傳人臉照片
```http
POST /api/persons/{person_id}/face-encoding
Content-Type: multipart/form-data

images: [file1.jpg, file2.jpg, file3.jpg]
```

**說明**: 建議上傳3-5張不同角度的人臉照片以提高識別準確度

---

### 影像來源管理

#### 建立影像來源
```http
POST /api/streams
Content-Type: application/json

{
  "stream_id": "camera_001",
  "name": "工廠入口攝影機",
  "stream_type": "RTSP",
  "url": "rtsp://192.168.1.100:554/stream1",
  "location": "工廠入口",
  "enabled": true,
  "config": {
    "tcp_transport": true,
    "timeout": 10
  }
}
```

**支援的串流類型**:
- `RTSP` - Real Time Streaming Protocol
- `WEBCAM` - 本地攝影機
- `HTTP_MJPEG` - HTTP Motion JPEG
- `HLS` - HTTP Live Streaming
- `DASH` - Dynamic Adaptive Streaming
- `WEBRTC` - Web Real-Time Communication
- `ONVIF` - 開放網路影像介面

#### 各類型配置範例

**WEBCAM**:
```json
{
  "stream_id": "webcam_01",
  "name": "本地攝影機",
  "stream_type": "WEBCAM",
  "enabled": true,
  "config": {
    "device_index": 0,
    "resolution": {"width": 1280, "height": 720},
    "fps": 30
  }
}
```

**HTTP_MJPEG**:
```json
{
  "stream_id": "http_cam_01",
  "name": "HTTP攝影機",
  "stream_type": "HTTP_MJPEG",
  "url": "http://192.168.1.100/mjpeg",
  "enabled": true,
  "config": {
    "auth": {
      "username": "admin",
      "password": "password"
    }
  }
}
```

---

### 規則引擎

#### 建立檢測規則
```http
POST /api/rules
Content-Type: application/json

{
  "rule_id": "rule_helmet_001",
  "name": "工廠入口安全帽檢測",
  "description": "檢測進入工廠的人員是否佩戴安全帽",
  "enabled": true,
  "stream_source_type": "RTSP",
  "stream_source_ids": ["camera_001", "camera_002"],
  "person_ids": null,
  "detection_types": ["helmet"],
  "confidence_threshold": 0.8,
  "notification_enabled": true,
  "notification_config": {
    "api_endpoint": "https://api.example.com/violations",
    "include_image": true
  },
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],
    "time_ranges": [
      {"start": "08:00", "end": "17:00"}
    ]
  },
  "priority": 10
}
```

**規則欄位說明**:
- `stream_source_type`: 影像來源類型篩選 (null=所有類型)
- `stream_source_ids`: 特定影像來源ID列表 (null=所有來源)
- `person_ids`: 特定人員ID列表 (null=所有人員)
- `detection_types`: 檢測類型 ["helmet", "drowsiness", "face"]
- `confidence_threshold`: 信心度閾值 (0.0-1.0)
- `time_threshold`: 時間閾值(秒)，用於瞌睡等需要持續時間的檢測
- `schedule_config.weekdays`: 1=週一, 7=週日

#### 使用規則範本
```http
POST /api/rules/templates/helmet_detection/apply
Content-Type: application/json

{
  "rule_id": "rule_001",
  "name": "安全帽檢測規則",
  "stream_source_ids": ["camera_001", "camera_002"]
}
```

**可用範本**:
- `helmet_detection` - 安全帽檢測
- `drowsiness_detection` - 瞌睡檢測
- `face_recognition` - 人臉識別
- `comprehensive` - 綜合檢測

#### 測試規則
```http
POST /api/rules/{rule_id}/test
```

回應會顯示規則會匹配哪些影像來源和人員。

---

### 違規記錄

#### 查詢違規記錄
```http
GET /api/violations?camera_id=camera_001&start_time=2024-01-01T00:00:00&limit=100
```

**查詢參數**:
- `camera_id`: 攝影機ID
- `violation_type`: 違規類型 (no_helmet/drowsiness/unknown_person)
- `person_id`: 人員ID
- `rule_id`: 規則ID
- `status`: 狀態 (new/acknowledged/resolved)
- `start_time`: 起始時間 (ISO 8601格式)
- `end_time`: 結束時間
- `skip`: 跳過筆數
- `limit`: 限制筆數

#### 確認違規
```http
POST /api/violations/{violation_id}/acknowledge
Content-Type: application/json

{
  "acknowledged_by": "manager_01",
  "notes": "已通知相關人員"
}
```

#### 處理完成違規
```http
POST /api/violations/{violation_id}/resolve
Content-Type: application/json

{
  "resolved_by": "supervisor_02",
  "notes": "已完成安全教育訓練"
}
```

#### 取得違規統計
```http
GET /api/violations/statistics/summary?days=7
```

**回應範例**:
```json
{
  "total_violations": 150,
  "violations_by_type": {
    "no_helmet": 80,
    "drowsiness": 50,
    "unknown_person": 20
  },
  "violations_by_camera": {
    "camera_001": 70,
    "camera_002": 80
  },
  "violations_by_person": {
    "emp_001": 5,
    "emp_002": 3
  },
  "violations_by_status": {
    "new": 30,
    "acknowledged": 50,
    "resolved": 70
  },
  "period_days": 7
}
```

#### 取得時間線統計
```http
GET /api/violations/statistics/timeline?days=7
```

**回應範例**:
```json
{
  "period_days": 7,
  "timeline": [
    {"date": "2024-01-01", "count": 20},
    {"date": "2024-01-02", "count": 25},
    {"date": "2024-01-03", "count": 18}
  ]
}
```

---

## 錯誤處理

所有API錯誤都遵循統一格式：

```json
{
  "error": "Error Type",
  "message": "詳細錯誤訊息",
  "detail": "額外細節 (可選)"
}
```

### HTTP狀態碼

- `200 OK` - 請求成功
- `201 Created` - 資源建立成功
- `400 Bad Request` - 請求參數錯誤
- `404 Not Found` - 資源不存在
- `500 Internal Server Error` - 伺服器內部錯誤
- `503 Service Unavailable` - 服務暫時不可用

---

## 完整使用範例

### 範例1: 建立完整的監控規則

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 建立影像來源
stream_data = {
    "stream_id": "camera_entrance",
    "name": "入口攝影機",
    "stream_type": "RTSP",
    "url": "rtsp://192.168.1.100:554/stream1",
    "location": "主入口",
    "enabled": True
}
response = requests.post(f"{BASE_URL}/api/streams", json=stream_data)
print(f"建立影像來源: {response.status_code}")

# 2. 建立人員
person_data = {
    "person_id": "emp_001",
    "name": "張三",
    "department": "生產部",
    "status": "active"
}
response = requests.post(f"{BASE_URL}/api/persons", json=person_data)
print(f"建立人員: {response.status_code}")

# 3. 上傳人臉照片
files = [
    ('images', open('photo1.jpg', 'rb')),
    ('images', open('photo2.jpg', 'rb')),
]
response = requests.post(
    f"{BASE_URL}/api/persons/emp_001/face-encoding",
    files=files
)
print(f"上傳人臉照片: {response.status_code}")

# 4. 建立檢測規則
rule_data = {
    "rule_id": "rule_001",
    "name": "入口安全帽檢測",
    "enabled": True,
    "stream_source_ids": ["camera_entrance"],
    "detection_types": ["helmet", "face"],
    "confidence_threshold": 0.75,
    "notification_enabled": True,
    "priority": 10
}
response = requests.post(f"{BASE_URL}/api/rules", json=rule_data)
print(f"建立規則: {response.status_code}")

# 5. 查詢違規記錄
response = requests.get(
    f"{BASE_URL}/api/violations",
    params={"camera_id": "camera_entrance", "limit": 10}
)
violations = response.json()
print(f"違規記錄數: {len(violations)}")
```

### 範例2: 查詢和處理違規

```python
# 查詢最近的未處理違規
response = requests.get(
    f"{BASE_URL}/api/violations",
    params={"status": "new", "limit": 10}
)
violations = response.json()

for violation in violations:
    violation_id = violation['violation_id']

    # 確認違規
    requests.post(
        f"{BASE_URL}/api/violations/{violation_id}/acknowledge",
        json={
            "acknowledged_by": "manager_01",
            "notes": "已確認，正在處理"
        }
    )

    # 處理完成
    requests.post(
        f"{BASE_URL}/api/violations/{violation_id}/resolve",
        json={
            "resolved_by": "supervisor_01",
            "notes": "已完成處理"
        }
    )
```

---

## WebSocket支援 (規劃中)

未來版本將支援WebSocket連接以實現即時通知：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/violations');
ws.onmessage = (event) => {
    const violation = JSON.parse(event.data);
    console.log('新違規:', violation);
};
```

---

## SDK和客戶端

### Python客戶端範例

```python
class StreamMonitorClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def create_person(self, person_data):
        return requests.post(
            f"{self.base_url}/api/persons",
            json=person_data
        )

    def get_violations(self, **params):
        return requests.get(
            f"{self.base_url}/api/violations",
            params=params
        ).json()

# 使用
client = StreamMonitorClient()
violations = client.get_violations(status="new", limit=10)
```

---

## 效能考量

### 分頁

所有列表API都支援分頁：
- 預設limit: 100
- 最大limit: 1000
- 使用skip和limit進行分頁

### 快取

建議在客戶端實作快取機制：
- 人員列表快取時間: 5分鐘
- 規則列表快取時間: 1分鐘
- 違規統計快取時間: 30秒

### 批次操作

大量資料操作時建議使用批次處理。

---

## 安全性建議

1. **使用HTTPS**: 生產環境必須使用HTTPS
2. **添加認證**: 實作JWT或API Key認證
3. **速率限制**: 實作API速率限制
4. **輸入驗證**: 嚴格驗證所有輸入
5. **CORS設定**: 限制允許的來源域名

---

## 更新日誌

### v1.0.0 (2024-10)
- 初始版本發布
- 實作人臉識別管理API
- 實作影像來源CRUD API
- 實作規則引擎API
- 實作違規記錄API

---

## 技術支援

- **文件**: [完整文件](./README.md)
- **問題回報**: GitHub Issues
- **API測試**: 使用Swagger UI (`/api/docs`)
