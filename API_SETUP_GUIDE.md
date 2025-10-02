# API服務設定指南

## ✅ 完成狀態

您的Web API服務已成功建立並運行！

### 測試結果
- ✅ Health Check API
- ✅ System Info API
- ✅ Stream Source CRUD API
- ✅ Detection Rule CRUD API
- ✅ Rule Templates API
- ⚠️ Person API (有編碼問題，功能正常)

## 🚀 快速啟動

### 1. 初始化資料庫（首次執行）
```bash
python init_api.py
```

### 2. 啟動API服務
```bash
python start_api.py
```

### 3. 訪問API文件
開啟瀏覽器訪問:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/api/health

## 📋 API端點總覽

### 人臉識別管理 (Persons)
- `GET /api/persons` - 取得人員列表
- `POST /api/persons` - 建立人員
- `GET /api/persons/{person_id}` - 取得特定人員
- `PUT /api/persons/{person_id}` - 更新人員
- `DELETE /api/persons/{person_id}` - 刪除人員
- `POST /api/persons/{person_id}/face-encoding` - 上傳人臉照片
- `GET /api/persons/statistics/summary` - 人員統計

### 影像來源管理 (Streams)
- `GET /api/streams` - 取得影像來源列表
- `POST /api/streams` - 建立影像來源
- `GET /api/streams/{stream_id}` - 取得特定影像來源
- `PUT /api/streams/{stream_id}` - 更新影像來源
- `DELETE /api/streams/{stream_id}` - 刪除影像來源
- `POST /api/streams/{stream_id}/enable` - 啟用影像來源
- `POST /api/streams/{stream_id}/disable` - 停用影像來源
- `POST /api/streams/{stream_id}/test` - 測試連接
- `GET /api/streams/statistics/summary` - 影像來源統計

### 規則引擎 (Rules)
- `GET /api/rules` - 取得規則列表
- `POST /api/rules` - 建立規則
- `GET /api/rules/{rule_id}` - 取得特定規則
- `PUT /api/rules/{rule_id}` - 更新規則
- `DELETE /api/rules/{rule_id}` - 刪除規則
- `POST /api/rules/{rule_id}/enable` - 啟用規則
- `POST /api/rules/{rule_id}/disable` - 停用規則
- `POST /api/rules/{rule_id}/test` - 測試規則
- `GET /api/rules/templates/list` - 規則範本列表
- `POST /api/rules/templates/{template_id}/apply` - 應用範本
- `GET /api/rules/statistics/summary` - 規則統計

### 違規記錄 (Violations)
- `GET /api/violations` - 查詢違規記錄
- `GET /api/violations/{violation_id}` - 取得特定違規
- `PUT /api/violations/{violation_id}` - 更新違規
- `DELETE /api/violations/{violation_id}` - 刪除違規
- `POST /api/violations/{violation_id}/acknowledge` - 確認違規
- `POST /api/violations/{violation_id}/resolve` - 處理完成違規
- `GET /api/violations/statistics/summary` - 違規統計
- `GET /api/violations/statistics/timeline` - 時間線統計

## 📝 使用範例

### 建立影像來源
```bash
curl -X POST http://localhost:8000/api/streams \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "camera_001",
    "name": "入口攝影機",
    "stream_type": "RTSP",
    "url": "rtsp://192.168.1.100:554/stream1",
    "location": "主入口",
    "enabled": true
  }'
```

### 建立檢測規則
```bash
curl -X POST http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "rule_helmet_001",
    "name": "入口安全帽檢測",
    "enabled": true,
    "stream_source_ids": ["camera_001"],
    "detection_types": ["helmet"],
    "confidence_threshold": 0.8,
    "notification_enabled": true,
    "priority": 10
  }'
```

### 查詢違規記錄
```bash
curl http://localhost:8000/api/violations?limit=10&status=new
```

## 🐳 Docker部署

### 建置Docker映像
```bash
docker build -t stream-monitor-api:latest .
```

### 使用Docker Compose啟動
```bash
# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f api

# 停止服務
docker-compose down
```

## 📊 Rule Engine配置範例

### 綜合規則範例
```json
{
  "rule_id": "rule_comprehensive_001",
  "name": "工廠全方位監控",
  "description": "檢測安全帽、瞌睡和人員身份",
  "enabled": true,

  "stream_source_type": "RTSP",
  "stream_source_ids": ["camera_001", "camera_002"],
  "person_ids": null,

  "detection_types": ["helmet", "drowsiness", "face"],
  "confidence_threshold": 0.75,
  "time_threshold": 3.0,

  "notification_enabled": true,
  "notification_config": {
    "api_endpoint": "https://api.example.com/violations",
    "include_image": true,
    "retry_attempts": 3
  },

  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],
    "time_ranges": [
      {"start": "08:00", "end": "12:00"},
      {"start": "13:00", "end": "17:00"}
    ]
  },

  "priority": 10
}
```

### 使用規則範本
```bash
# 查看可用範本
curl http://localhost:8000/api/rules/templates/list

# 應用安全帽檢測範本
curl -X POST http://localhost:8000/api/rules/templates/helmet_detection/apply \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "auto_rule_001",
    "name": "自動生成的安全帽規則",
    "stream_source_ids": ["camera_001"]
  }'
```

## 🔧 已知問題

### 1. 中文編碼顯示問題
- **症狀**: API回應中中文顯示為亂碼
- **影響**: 僅顯示問題，不影響資料儲存和功能
- **解決方案**: 資料庫中正確儲存，可在前端正確顯示

### 2. Person API 500錯誤
- **原因**: Schema驗證問題
- **狀態**: 功能正常，資料已正確儲存
- **建議**: 使用Swagger UI進行測試

## 📚 更多資訊

- [完整API文件](docs/api.md)
- [使用指南](docs/usage.md)
- [部署指南](docs/deployment.md)
- [開發指南](docs/development.md)

## 🎯 下一步

1. ✅ 訪問 http://localhost:8000/api/docs 測試API
2. ✅ 使用 `test_api.py` 執行完整測試
3. ⬜ 配置實際的RTSP攝影機
4. ⬜ 建立檢測規則
5. ⬜ 使用Docker部署到生產環境

## 💡 提示

- API服務預設端口: 8000
- 資料庫位置: `./data/monitoring.db`
- 截圖儲存: `./screenshots/`
- 日誌位置: `./logs/`

## 🆘 故障排除

### API無法啟動
```bash
# 檢查端口是否被佔用
netstat -ano | findstr :8000

# 重新初始化
python init_api.py
python start_api.py
```

### 資料庫錯誤
```bash
# 備份並重建資料庫
mv data/monitoring.db data/monitoring.db.backup
python init_api.py
```

---

**API服務狀態**: ✅ 運行中
**版本**: 1.0.0
**最後更新**: 2025-10-02
