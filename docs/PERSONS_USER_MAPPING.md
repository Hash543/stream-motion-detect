# Persons API - 使用者關聯功能

## 概述

Persons API 現在支持將人員 (Person) 與系統使用者 (User) 進行關聯。這允許您將人臉識別系統中的人員資料與實際的系統使用者帳號綁定。

## 資料庫變更

### 新增欄位

在 `persons` 表中新增了以下欄位：

| 欄位名稱 | 類型 | 說明 | 外鍵 |
|---------|------|------|------|
| user_id | INTEGER | 關聯的使用者ID | user.id |

### 關聯關係

- **外鍵約束**: `fk_persons_user_id`
- **關聯表**: `user`
- **級聯規則**:
  - `ON DELETE SET NULL` - 刪除使用者時，person.user_id 設為 NULL
  - `ON UPDATE CASCADE` - 更新使用者ID時，person.user_id 自動更新
- **索引**: `idx_persons_user_id` 已建立以提升查詢性能

## API 端點

### 1. 取得使用者選項列表 (用於下拉選單)

**端點**: `GET /api/persons/users/options`

**描述**: 取得所有可用的使用者列表，用於前端下拉選單選擇

**查詢參數**:
- `status` (可選): 篩選使用者狀態
  - `0`: 正常 (預設)
  - `1`: 凍結
  - `2`: 刪除

**請求範例**:
```bash
# 取得所有啟用的使用者
curl -X GET "http://localhost:8282/api/persons/users/options"

# 取得所有狀態的使用者
curl -X GET "http://localhost:8282/api/persons/users/options?status=0"
```

**回應範例**:
```json
{
  "status": "success",
  "data": [
    {
      "value": 1,
      "label": "張三 (zhangsan)",
      "user_id": 1,
      "user_name": "張三",
      "username": "zhangsan",
      "org_id": 1,
      "role_id": 2
    },
    {
      "value": 2,
      "label": "李四 (lisi)",
      "user_id": 2,
      "user_name": "李四",
      "username": "lisi",
      "org_id": 2,
      "role_id": 3
    }
  ]
}
```

### 2. 建立人員 (含使用者關聯)

**端點**: `POST /api/persons/`

**描述**: 建立新的人員資料，可以選擇性地關聯到系統使用者

**請求參數**:
```json
{
  "person_id": "P001",
  "name": "張三",
  "department": "技術部",
  "position": "工程師",
  "user_id": 1,           // 新增: 關聯的使用者ID (可選)
  "status": "active",
  "extra_data": {}
}
```

**請求範例**:
```bash
curl -X POST "http://localhost:8282/api/persons/" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "P001",
    "name": "張三",
    "department": "技術部",
    "position": "工程師",
    "user_id": 1,
    "status": "active"
  }'
```

**回應範例**:
```json
{
  "id": 1,
  "person_id": "P001",
  "name": "張三",
  "department": "技術部",
  "position": "工程師",
  "user_id": 1,
  "user_name": "張三 (zhangsan)",  // 新增: 關聯的使用者名稱
  "status": "active",
  "extra_data": {},
  "face_encoding": null,
  "created_at": "2025-10-17T12:34:56.789Z",
  "updated_at": "2025-10-17T12:34:56.789Z"
}
```

### 3. 更新人員 (更新使用者關聯)

**端點**: `PUT /api/persons/{person_id}`

**描述**: 更新人員資料，可以新增、修改或移除使用者關聯

**請求參數**:
```json
{
  "name": "張三",
  "department": "研發部",
  "position": "高級工程師",
  "user_id": 2,          // 可以更改關聯的使用者
  "status": "active"
}
```

**移除使用者關聯**:
```json
{
  "user_id": null        // 設為 null 可以清除關聯
}
```

**請求範例**:
```bash
# 更新使用者關聯
curl -X PUT "http://localhost:8282/api/persons/P001" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2
  }'

# 移除使用者關聯
curl -X PUT "http://localhost:8282/api/persons/P001" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": null
  }'
```

