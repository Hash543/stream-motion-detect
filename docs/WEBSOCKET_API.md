# WebSocket API 文檔

## 概述

本系統提供 WebSocket 服務，用於即時推送違規事件通知給前端客戶端。當監控系統檢測到違規行為（如未戴安全帽、瞌睡、靜止偵測等）時，會立即通過 WebSocket 推送通知。

## 連接端點

### WebSocket URL

```
ws://localhost:8282/api/ws/violations
```

生產環境:
```
wss://your-domain.com/api/ws/violations
```

## 訊息格式

### 1. 連接確認訊息 (Connection)

當客戶端成功連接到 WebSocket 服務器時，會收到確認訊息：

```json
{
  "type": "connection",
  "message": "Connected to violation notification service",
  "timestamp": "2025-10-16T12:34:56.789Z",
  "active_connections": 3
}
```

**欄位說明:**
- `type`: 訊息類型，值為 `"connection"`
- `message`: 連接成功訊息
- `timestamp`: 伺服器時間戳
- `active_connections`: 當前活躍連接數

### 2. 違規通知訊息 (Violation)

當系統檢測到違規時，會推送以下格式的訊息：

```json
{
  "type": "violation",
  "timestamp": "2025-10-16T12:34:56.789Z",
  "data": {
    "id": 123,
    "violation_type": "helmet",
    "camera_id": "camera_001",
    "stream_id": "stream_001",
    "confidence": 0.95,
    "person_id": "P001",
    "severity": "高等",
    "lat": 25.033,
    "lng": 121.565,
    "address": "台北市信義區",
    "image_path": "/uploads/violations/2025-10-16/violation_123.jpg",
    "bbox": [100, 150, 200, 300],
    "created_at": "2025-10-16T12:34:56.789Z"
  }
}
```

**data 欄位說明:**
- `id`: 違規事件 ID（對應 alert_event 表的 ID）
- `violation_type`: 違規類型
  - `"helmet"`: 未戴安全帽
  - `"drowsiness"`: 瞌睡檢測
  - `"inactivity"`: 靜止偵測
  - `"face"`: 人臉識別
- `camera_id`: 攝像頭 ID
- `stream_id`: 串流 ID
- `confidence`: 信心度 (0.0 ~ 1.0)
- `person_id`: 人員 ID（如果有識別到）
- `severity`: 嚴重程度
  - `"高等"`: confidence >= 0.9
  - `"中等"`: 0.7 <= confidence < 0.9
  - `"低等"`: confidence < 0.7
- `lat`: 緯度（如果有）
- `lng`: 經度（如果有）
- `address`: 地址（如果有）
- `image_path`: 違規截圖路徑
- `bbox`: 邊界框 [x, y, width, height]
- `created_at`: 建立時間

### 3. Pong 回應訊息

當客戶端發送 Ping 時，會收到 Pong 回應：

```json
{
  "type": "pong",
  "timestamp": "2025-10-16T12:34:56.789Z"
}
```

## 客戶端發送訊息

### Ping 訊息

客戶端可以定期發送 Ping 訊息來保持連接活躍：

```json
{
  "type": "ping"
}
```

## 使用範例

### JavaScript (原生 WebSocket)

```javascript
// 建立 WebSocket 連接
const ws = new WebSocket('ws://localhost:8282/api/ws/violations');

// 連接成功
ws.onopen = () => {
  console.log('WebSocket connected');
};

// 接收訊息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Message received:', data);

  if (data.type === 'violation') {
    // 處理違規通知
    handleViolation(data.data);
  }
};

// 連接錯誤
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// 連接關閉
ws.onclose = () => {
  console.log('WebSocket disconnected');
  // 可以在這裡實現重連邏輯
};

// 發送 Ping
function sendPing() {
  ws.send(JSON.stringify({ type: 'ping' }));
}

// 處理違規通知
function handleViolation(violation) {
  alert(`違規檢測: ${violation.violation_type} at ${violation.camera_id}`);
  // 顯示通知、更新 UI 等
}
```

### Vue 3 Composition API

```typescript
// useWebSocket.ts
import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket(url: string) {
  const ws = ref<WebSocket | null>(null);
  const isConnected = ref(false);
  const violations = ref<any[]>([]);

  const connect = () => {
    ws.value = new WebSocket(url);

    ws.value.onopen = () => {
      isConnected.value = true;
      console.log('WebSocket connected');
    };

    ws.value.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'violation' && message.data) {
        violations.value.unshift(message.data);
      }
    };

    ws.value.onclose = () => {
      isConnected.value = false;
      console.log('WebSocket disconnected');
    };
  };

  const disconnect = () => {
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
  };

  onMounted(() => {
    connect();
  });

  onUnmounted(() => {
    disconnect();
  });

  return {
    ws,
    isConnected,
    violations,
    connect,
    disconnect
  };
}
```

