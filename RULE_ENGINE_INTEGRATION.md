# Rule Engine 整合說明

## 📋 概述

Rule Engine（規則引擎）是系統的核心控制機制，所有檢測都必須先通過 Rule Engine 的規則匹配才會被處理。這提供了靈活的檢測控制能力。

## 🔧 運作原理

### 檢測流程

```
1. 檢測器偵測到違規
   ↓
2. Rule Engine 檢查是否有匹配的規則
   ↓ 有匹配規則        ↓ 沒有匹配規則
3a. 檢查信心度閾值    3b. 丟棄檢測結果
   ↓ 通過             ↓ 不通過
4a. 處理違規          4b. 丟棄檢測結果
   (截圖、記錄、通知)
```

### 規則匹配邏輯

Rule Engine 依序檢查以下條件：

1. **檢測類型匹配**: `detection_types` 包含當前檢測類型
2. **攝影機類型匹配**: `stream_source_type` 符合（如果有設定）
3. **攝影機ID匹配**: `stream_source_ids` 包含當前攝影機（如果有設定）
4. **人員ID匹配**: `person_ids` 包含當前人員（僅用於人臉識別）
5. **排程匹配**: 當前時間在 `schedule_config` 範圍內（如果有啟用）
6. **信心度閾值**: 檢測信心度 >= `confidence_threshold`

**所有條件都通過** 才會觸發違規處理。

### 優先級機制

- 規則按 `priority` 由高到低排序
- 系統使用**第一個匹配**的規則
- 高優先級規則可以覆蓋低優先級規則

## 📊 預設規則

系統預設創建了 5 條規則，涵蓋所有檢測類型：

### 1. 疲勞駕駛檢測規則 (優先級: 90)

```json
{
  "rule_id": "default_drowsiness_detection",
  "name": "預設疲勞駕駛檢測規則",
  "detection_types": ["drowsiness"],
  "confidence_threshold": 0.7,
  "time_threshold": 3,
  "schedule_enabled": false,
  "priority": 90
}
```

**特點**:
- 最高優先級（安全關鍵）
- 全天候監控
- 需持續 3 秒才觸發
- 適用所有攝影機

### 2. RTSP 綜合檢測規則 (優先級: 85)

```json
{
  "rule_id": "default_rtsp_comprehensive",
  "name": "RTSP攝影機綜合檢測",
  "stream_source_type": "rtsp",
  "detection_types": ["helmet", "drowsiness", "face"],
  "confidence_threshold": 0.65,
  "priority": 85
}
```

**特點**:
- 僅適用 RTSP 攝影機
- 涵蓋三種檢測類型
- 統一的信心度閾值 (0.65)
- 全天候監控

### 3. 安全帽檢測規則 (優先級: 80)

```json
{
  "rule_id": "default_helmet_detection",
  "name": "預設安全帽檢測規則",
  "detection_types": ["helmet"],
  "confidence_threshold": 0.6,
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],
    "time_ranges": [
      {"start": "08:00", "end": "18:00"}
    ]
  },
  "priority": 80
}
```

**特點**:
- 僅在上班時間監控（週一至週五 08:00-18:00）
- 適用所有攝影機
- 需先偵測到人臉才會進行安全帽檢測

### 4. 人臉識別規則 (優先級: 70)

```json
{
  "rule_id": "default_face_recognition",
  "name": "預設人臉識別規則",
  "detection_types": ["face"],
  "confidence_threshold": 0.5,
  "priority": 70
}
```

**特點**:
- 較低的信心度閾值（避免漏失人臉）
- 全天候監控
- 適用所有人員

### 5. 無活動檢測規則 (優先級: 60)

```json
{
  "rule_id": "default_inactivity_detection",
  "name": "預設無活動檢測規則",
  "detection_types": ["inactivity"],
  "confidence_threshold": 0.9,
  "time_threshold": 30,
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5, 6, 7],
    "time_ranges": [
      {"start": "08:00", "end": "22:00"}
    ]
  },
  "priority": 60
}
```

**特點**:
- 工作時段監控（全週 08:00-22:00）
- 30 秒無人無動作才觸發
- 適用所有攝影機

## 🛠️ 初始化和管理

### 初始化預設規則

```bash
# 初始化預設規則（如果已存在規則會跳過）
python init_default_rules.py

# 強制重新初始化（刪除所有現有規則）
python init_default_rules_force.py

# 列出現有規則
python init_default_rules.py --list
```