**回應範例**:
```json
{
  "id": 1,
  "person_id": "P001",
  "name": "張三",
  "department": "研發部",
  "position": "高級工程師",
  "user_id": 2,
  "user_name": "李四 (lisi)",  // 更新後的使用者名稱
  "status": "active",
  "extra_data": {},
  "face_encoding": "...",
  "created_at": "2025-10-17T12:34:56.789Z",
  "updated_at": "2025-10-17T12:45:00.000Z"
}
```

### 4. 查詢人員列表 (依使用者ID篩選)

**端點**: `GET /api/persons/`

**描述**: 取得人員列表，可以根據關聯的使用者ID進行篩選

**查詢參數**:
- `skip` (可選): 跳過筆數，預設 0
- `limit` (可選): 限制筆數，預設 100
- `status` (可選): 篩選狀態 (active/inactive)
- `department` (可選): 篩選部門
- `user_id` (可選): **新增** - 篩選關聯的使用者ID

**請求範例**:
```bash
# 查詢所有人員
curl -X GET "http://localhost:8282/api/persons/"

# 查詢特定使用者關聯的所有人員
curl -X GET "http://localhost:8282/api/persons/?user_id=1"

# 查詢技術部且有使用者關聯的人員
curl -X GET "http://localhost:8282/api/persons/?department=技術部&user_id=1"
```

**回應範例**:
```json
[
  {
    "id": 1,
    "person_id": "P001",
    "name": "張三",
    "department": "技術部",
    "position": "工程師",
    "user_id": 1,
    "user_name": "張三 (zhangsan)",  // 包含使用者名稱
    "status": "active",
    "extra_data": {},
    "face_encoding": "...",
    "created_at": "2025-10-17T12:34:56.789Z",
    "updated_at": "2025-10-17T12:34:56.789Z"
  }
]
```

### 5. 取得單一人員資訊

**端點**: `GET /api/persons/{person_id}`

**描述**: 取得特定人員的詳細資訊，包含關聯的使用者名稱

**請求範例**:
```bash
curl -X GET "http://localhost:8282/api/persons/P001"
```

**回應範例**:
```json
{
  "id": 1,
  "person_id": "P001",
  "name": "張三",
  "department": "技術部",
  "position": "工程師",
  "user_id": 1,
  "user_name": "張三 (zhangsan)",  // 關聯的使用者名稱
  "status": "active",
  "extra_data": {},
  "face_encoding": "...",
  "created_at": "2025-10-17T12:34:56.789Z",
  "updated_at": "2025-10-17T12:34:56.789Z"
}
```

## 使用場景

### 場景 1: 建立人員時關聯使用者

```python
import requests

# 1. 先取得可用的使用者列表
response = requests.get("http://localhost:8282/api/persons/users/options")
users = response.json()["data"]

print("可用的使用者:")
for user in users:
    print(f"  {user['value']}: {user['label']}")

# 2. 選擇使用者並建立人員
selected_user_id = users[0]["value"]

person_data = {
    "person_id": "P001",
    "name": "張三",
    "department": "技術部",
    "position": "工程師",
    "user_id": selected_user_id,
    "status": "active"
}

response = requests.post(
    "http://localhost:8282/api/persons/",
    json=person_data
)

person = response.json()
print(f"建立人員成功: {person['name']} (關聯使用者: {person['user_name']})")
```

### 場景 2: 查詢使用者關聯的所有人員

```python
import requests

user_id = 1

# 查詢該使用者關聯的所有人員
response = requests.get(
    f"http://localhost:8282/api/persons/",
    params={"user_id": user_id}
)

persons = response.json()
print(f"使用者 ID {user_id} 關聯的人員:")
for person in persons:
    print(f"  - {person['person_id']}: {person['name']} ({person['department']})")
```

### 場景 3: 前端下拉選單實現 (Vue 3)

```vue
<template>
  <div>
    <label>選擇關聯使用者:</label>
    <select v-model="selectedUserId">
      <option :value="null">-- 無關聯 --</option>
      <option
        v-for="user in userOptions"
        :key="user.value"
        :value="user.value"
      >
        {{ user.label }}
      </option>
    </select>

    <button @click="createPerson">建立人員</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const userOptions = ref([]);
const selectedUserId = ref(null);

onMounted(async () => {
  // 載入使用者選項
  const response = await axios.get('/api/persons/users/options');
  userOptions.value = response.data.data;
});

const createPerson = async () => {
  const personData = {
    person_id: 'P001',
    name: '張三',
    department: '技術部',
    position: '工程師',
    user_id: selectedUserId.value,  // 可能是 null
    status: 'active'
  };

  await axios.post('/api/persons/', personData);
  alert('人員建立成功！');
};
</script>
```

