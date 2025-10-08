# RTSP影像監控系統 - API服務快速指南

## 🚀 快速開始

### 本地開發

1. **安裝API依賴**:
```bash
pip install -r requirements-api.txt
```

2. **啟動API服務**:
```bash
python -m uvicorn api.main:app --reload --port 8282
```

3. **訪問API文件**:
- Swagger UI: http://localhost:8282/api/docs
- ReDoc: http://localhost:8282/api/redoc

### Docker部署

1. **使用Docker Compose (推薦)**:
```bash
# 建置並啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

2. **單獨建置Docker映像**:
```bash
docker build -t stream-monitor:latest .
docker run -d -p 8000:8282 stream-monitor:latest
```

## 📋 API功能概覽

### 1. 人臉識別建檔管理

```bash
# 建立人員
curl -X POST http://localhost:8282/api/persons \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "emp_001",
    "name": "張三",
    "department": "生產部"
  }'

# 上傳人臉照片
curl -X POST http://localhost:8282/api/persons/emp_001/face-encoding \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg"

# 取得人員列表
curl http://localhost:8282/api/persons
```

### 2. 影像來源CRUD

```bash
# 建立RTSP影像來源
curl -X POST http://localhost:8282/api/streams \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "camera_001",
    "name": "入口攝影機",
    "stream_type": "RTSP",
    "url": "rtsp://192.168.1.100:554/stream1",
    "location": "主入口",
    "enabled": true
  }'

# 取得影像來源列表
curl http://localhost:8282/api/streams

# 啟用影像來源
curl -X POST http://localhost:8282/api/streams/camera_001/enable

# 測試連接
curl -X POST http://localhost:8282/api/streams/camera_001/test
```

### 3. 規則引擎配置

```bash
# 建立安全帽檢測規則
curl -X POST http://localhost:8282/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "rule_helmet_001",
    "name": "入口安全帽檢測",
    "enabled": true,
    "stream_source_ids": ["camera_001"],
    "detection_types": ["helmet"],
    "confidence_threshold": 0.8,
    "notification_enabled": true
  }'

# 使用範本快速建立規則
curl -X POST "http://localhost:8282/api/rules/templates/helmet_detection/apply" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "rule_002",
    "name": "工廠安全帽檢測",
    "stream_source_ids": ["camera_001", "camera_002"]
  }'

# 測試規則
curl -X POST http://localhost:8282/api/rules/rule_helmet_001/test
```

### 4. 違規記錄查詢

```bash
# 查詢違規記錄
curl "http://localhost:8282/api/violations?limit=10&status=new"

# 取得違規統計
curl "http://localhost:8282/api/violations/statistics/summary?days=7"

# 確認違規
curl -X POST http://localhost:8282/api/violations/{violation_id}/acknowledge \
  -H "Content-Type: application/json" \
  -d '{
    "acknowledged_by": "manager_01",
    "notes": "已確認"
  }'
```

## 🔧 規則引擎說明

### 規則結構

規則引擎允許靈活配置檢測行為：

```json
{
  "rule_id": "rule_001",
  "name": "規則名稱",

  // 影像來源篩選
  "stream_source_type": "RTSP",           // 來源類型 (可選)
  "stream_source_ids": ["cam_001"],       // 特定來源 (可選)

  // 人員篩選
  "person_ids": ["emp_001", "emp_002"],   // 特定人員 (可選，空=所有人員)

  // 檢測類型
  "detection_types": ["helmet", "drowsiness", "face"],

  // 檢測參數
  "confidence_threshold": 0.75,
  "time_threshold": 3.0,

  // 通知設定
  "notification_enabled": true,
  "notification_config": {
    "api_endpoint": "https://api.example.com/violations"
  },

  // 排程設定
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],          // 1=週一, 7=週日
    "time_ranges": [
      {"start": "08:00", "end": "17:00"}
    ]
  },

  "priority": 10
}
```

### 規則匹配邏輯

1. **影像來源匹配**:
   - 如指定`stream_source_type`，只匹配該類型
   - 如指定`stream_source_ids`，只匹配列表中的來源
   - 都未指定則匹配所有來源

2. **人員匹配** (僅用於人臉識別):
   - 如指定`person_ids`，只對列表中的人員觸發
   - 未指定則對所有人員觸發

3. **檢測類型**: 必須匹配`detection_types`中的一種

4. **排程匹配**: 如啟用排程，只在指定時間範圍內有效

5. **優先級**: 有多個規則匹配時，使用優先級最高的

### 預設規則範本

系統提供以下範本：

1. **helmet_detection** - 安全帽檢測
   - 檢測類型: helmet
   - 建議信心度: 0.75

2. **drowsiness_detection** - 瞌睡檢測
   - 檢測類型: drowsiness
   - 建議信心度: 0.7
   - 建議時間閾值: 3.0秒

3. **face_recognition** - 人臉識別
   - 檢測類型: face
   - 建議信心度: 0.6

4. **comprehensive** - 綜合檢測
   - 檢測類型: helmet, drowsiness, face
   - 建議信心度: 0.7

## 📊 資料模型

### 影像來源類型

- `RTSP` - Real Time Streaming Protocol
- `WEBCAM` - 本地攝影機
- `HTTP_MJPEG` - HTTP Motion JPEG
- `HLS` - HTTP Live Streaming
- `DASH` - Dynamic Adaptive Streaming
- `WEBRTC` - Web Real-Time Communication
- `ONVIF` - 開放網路影像介面

### 檢測類型

- `helmet` - 安全帽檢測
- `drowsiness` - 瞌睡檢測
- `face` - 人臉識別

### 違規狀態

- `new` - 新違規
- `acknowledged` - 已確認
- `resolved` - 已處理完成

## 🐳 Docker部署詳解

### docker-compose.yml 結構

```yaml
services:
  api:          # API服務 (端口8000)
  monitor:      # 監控服務 (處理影像檢測)
  nginx:        # 反向代理 (可選)
