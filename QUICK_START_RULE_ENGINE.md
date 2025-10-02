# Rule Engine 快速開始指南

## 🚀 快速開始（3 步驟）

### 步驟 1: 初始化預設規則

```bash
# 初始化 5 條預設檢測規則
python init_default_rules_force.py
```

輸出：
```
已創建的規則：
1. 安全帽檢測規則 (優先級: 80)
2. 疲勞駕駛檢測規則 (優先級: 90)
3. 人臉識別規則 (優先級: 70)
4. 無活動檢測規則 (優先級: 60)
5. RTSP綜合檢測規則 (優先級: 85)
```

### 步驟 2: 啟動 API 服務

```bash
python start_api.py
```

API 文檔: http://localhost:8232/api/docs

### 步驟 3: 查看和管理規則

瀏覽器開啟: http://localhost:8232/api/docs

找到 `/api/rules` 端點，可以：
- 查詢所有規則
- 創建新規則
- 修改現有規則
- 啟用/停用規則

## 📋 規則說明

所有檢測（安全帽、疲勞駕駛、人臉、無活動）現在都依照 Rule Engine 的規則執行：

- ✅ **有匹配規則** + **信心度達標** → 處理違規（截圖、記錄、通知）
- ❌ **無匹配規則** 或 **信心度不足** → 丟棄檢測結果

## 🎯 常用操作

### 查看所有規則

```bash
python init_default_rules.py --list
```

### 透過 API 查詢規則

```bash
curl http://localhost:8232/api/rules
```

### 創建自訂規則

```bash
curl -X POST http://localhost:8232/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "my_custom_rule",
    "name": "我的自訂規則",
    "detection_types": ["helmet"],
    "stream_source_ids": ["camera_001"],
    "confidence_threshold": 0.7,
    "priority": 75,
    "enabled": true
  }'
```

### 停用規則

```bash
curl -X PATCH http://localhost:8232/api/rules/{rule_id}/disable
```

### 啟用規則

```bash
curl -X PATCH http://localhost:8232/api/rules/{rule_id}/enable
```

## 📊 檢測類型

系統支援 4 種檢測類型：

| 檢測類型 | detection_type | 說明 |
|---------|----------------|------|
| 安全帽檢測 | `helmet` | 檢測未戴安全帽（需先偵測到人臉） |
| 疲勞駕駛檢測 | `drowsiness` | 檢測疲勞狀態 |
| 人臉識別 | `face` | 識別已知人員 |
| 無活動檢測 | `inactivity` | 30秒無人無動作 |

## ⚙️ 規則參數說明

### 必填參數

- `rule_id`: 規則唯一識別碼
- `name`: 規則名稱
- `detection_types`: 檢測類型列表（可多選）
- `confidence_threshold`: 信心度閾值 (0.0 - 1.0)
- `priority`: 優先級 (數字越大越優先)
- `enabled`: 是否啟用

### 選填參數

- `stream_source_type`: 攝影機類型（`rtsp`, `webcam`, 等）
- `stream_source_ids`: 特定攝影機ID列表
- `person_ids`: 特定人員ID列表（僅用於人臉識別）
- `schedule_enabled`: 是否啟用排程
- `schedule_config`: 排程配置
  ```json
  {
    "weekdays": [1, 2, 3, 4, 5],  // 1=週一, 7=週日
    "time_ranges": [
      {"start": "08:00", "end": "18:00"}
    ]
  }
  ```
- `notification_enabled`: 是否發送通知
- `notification_config`: 通知配置

## 🔍 範例規則

### 範例 1: 僅監控特定攝影機的安全帽

```json
{
  "rule_id": "entrance_helmet",
  "name": "入口安全帽檢測",
  "detection_types": ["helmet"],
  "stream_source_ids": ["camera_entrance"],
  "confidence_threshold": 0.75,
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],
    "time_ranges": [{"start": "07:00", "end": "19:00"}]
  },
  "priority": 85,
  "enabled": true
}
```

### 範例 2: 週末停用所有檢測

設定所有規則的 `schedule_config`:
```json
{
  "weekdays": [1, 2, 3, 4, 5]  // 僅週一至週五
}
```

### 範例 3: 特定人員的高優先級識別

```json
{
  "rule_id": "vip_detection",
  "name": "VIP人員識別",
  "detection_types": ["face"],
  "person_ids": ["person_vip_001", "person_vip_002"],
  "confidence_threshold": 0.6,
  "notification_enabled": true,
  "priority": 95,
  "enabled": true
}
```

## 💡 提示

1. **規則自動重載**: 修改規則後，系統會在 5 分鐘內自動重新載入
2. **優先級機制**: 多條規則匹配時，使用優先級最高的規則
3. **預設規則**: 初始化的預設規則涵蓋所有檢測類型，可直接使用
4. **日誌查看**: 檢查系統日誌可看到規則匹配情況

## 📚 詳細文檔

完整文檔請參考: [RULE_ENGINE_INTEGRATION.md](RULE_ENGINE_INTEGRATION.md)

## 🆘 常見問題

**Q: 為什麼檢測到違規但沒有處理？**
A: 可能沒有匹配的規則，或信心度低於閾值。檢查日誌中的 "filtered by Rule Engine" 訊息。

**Q: 如何讓某個攝影機不進行檢測？**
A: 創建規則時不要包含該攝影機ID，或為該攝影機創建信心度閾值為 1.0 的規則。

**Q: 如何調整檢測的敏感度？**
A: 修改規則的 `confidence_threshold`。數值越低越敏感（但可能誤報越多）。

**Q: 修改規則後要重啟系統嗎？**
A: 不需要。系統會在 5 分鐘內自動重載規則。

---

**需要幫助？** 查看完整文檔或透過 API 文檔測試規則。
