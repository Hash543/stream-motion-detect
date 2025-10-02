# 建置與部署指南

## 專案架構

```
stream-motion-detect/
├── config/                 # 設定檔目錄
│   └── config.json         # 主要設定檔
├── src/                    # 原始碼
│   ├── managers/           # 管理模組
│   │   ├── config_manager.py
│   │   ├── rtsp_manager.py
│   │   ├── universal_stream_manager.py
│   │   ├── screenshot_manager.py
│   │   ├── notification_sender.py
│   │   ├── database_manager.py
│   │   ├── face_detection_manager.py
│   │   └── helmet_violation_manager.py
│   ├── detectors/          # AI檢測模組（保留供未來擴充）
│   └── monitoring_system.py
├── screenshots/            # 截圖儲存目錄
├── logs/                   # 日誌檔案目錄
├── models/                 # AI模型檔案
├── data/                   # 資料庫檔案
├── docs/                   # 文件目錄
├── main.py                 # 主程式進入點
├── start_system.py         # 簡化啟動腳本
├── requirements.txt        # Python套件需求
├── requirements_minimal.txt
├── requirements_streaming.txt
└── README.md
```

## 開發環境建置

### 1. 設定開發環境

```bash
# 克隆專案
git clone https://github.com/your-repo/stream-motion-detect.git
cd stream-motion-detect

# 建立虛擬環境
python -m venv venv

# 啟用虛擬環境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安裝開發依賴
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如有開發專用依賴
```

### 2. IDE設定

#### VS Code
建議安裝擴充功能：
- Python
- Pylance
- Python Test Explorer
- GitLens

`.vscode/settings.json` 範例：
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
```

#### PyCharm
1. 開啟專案目錄
2. 設定 Python 解譯器為 `venv/bin/python`
3. 標記 `src/` 為 Sources Root
4. 啟用 PEP 8 檢查

### 3. 程式碼品質工具

安裝程式碼檢查工具：
```bash
pip install black pylint flake8 mypy
```

執行程式碼格式化：
```bash
# 格式化程式碼
black src/

# 檢查程式碼品質
pylint src/
flake8 src/

# 類型檢查
mypy src/
```

## 測試

### 單元測試

```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_face_detection.py

# 產生覆蓋率報告
pytest --cov=src --cov-report=html
```

### 整合測試

```bash
# 測試RTSP串流
python test_streams.py

# 測試人臉檢測
python test_face_detection.py

# 測試安全帽檢測間隔
python test_helmet_interval.py

# 測試人臉歸檔
python test_face_filing.py
```

### 效能測試

```bash
# 監控CPU和記憶體使用
python -m memory_profiler start_system.py

# 檢查處理延遲
python benchmark.py
```

## 建置流程

### 1. 準備發布版本

```bash
# 清理暫存檔案
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# 更新版本號
# 編輯 src/__init__.py
__version__ = "1.0.0"

# 產生需求檔案（如有更新）
pip freeze > requirements.txt
```

### 2. 建立發布套件

```bash
# 安裝建置工具
pip install build

# 建置套件
python -m build

# 這會產生：
# dist/stream_motion_detect-1.0.0.tar.gz
# dist/stream_motion_detect-1.0.0-py3-none-any.whl
```

## 部署方式

### 方法1: 直接部署

#### Windows

1. 準備部署目錄：
```powershell
mkdir C:\StreamMonitor
cd C:\StreamMonitor
```

2. 複製檔案：
```powershell
# 複製專案檔案
xcopy /E /I C:\path\to\stream-motion-detect C:\StreamMonitor

# 建立虛擬環境
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. 設定系統服務（使用NSSM）：
```powershell
# 下載NSSM: https://nssm.cc/download
nssm install StreamMonitor C:\StreamMonitor\venv\Scripts\python.exe C:\StreamMonitor\start_system.py
nssm set StreamMonitor AppDirectory C:\StreamMonitor
nssm start StreamMonitor
```

#### Linux (Ubuntu/Debian)

1. 準備部署目錄：
```bash
sudo mkdir -p /opt/stream-monitor
cd /opt/stream-monitor
```

