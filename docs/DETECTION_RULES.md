# 偵測規則說明文檔

## 概述

本系統支援多種偵測類型，並提供靈活的規則配置系統。每個偵測規則可以針對特定的串流來源、人員、時間範圍進行配置。

## 可用的偵測類型

系統支援以下偵測類型：

| 偵測類型 | 代碼 | 說明 | 建議閾值 |
|---------|------|------|---------|
| 安全帽偵測 | `helmet` | 偵測人員是否配戴安全帽 | 0.7 |
| 瞌睡偵測 | `drowsiness` | 偵測人員是否打瞌睡 | 0.6 |
| 人臉辨識 | `face` | 辨識已知/未知人員 | 0.6 |
| 不活動偵測 | `inactivity` | 偵測畫面長時間無活動 | 0.7 |
| 自訂偵測 | `custom` | 自訂偵測邏輯 | - |

## 預設規則列表

系統已預設建立 8 條偵測規則：

### 1. 全域安全帽偵測 (helmet-detection-all)
- **狀態**: ✅ 啟用
- **優先級**: 100 (高)
- **偵測類型**: 安全帽
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.7
- **通知嚴重性**: High
- **說明**: 偵測所有影像來源中未戴安全帽的人員，適用於工地、工廠等需要強制配戴安全帽的場所

### 2. 全域瞌睡偵測 (drowsiness-detection-all)
- **狀態**: ✅ 啟用
- **優先級**: 200 (最高)
- **偵測類型**: 瞌睡
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.6
- **時間閾值**: 3 秒
- **通知嚴重性**: Critical
- **說明**: 偵測所有影像來源中打瞌睡的人員，需持續 3 秒以上才觸發警報

### 3. 全域人臉辨識 (face-recognition-all)
- **狀態**: ✅ 啟用
- **優先級**: 50 (中)
- **偵測類型**: 人臉辨識
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.6
- **通知嚴重性**: Medium
- **說明**: 辨識所有影像來源中的人臉，記錄已知人員並標記未知人員

### 4. 未知人員警報 (unknown-person-alert)
- **狀態**: ✅ 啟用
- **優先級**: 150 (高)
- **偵測類型**: 人臉辨識 (僅未知人員)
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.5
- **通知嚴重性**: High
- **說明**: 當偵測到未知人員時立即發送警報，適用於需要門禁管理的場所

### 5. 全域不活動偵測 (inactivity-detection-all)
- **狀態**: ✅ 啟用
- **優先級**: 30 (低)
- **偵測類型**: 不活動
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.7
- **時間閾值**: 600 秒 (10 分鐘)
- **通知嚴重性**: Medium
- **說明**: 偵測影像中長時間無活動的情況

### 6. WEBCAM 綜合偵測 (webcam-comprehensive)
- **狀態**: ✅ 啟用
- **優先級**: 120 (高)
- **偵測類型**: 安全帽 + 瞌睡 + 人臉辨識
- **適用範圍**: 僅 WEBCAM 類型串流
- **信心度閾值**: 0.7
- **通知嚴重性**: High
- **說明**: 針對 WEBCAM 類型影像來源的綜合偵測

### 7. 工作時間安全帽偵測 (helmet-work-hours)
- **狀態**: ⭕ 停用 (可依需求啟用)
- **優先級**: 100
- **偵測類型**: 安全帽
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.7
- **排程**: 週一至週五 08:00-18:00 (Asia/Taipei)
- **通知嚴重性**: High
- **說明**: 僅在工作時間執行安全帽偵測

### 8. 夜班瞌睡偵測 (drowsiness-night-shift)
- **狀態**: ⭕ 停用 (可依需求啟用)
- **優先級**: 200 (最高)
- **偵測類型**: 瞌睡
- **適用範圍**: 所有串流來源
- **信心度閾值**: 0.5 (更敏感)
- **時間閾值**: 2 秒
- **排程**: 每日 22:00-06:00 (Asia/Taipei)
- **通知嚴重性**: Critical
- **說明**: 針對夜班時段加強瞌睡偵測

## 規則配置說明

### 規則欄位