```vue
<!-- Component.vue -->
<template>
  <div>
    <div v-if="isConnected" class="status-connected">已連接</div>
    <div v-else class="status-disconnected">未連接</div>

    <div v-for="violation in violations" :key="violation.id">
      <div class="violation-alert">
        {{ violation.violation_type }} - {{ violation.camera_id }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { useWebSocket } from '@/hooks/useWebSocket';

const wsUrl = 'ws://localhost:8282/api/ws/violations';
const { isConnected, violations } = useWebSocket(wsUrl);
</script>
```

### React

```javascript
import { useEffect, useState } from 'react';

function useWebSocket(url) {
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [violations, setViolations] = useState([]);

  useEffect(() => {
    const websocket = new WebSocket(url);

    websocket.onopen = () => {
      setIsConnected(true);
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'violation' && message.data) {
        setViolations(prev => [message.data, ...prev]);
      }
    };

    websocket.onclose = () => {
      setIsConnected(false);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [url]);

  return { ws, isConnected, violations };
}

function App() {
  const { isConnected, violations } = useWebSocket('ws://localhost:8282/api/ws/violations');

  return (
    <div>
      <div>{isConnected ? '已連接' : '未連接'}</div>
      {violations.map(v => (
        <div key={v.id}>
          {v.violation_type} - {v.camera_id}
        </div>
      ))}
    </div>
  );
}
```

## 連接管理

### 自動重連

建議實現自動重連機制：

```javascript
let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 3000; // 3 seconds

function connect() {
  ws = new WebSocket('ws://localhost:8282/api/ws/violations');

  ws.onopen = () => {
    reconnectAttempts = 0;
    console.log('Connected');
  };

  ws.onclose = () => {
    console.log('Disconnected');

    if (reconnectAttempts < maxReconnectAttempts) {
      reconnectAttempts++;
      console.log(`Reconnecting in ${reconnectDelay}ms (${reconnectAttempts}/${maxReconnectAttempts})`);
      setTimeout(connect, reconnectDelay);
    }
  };
}

connect();
```

### 心跳保持

定期發送 Ping 訊息保持連接：

```javascript
let pingInterval = null;

ws.onopen = () => {
  // 每 30 秒發送一次 Ping
  pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, 30000);
};

ws.onclose = () => {
  if (pingInterval) {
    clearInterval(pingInterval);
  }
};
```

## 測試

### 使用測試頁面

打開瀏覽器訪問：
```
file:///D:/stream-motion-detect/test_websocket.html
```

或使用 Python 簡單 HTTP 服務器：
```bash
cd D:\stream-motion-detect
python -m http.server 8000
```

然後訪問：
```
http://localhost:8000/test_websocket.html
```

### 使用 wscat 命令行工具

```bash
npm install -g wscat
wscat -c ws://localhost:8282/api/ws/violations
```

### 使用 Postman

1. 創建新的 WebSocket 請求
2. URL: `ws://localhost:8282/api/ws/violations`
3. 點擊 Connect
4. 接收即時違規通知

## API 端點

### 查詢連接資訊

**GET** `/api/ws/connections`

回應範例:
```json
{
  "status": "success",
  "data": {
    "active_connections": 5,
    "timestamp": "2025-10-16T12:34:56.789Z"
  }
}
```

## 錯誤處理

### 連接失敗

- 確認 API 服務器正在運行
- 檢查 WebSocket URL 是否正確
- 確認防火牆沒有阻擋 WebSocket 連接
- 檢查瀏覽器是否支持 WebSocket

### 訊息解析失敗

- 確保接收到的是有效的 JSON 格式
- 檢查訊息格式是否符合文檔規範

## 安全性考慮

### 生產環境建議

1. **使用 WSS (WebSocket Secure)**
   ```
   wss://your-domain.com/api/ws/violations
   ```

2. **添加身份驗證**
   - 可以在連接時傳遞 token
   - 或在初始訊息中驗證身份

3. **速率限制**
   - 限制每個客戶端的連接數
   - 限制訊息發送頻率

4. **CORS 設定**
   - 限制允許連接的來源域名

## 性能優化

1. **訊息批處理**: 將多個違規事件合併成一個訊息發送
2. **訊息壓縮**: 對大型訊息進行壓縮
3. **連接池管理**: 限制最大連接數
4. **內存管理**: 定期清理斷開的連接

## 故障排除

### 連接立即斷開

檢查服務器日誌：
```bash
tail -f logs/app.log | grep WebSocket
```

### 收不到違規通知

1. 確認監控系統正在運行
2. 確認有攝像頭正在檢測
3. 檢查規則引擎是否啟用
4. 查看服務器日誌確認違規是否被觸發

### 連接頻繁斷開

1. 增加心跳頻率
2. 檢查網絡穩定性
3. 調整服務器超時設定

## 相關文件

- [API 文檔](./API.md)
- [部署指南](./DEPLOYMENT.md)
- [開發指南](./DEVELOPMENT.md)

## 版本歷史

- **v1.0.0** (2025-10-16): 初始版本，支持基本違規通知推送