### 場景 4: 前端下拉選單實現 (React)

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function PersonForm() {
  const [userOptions, setUserOptions] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);

  useEffect(() => {
    // 載入使用者選項
    axios.get('/api/persons/users/options')
      .then(response => {
        setUserOptions(response.data.data);
      });
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const personData = {
      person_id: 'P001',
      name: '張三',
      department: '技術部',
      position: '工程師',
      user_id: selectedUserId,
      status: 'active'
    };

    await axios.post('/api/persons/', personData);
    alert('人員建立成功！');
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>選擇關聯使用者:</label>
      <select
        value={selectedUserId || ''}
        onChange={(e) => setSelectedUserId(e.target.value || null)}
      >
        <option value="">-- 無關聯 --</option>
        {userOptions.map(user => (
          <option key={user.value} value={user.value}>
            {user.label}
          </option>
        ))}
      </select>
      <button type="submit">建立人員</button>
    </form>
  );
}

export default PersonForm;
```

## 資料驗證

### 建立/更新時的驗證規則

1. **user_id 驗證**:
   - 如果提供了 `user_id`，系統會檢查該使用者是否存在
   - 如果使用者不存在，會返回 404 錯誤
   - 如果 `user_id` 為 `null`，則允許（清除關聯）

2. **person_id 唯一性**:
   - `person_id` 必須是唯一的
   - 建立時如果已存在，會返回 400 錯誤

### 錯誤處理範例

```bash
# 關聯不存在的使用者
curl -X POST "http://localhost:8282/api/persons/" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "P999",
    "name": "測試",
    "user_id": 9999
  }'

# 回應
{
  "detail": "User not found"
}
```

## 最佳實踐

### 1. 使用者選擇流程

```
1. 載入使用者選項 (GET /api/persons/users/options)
   ↓
2. 顯示下拉選單讓使用者選擇
   ↓
3. 建立/更新人員時傳入 user_id
   ↓
4. API 回應包含 user_name 供顯示使用
```

### 2. 關聯管理

- **建立人員時**: 可以直接指定 `user_id`，也可以稍後再更新
- **更新關聯**: 使用 PUT 端點更新 `user_id`
- **移除關聯**: 將 `user_id` 設為 `null`
- **查詢關聯**: 使用 `user_id` 參數篩選人員列表

### 3. 顯示使用者資訊

所有 Person 回應都包含 `user_name` 欄位：
- 如果有關聯: 顯示 `"張三 (zhangsan)"`
- 如果無關聯: `user_name` 為 `null`

## 資料庫查詢範例

### SQL 查詢範例

```sql
-- 查詢所有有使用者關聯的人員
SELECT
    p.*,
    u.user_name,
    u.username
FROM persons p
LEFT JOIN "user" u ON p.user_id = u.id
WHERE p.user_id IS NOT NULL;

-- 查詢特定使用者關聯的人員
SELECT
    p.*,
    u.user_name
FROM persons p
LEFT JOIN "user" u ON p.user_id = u.id
WHERE p.user_id = 1;

-- 查詢沒有使用者關聯的人員
SELECT * FROM persons WHERE user_id IS NULL;

-- 統計各使用者關聯的人員數量
SELECT
    u.user_name,
    COUNT(p.id) as person_count
FROM "user" u
LEFT JOIN persons p ON u.id = p.user_id
GROUP BY u.id, u.user_name;
```

## 相關文件

- [Persons API 文檔](./API.md#persons-api)
- [Users API 文檔](./API.md#users-api)
- [資料庫架構](./DATABASE_SCHEMA.md)

## 版本歷史

- **v1.1.0** (2025-10-17): 新增 user_id 關聯功能
  - 新增 user_id 欄位到 persons 表
  - 新增 /users/options 端點
  - 所有 Person 回應包含 user_name
  - 支援透過 user_id 篩選人員