```

### 環境變數配置

複製 `.env.example` 到 `.env` 並修改：

```bash
cp .env.example .env
```

主要配置項：
- `DATABASE_URL` - 資料庫連接
- `LOG_LEVEL` - 日誌等級
- `NOTIFICATION_ENDPOINT` - 通知API端點

### Volume掛載

- `./config` - 配置檔案
- `./screenshots` - 截圖儲存
- `./logs` - 日誌檔案
- `./data` - 資料庫檔案
- `./models` - AI模型檔案

### GPU支援

如需使用GPU加速，取消註釋docker-compose.yml中的GPU配置：

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## 📝 使用範例

### Python客戶端

```python
import requests

class MonitorAPI:
    def __init__(self, base_url="http://localhost:8282"):
        self.base_url = base_url

    def create_stream(self, stream_data):
        return requests.post(
            f"{self.base_url}/api/streams",
            json=stream_data
        )

    def create_rule(self, rule_data):
        return requests.post(
            f"{self.base_url}/api/rules",
            json=rule_data
        )

    def get_violations(self, **params):
        return requests.get(
            f"{self.base_url}/api/violations",
            params=params
        ).json()

# 使用
api = MonitorAPI()

# 建立影像來源
stream = api.create_stream({
    "stream_id": "cam_001",
    "name": "入口攝影機",
    "stream_type": "RTSP",
    "url": "rtsp://192.168.1.100:554/stream1",
    "enabled": True
})

# 建立規則
rule = api.create_rule({
    "rule_id": "rule_001",
    "name": "安全帽檢測",
    "stream_source_ids": ["cam_001"],
    "detection_types": ["helmet"],
    "confidence_threshold": 0.8
})

# 查詢違規
violations = api.get_violations(status="new", limit=10)
```

### JavaScript客戶端

```javascript
class MonitorAPI {
    constructor(baseUrl = 'http://localhost:8282') {
        this.baseUrl = baseUrl;
    }

    async createStream(streamData) {
        const response = await fetch(`${this.baseUrl}/api/streams`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(streamData)
        });
        return response.json();
    }

    async getViolations(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const response = await fetch(
            `${this.baseUrl}/api/violations?${queryString}`
        );
        return response.json();
    }
}

// 使用
const api = new MonitorAPI();

// 建立影像來源
await api.createStream({
    stream_id: 'cam_001',
    name: '入口攝影機',
    stream_type: 'RTSP',
    url: 'rtsp://192.168.1.100:554/stream1',
    enabled: true
});

// 查詢違規
const violations = await api.getViolations({status: 'new', limit: 10});
```

## 🔍 監控和除錯

### 查看API日誌

```bash
# Docker
docker-compose logs -f api

# 本地
tail -f logs/monitoring.log
```

### 健康檢查

```bash
curl http://localhost:8282/api/health
```

### 系統資訊

```bash
curl http://localhost:8282/api/info
```

## 📚 更多文件

- [完整API文件](docs/api.md)
- [使用指南](docs/usage.md)
- [部署指南](docs/deployment.md)
- [開發指南](docs/development.md)

## 🆘 常見問題

### Q: 如何修改API端口？

修改 `docker-compose.yml`:
```yaml
ports:
  - "9000:8282"  # 將8000改為9000
```

或本地啟動時：
```bash
uvicorn api.main:app --port 9000
```

### Q: 資料庫在哪裡？

預設位置: `./data/monitoring.db` (SQLite)

### Q: 如何備份資料？

```bash
# 備份資料庫
cp data/monitoring.db data/monitoring.db.backup

# 備份截圖
tar -czf screenshots_backup.tar.gz screenshots/
```

### Q: 如何重置系統？

```bash
# 停止服務
docker-compose down

# 刪除資料
rm -rf data/*.db screenshots/* logs/*

# 重新啟動
docker-compose up -d
```

## 📞 技術支援

- GitHub Issues: [報告問題]
- API測試: http://localhost:8282/api/docs
- 文件: [完整文件](docs/)