2. 複製檔案並設定：
```bash
# 複製專案
sudo cp -r /path/to/stream-motion-detect/* .

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 設定權限
sudo chown -R monitor:monitor /opt/stream-monitor
```

3. 建立systemd服務：

`/etc/systemd/system/stream-monitor.service`：
```ini
[Unit]
Description=RTSP Stream Motion Detection System
After=network.target

[Service]
Type=simple
User=monitor
WorkingDirectory=/opt/stream-monitor
Environment="PATH=/opt/stream-monitor/venv/bin"
ExecStart=/opt/stream-monitor/venv/bin/python start_system.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟動服務：
```bash
sudo systemctl daemon-reload
sudo systemctl enable stream-monitor
sudo systemctl start stream-monitor
sudo systemctl status stream-monitor
```

### 方法2: Docker部署

#### 建立Dockerfile

`Dockerfile`：
```dockerfile
FROM python:3.11-slim

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製需求檔案
COPY requirements.txt .

# 安裝Python套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式
COPY . .

# 建立必要目錄
RUN mkdir -p screenshots logs data

# 暴露端口（如需API）
EXPOSE 8000

# 啟動命令
CMD ["python", "start_system.py"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  stream-monitor:
    build: .
    container_name: stream-monitor
    restart: unless-stopped
    volumes:
      - ./config:/app/config
      - ./screenshots:/app/screenshots
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - TZ=Asia/Taipei
    network_mode: host  # 用於RTSP串流
    # 或使用 ports:
    # ports:
    #   - "8000:8000"
```

#### 建置與執行

```bash
# 建置Docker映像
docker-compose build

# 啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

### 方法3: Kubernetes部署

#### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stream-monitor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stream-monitor
  template:
    metadata:
      labels:
        app: stream-monitor
    spec:
      containers:
      - name: stream-monitor
        image: your-registry/stream-monitor:latest
        resources:
          limits:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: 1
          requests:
            memory: "8Gi"
            cpu: "2"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: screenshots
          mountPath: /app/screenshots
        - name: data
          mountPath: /app/data
      volumes:
      - name: config
        configMap:
          name: stream-monitor-config
      - name: screenshots
        persistentVolumeClaim:
          claimName: screenshots-pvc
      - name: data
        persistentVolumeClaim:
          claimName: data-pvc
```

## 環境配置

### 生產環境設定

`config/config.production.json`：
```json
{
  "system": {
    "environment": "production",
    "log_level": "INFO",
    "use_gpu": true
  },
  "rtsp_sources": [
    {
      "id": "camera_001",
      "url": "rtsp://192.168.1.100:554/stream1",
      "location": "入口"
    }
  ],
  "detection_settings": {
    "processing_fps": 2,
    "helmet_confidence_threshold": 0.8
  },
  "notification_api": {
    "endpoint": "https://api.production.com/violations",
    "timeout": 10,
    "retry_attempts": 3
  },
  "storage": {
    "screenshot_path": "/data/screenshots/",
    "max_storage_days": 30
  }
}
```

### 環境變數

支援使用環境變數覆蓋設定：

```bash
# .env 檔案
RTSP_URL_1=rtsp://192.168.1.100:554/stream1
NOTIFICATION_ENDPOINT=https://api.production.com/violations
LOG_LEVEL=INFO
USE_GPU=true
```

在程式中讀取：
```python
import os
from dotenv import load_dotenv

load_dotenv()

rtsp_url = os.getenv('RTSP_URL_1')
notification_endpoint = os.getenv('NOTIFICATION_ENDPOINT')
```

## 監控與維護

### 日誌管理

#### 日誌輪替（Linux）

`/etc/logrotate.d/stream-monitor`：
```
/opt/stream-monitor/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 monitor monitor
    sharedscripts
    postrotate
        systemctl reload stream-monitor
    endscript
}
```

#### Windows事件日誌

配置系統將日誌輸出到Windows事件檢視器：
```python
import logging
import logging.handlers