### 透過 API 管理規則

API 端點: `http://localhost:8232/api/docs`

#### 查詢所有規則
```bash
GET /api/rules
```

#### 創建新規則
```bash
POST /api/rules
Content-Type: application/json

{
  "rule_id": "custom_rule_001",
  "name": "自訂規則",
  "detection_types": ["helmet"],
  "stream_source_ids": ["camera_001"],
  "confidence_threshold": 0.75,
  "priority": 50,
  "enabled": true
}
```

#### 更新規則
```bash
PUT /api/rules/{rule_id}
```

#### 啟用/停用規則
```bash
PATCH /api/rules/{rule_id}/enable
PATCH /api/rules/{rule_id}/disable
```

#### 刪除規則
```bash
DELETE /api/rules/{rule_id}
```

## 📖 使用範例

### 範例 1: 特定攝影機的高敏感度檢測

```json
{
  "rule_id": "high_security_camera",
  "name": "高安全性攝影機規則",
  "stream_source_ids": ["camera_entrance"],
  "detection_types": ["helmet", "face"],
  "confidence_threshold": 0.8,
  "notification_enabled": true,
  "notification_config": {
    "priority": "critical"
  },
  "priority": 95,
  "enabled": true
}
```

**用途**: 入口攝影機需要更嚴格的檢測

### 範例 2: 夜間無活動檢測

```json
{
  "rule_id": "night_inactivity",
  "name": "夜間無活動監控",
  "detection_types": ["inactivity"],
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5, 6, 7],
    "time_ranges": [
      {"start": "22:00", "end": "06:00"}
    ]
  },
  "confidence_threshold": 0.9,
  "priority": 75,
  "enabled": true
}
```

**用途**: 夜間時段特別監控無人狀態

### 範例 3: 特定人員的人臉識別

```json
{
  "rule_id": "vip_recognition",
  "name": "VIP人員識別",
  "detection_types": ["face"],
  "person_ids": ["person_001", "person_002"],
  "confidence_threshold": 0.6,
  "notification_enabled": true,
  "notification_config": {
    "priority": "high",
    "methods": ["api", "email"]
  },
  "priority": 85,
  "enabled": true
}
```

**用途**: 只關注特定重要人員的出現

### 範例 4: 停用週末檢測

```json
{
  "rule_id": "weekday_only",
  "name": "僅工作日檢測",
  "detection_types": ["helmet", "drowsiness"],
  "schedule_enabled": true,
  "schedule_config": {
    "weekdays": [1, 2, 3, 4, 5],
    "time_ranges": [
      {"start": "00:00", "end": "23:59"}
    ]
  },
  "priority": 70,
  "enabled": true
}
```

**用途**: 週末不進行檢測

## 🔍 規則優先級建議

根據檢測重要性和場景，建議的優先級範圍：

| 優先級範圍 | 適用場景 | 範例 |
|----------|---------|------|
| 90-100 | 安全關鍵檢測 | 疲勞駕駛、緊急狀況 |
| 80-89 | 重要檢測 | 安全帽、特定攝影機綜合檢測 |
| 70-79 | 一般檢測 | 人臉識別、常規違規 |
| 60-69 | 次要檢測 | 無活動檢測、統計用途 |
| 50-59 | 自訂規則 | 實驗性規則、特殊需求 |

## ⚙️ 技術整合

### 在 MonitoringSystem 中的整合

```python
# 初始化 Rule Engine
self.rule_engine_manager = RuleEngineManager()
self.rule_engine_manager.reload_rules()

# 處理違規時檢查規則
def _handle_violation(self, camera_id, frame, violation, face_detections, timestamp):
    # 獲取攝影機類型
    stream_type = self._get_stream_type(camera_id)

    # Rule Engine 檢查
    should_trigger, matched_rule = self.rule_engine_manager.should_trigger_violation(
        stream_id=camera_id,
        stream_type=stream_type,
        detection_type=violation.detection_type,
        confidence=violation.confidence,
        person_id=person_id
    )

    if not should_trigger:
        return  # 不符合規則，丟棄檢測結果

    # 處理違規（截圖、記錄、通知）
    # ...
```

### 規則自動重載

Rule Engine 每 5 分鐘自動重新載入規則：

```python
def should_reload_rules(self) -> bool:
    if not self.last_reload_time:
        return True
    elapsed = (datetime.now() - self.last_reload_time).total_seconds()
    return elapsed > self.reload_interval  # 300 秒
```