```json
{
  "rule_id": "唯一規則 ID",
  "name": "規則名稱",
  "description": "規則說明",
  "enabled": true,  // 是否啟用

  // 適用條件
  "stream_source_type": "WEBCAM",  // 串流類型篩選 (null = 全部)
  "stream_source_ids": ["11223"],  // 特定串流 ID (null = 全部)
  "person_ids": ["P001"],          // 特定人員 ID (null = 全部)

  // 偵測設定
  "detection_types": ["helmet", "drowsiness"],
  "confidence_threshold": 0.7,     // 信心度閾值
  "time_threshold": 3.0,           // 時間閾值 (秒)

  // 通知設定
  "notification_enabled": true,
  "notification_config": {
    "methods": ["api", "websocket"],
    "severity": "high"
  },

  // 排程設定
  "schedule_enabled": true,
  "schedule_config": {
    "days": [1,2,3,4,5],          // 0=週日, 1=週一...
    "start_time": "08:00",
    "end_time": "18:00",
    "timezone": "Asia/Taipei"
  },

  "priority": 100  // 優先級 (數值越大越優先)
}
```

### 串流類型

可用的串流類型：
- `RTSP` - RTSP 串流
- `WEBCAM` - 網路攝影機
- `HTTP_MJPEG` - HTTP MJPEG 串流
- `HLS` - HTTP Live Streaming
- `DASH` - Dynamic Adaptive Streaming
- `WEBRTC` - WebRTC 串流
- `ONVIF` - ONVIF 協議攝影機

### 通知嚴重性等級

- `critical` - 危急 (最高)
- `high` - 高
- `medium` - 中等
- `low` - 低

## 使用 API 管理規則

### 查詢所有規則

```bash
GET /api/rules
```

### 查詢特定規則

```bash
GET /api/rules/{rule_id}
```

### 建立規則

```bash
POST /api/rules
Content-Type: application/json

{
  "rule_id": "custom-rule-01",
  "name": "自訂規則",
  "detection_types": ["helmet", "face"],
  "enabled": true,
  "confidence_threshold": 0.75
}
```

### 更新規則

```bash
PUT /api/rules/{rule_id}
Content-Type: application/json

{
  "enabled": true,
  "confidence_threshold": 0.8
}
```

### 刪除規則

```bash
DELETE /api/rules/{rule_id}
```

## 最佳實踐

### 1. 優先級設定

建議優先級範圍：
- **200+**: 最高優先級（危急情況，如瞌睡偵測）
- **100-199**: 高優先級（重要安全，如安全帽偵測）
- **50-99**: 中等優先級（一般監控，如人臉辨識）
- **0-49**: 低優先級（輔助功能，如不活動偵測）

### 2. 信心度閾值

- **安全帽偵測**: 0.7 (較嚴格，減少誤報)
- **瞌睡偵測**: 0.5-0.6 (稍寬鬆，避免漏報)
- **人臉辨識**: 0.6 (平衡準確度)
- **未知人員**: 0.5 (寬鬆，提高檢測率)

### 3. 時間閾值

- **瞌睡偵測**: 2-3 秒（避免短暫閉眼觸發）
- **不活動偵測**: 300-600 秒（5-10 分鐘）

### 4. 規則組合建議

**情境 1: 工地安全監控**
- 啟用: helmet-detection-all
- 啟用: unknown-person-alert
- 啟用: inactivity-detection-all

**情境 2: 駕駛監控**
- 啟用: drowsiness-detection-all
- 啟用: face-recognition-all

**情境 3: 辦公室門禁**
- 啟用: face-recognition-all
- 啟用: unknown-person-alert
- 停用: helmet-detection-all

**情境 4: 夜間值班監控**
- 啟用: drowsiness-night-shift
- 啟用: inactivity-detection-all
- 啟用: face-recognition-all

## 重新載入規則

系統會自動定期重新載入規則（預設 5 分鐘），也可以透過 API 手動觸發：

```bash
POST /api/rules/reload
```

## 故障排除

### 規則未生效

1. 檢查規則是否啟用 (`enabled = true`)
2. 檢查規則的 `stream_source_type` 和 `stream_source_ids` 篩選條件
3. 檢查排程設定（如果 `schedule_enabled = true`）
4. 查看日誌確認規則載入狀態

### 誤報過多

1. 提高 `confidence_threshold` 值
2. 增加 `time_threshold` 避免瞬間觸發
3. 調整規則的適用範圍

### 漏報問題

1. 降低 `confidence_threshold` 值
2. 減少 `time_threshold`
3. 檢查攝影機角度和光線條件

## 參考資料

- [API 文檔](./api.md)
- [開發指南](./development.md)
- [規則引擎整合](../RULE_ENGINE_INTEGRATION.md)