handler = logging.handlers.NTEventLogHandler('StreamMonitor')
logger.addHandler(handler)
```

### 健康檢查

建立健康檢查端點：
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "uptime": get_uptime(),
        "cameras_active": get_active_cameras(),
        "version": __version__
    }
```

### 效能監控

使用Prometheus監控：
```python
from prometheus_client import Counter, Histogram, start_http_server

# 定義指標
frames_processed = Counter('frames_processed_total', 'Total frames processed')
detection_duration = Histogram('detection_duration_seconds', 'Detection duration')

# 啟動metrics服務
start_http_server(9090)
```

## 更新與升級

### 版本更新流程

```bash
# 1. 備份當前版本
cp -r /opt/stream-monitor /opt/stream-monitor.backup

# 2. 停止服務
sudo systemctl stop stream-monitor

# 3. 更新程式碼
cd /opt/stream-monitor
git pull origin main

# 4. 更新依賴
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 5. 執行資料庫遷移（如需要）
python migrate_database.py

# 6. 重啟服務
sudo systemctl start stream-monitor

# 7. 驗證
sudo systemctl status stream-monitor
tail -f logs/monitoring.log
```

### 零停機更新（使用藍綠部署）

```bash
# 部署新版本到green環境
# 切換流量到green
# 驗證green環境正常
# 停止blue環境
```

## 備份與恢復

### 備份腳本

```bash
#!/bin/bash
BACKUP_DIR="/backup/stream-monitor"
DATE=$(date +%Y%m%d_%H%M%S)

# 備份資料庫
cp /opt/stream-monitor/data/monitoring.db $BACKUP_DIR/db_$DATE.db

# 備份設定檔
cp /opt/stream-monitor/config/config.json $BACKUP_DIR/config_$DATE.json

# 備份最近7天的截圖
find /opt/stream-monitor/screenshots -mtime -7 -type f -exec cp {} $BACKUP_DIR/screenshots/ \;

# 壓縮備份
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*
```

### 恢復步驟

```bash
# 1. 解壓備份
tar -xzf backup_20240315_120000.tar.gz

# 2. 恢復資料庫
cp db_20240315_120000.db /opt/stream-monitor/data/monitoring.db

# 3. 恢復設定
cp config_20240315_120000.json /opt/stream-monitor/config/config.json

# 4. 重啟服務
sudo systemctl restart stream-monitor
```

## 安全性考量

### 1. 網路安全

- 使用防火牆限制RTSP連接來源
- 啟用HTTPS for API通知
- 使用VPN連接遠端攝影機

### 2. 認證與授權

- RTSP連接使用強密碼
- API通知使用token認證
- 定期輪換認證憑證

### 3. 資料保護

- 加密敏感設定檔案
- 截圖檔案設定適當權限
- 定期清理舊資料

```bash
# 設定檔案權限
chmod 600 config/config.json
chmod 700 data/
chmod 755 screenshots/
```

## 故障排除

### 常見部署問題

1. **服務無法啟動**
   - 檢查日誌：`journalctl -u stream-monitor -n 50`
   - 驗證設定檔：`python main.py --validate-config`
   - 檢查權限：`ls -la /opt/stream-monitor`

2. **記憶體不足**
   - 降低處理頻率
   - 減少同時處理的攝影機
   - 增加系統swap空間

3. **GPU不可用**
   - 檢查CUDA安裝：`nvidia-smi`
   - 驗證PyTorch CUDA：`python -c "import torch; print(torch.cuda.is_available())"`
   - 安裝對應的CUDA版本

## 效能基準

### 參考配置

| 硬體規格 | 攝影機數 | 處理FPS | CPU使用 | 記憶體使用 | GPU使用 |
|---------|---------|--------|---------|-----------|---------|
| i7-9700K, RTX 3060 | 4 | 2 | 35% | 6GB | 45% |
| i9-11900K, RTX 4070 | 8 | 2 | 45% | 10GB | 60% |
| Xeon E5-2680, Tesla T4 | 16 | 1 | 60% | 18GB | 75% |

## 下一步

- [使用指南](usage.md) - 了解如何使用系統
- [開發指南](development.md) - 擴充功能開發
- [API文件](api.md) - API接口說明