**優點**:
- 修改規則後無需重啟系統
- 規則變更在 5 分鐘內生效
- 降低資料庫查詢頻率

## 📊 監控和除錯

### 查看規則匹配日誌

系統日誌會記錄規則匹配資訊：

```
INFO - Rule Engine matched: 預設疲勞駕駛檢測規則 for drowsiness on camera_001
WARNING - VIOLATION DETECTED: drowsiness on camera_001 (confidence: 0.85, person: person_001, rule: 預設疲勞駕駛檢測規則)
```

### 被過濾的檢測

```
DEBUG - Violation helmet on camera_002 filtered by Rule Engine (no matching rule or confidence too low)
```

### 檢查規則狀態

```bash
# 透過 API 查詢規則
curl http://localhost:8232/api/rules

# 查詢特定規則
curl http://localhost:8232/api/rules/default_helmet_detection
```

## 💡 最佳實踐

### 1. 規則命名規範

```
{prefix}_{detection_type}_{scope}_{identifier}

範例:
- default_helmet_detection          (預設安全帽檢測)
- custom_face_entrance_001          (自訂入口人臉識別)
- test_inactivity_warehouse_temp    (測試倉庫無活動)
```

### 2. 規則設計原則

**DO**:
- ✅ 使用明確的規則名稱和描述
- ✅ 合理設定信心度閾值（避免過多誤報）
- ✅ 使用排程避免非工作時段的檢測
- ✅ 為關鍵檢測設定高優先級
- ✅ 定期檢視和調整規則

**DON'T**:
- ❌ 創建過多重疊的規則
- ❌ 設定過低的信心度閾值
- ❌ 忘記設定合理的優先級
- ❌ 忽略排程功能（造成不必要的處理）

### 3. 信心度閾值建議

| 檢測類型 | 建議閾值範圍 | 說明 |
|---------|------------|------|
| helmet | 0.6 - 0.75 | 安全帽外觀較一致 |
| drowsiness | 0.7 - 0.85 | 需較高信心度避免誤報 |
| face | 0.5 - 0.7 | 較低閾值避免漏失 |
| inactivity | 0.9 - 1.0 | 幾乎不需調整 |

### 4. 測試新規則

```bash
# 1. 創建測試規則（低優先級、停用通知）
POST /api/rules
{
  "rule_id": "test_new_rule",
  "priority": 10,
  "enabled": true,
  "notification_enabled": false
}

# 2. 觀察日誌中的匹配情況

# 3. 調整參數

# 4. 確認無誤後啟用通知和提高優先級
```

## 🔧 故障排除

### 問題 1: 檢測未觸發違規處理

**可能原因**:
1. 沒有匹配的規則
2. 信心度低於閾值
3. 不在排程時段內
4. 規則被停用

**解決方法**:
```bash
# 檢查是否有匹配的規則
python init_default_rules.py --list

# 查看系統日誌
# 尋找 "filtered by Rule Engine" 訊息

# 檢查規則是否啟用
curl http://localhost:8232/api/rules
```

### 問題 2: 規則修改未生效

**原因**: Rule Engine 尚未重新載入（最多等待 5 分鐘）

**解決方法**:
```bash
# 重啟監控系統
# 或等待 5 分鐘自動重載
```

### 問題 3: 多條規則衝突

**原因**: 多條規則匹配同一檢測，使用了優先級最高的

**解決方法**:
```bash
# 檢查規則優先級
python init_default_rules.py --list

# 調整規則優先級或停用衝突的規則
```

## 📚 相關檔案

- **Rule Engine 管理器**: `src/managers/rule_engine_manager.py`
- **初始化腳本**: `init_default_rules.py`, `init_default_rules_force.py`
- **API 路由**: `api/routers/rules.py`
- **資料模型**: `api/models.py` (`DetectionRule`)
- **監控系統整合**: `src/monitoring_system.py`

## 🎯 總結

Rule Engine 提供了靈活且強大的檢測控制機制：

- ✅ **統一控制**: 所有檢測都通過 Rule Engine
- ✅ **靈活配置**: 支援多維度過濾（攝影機、人員、時段、信心度）
- ✅ **優先級機制**: 精確控制規則應用順序
- ✅ **動態更新**: 無需重啟即可修改規則
- ✅ **預設規則**: 開箱即用的完整檢測配置

---

**版本**: 1.0.0
**最後更新**: 2025-10-02
**API 端點**: http://localhost:8232/api/docs
