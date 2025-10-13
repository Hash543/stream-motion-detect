# 部署指南

本文檔說明如何將 Stream Motion Detect 服務透過 SSH 部署到遠端伺服器。

## 目標伺服器資訊

- **伺服器 IP**: 210.61.69.175
- **部署目錄**: `/opt/stream-motion-detect`

## 前置需求

### 本地環境
- Git
- SSH 客戶端
- rsync（用於檔案同步）

### 遠端伺服器需求
- Ubuntu/Debian Linux
- Docker Engine (>= 20.10)
- Docker Compose (>= 2.0)
- SSH 服務已啟用
- 足夠的磁碟空間（建議至少 10GB）

## 部署步驟

### 1. 設定 SSH 金鑰（首次部署）

如果尚未設定 SSH 金鑰認證，請執行：

```bash
# 生成 SSH 金鑰（如果還沒有）
ssh-keygen -t rsa -b 4096

# 複製公鑰到遠端伺服器
ssh-copy-id root@210.61.69.175
```

### 2. 確認遠端伺服器 Docker 環境

登入遠端伺服器並安裝 Docker：

```bash
ssh root@210.61.69.175

# 安裝 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安裝 Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 驗證安裝
docker --version
docker compose version
```

### 3. 使用自動化部署腳本

在本地專案目錄執行：

```bash
# 賦予腳本執行權限
chmod +x deploy.sh

# 執行部署（使用預設伺服器 210.61.69.175）
./deploy.sh

# 或指定自訂伺服器和使用者
./deploy.sh 210.61.69.175 root
```

部署腳本會自動執行以下步驟：
1. 檢查 SSH 連線
2. 檢查遠端 Docker 環境
3. 建立部署目錄結構
4. 同步專案檔案
5. 配置環境變數
6. 建置並啟動 Docker 容器
7. 檢查服務狀態

### 4. 手動部署（可選）

如果不使用自動化腳本，可以手動執行以下步驟：

```bash
# 1. 同步檔案到遠端伺服器
rsync -avz --progress \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='venv' \
  --exclude='logs/*.log' \
  --exclude='data/*.db' \
  --exclude='screenshots/*' \
  ./ root@210.61.69.175:/opt/stream-motion-detect/

# 2. SSH 登入遠端伺服器
ssh root@210.61.69.175

# 3. 進入部署目錄
cd /opt/stream-motion-detect

# 4. 創建環境變數檔案
cp .env.example .env
nano .env  # 根據需要修改配置

# 5. 啟動服務
docker compose down
docker compose up -d --build

# 6. 查看服務狀態
docker compose ps
docker compose logs -f
```

## 服務配置

### 環境變數配置

編輯 `.env` 檔案來配置服務：

```bash
# 在遠端伺服器上
cd /opt/stream-motion-detect
nano .env
```

重要配置項：
- `DATABASE_URL`: 資料庫連線字串
- `LOG_LEVEL`: 日誌等級（DEBUG, INFO, WARNING, ERROR）
- `TZ`: 時區設定（Asia/Taipei）
- `API_PORT`: API 服務端口（預設 8282）

### 端口說明

- **80**: Nginx HTTP（對外）
- **443**: Nginx HTTPS（對外，需配置 SSL）
- **8282**: API 服務（內部，透過 Nginx 反向代理）

## 服務管理

### 查看服務狀態

```bash
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose ps'
```

### 查看日誌

```bash
# 查看所有服務日誌
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose logs -f'

# 查看特定服務日誌
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose logs -f api'
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose logs -f monitor'
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose logs -f nginx'
```

### 重啟服務

```bash
# 重啟所有服務
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose restart'

# 重啟特定服務
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose restart api'
```

### 停止服務

```bash
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose down'
```

### 更新部署

當程式碼有更新時，重新執行部署腳本：

```bash
./deploy.sh
```

## 驗證部署

部署完成後，檢查以下端點：

```bash
# 健康檢查（透過 Nginx）
curl http://210.61.69.175/api/health

# 健康檢查（直連 API）
curl http://210.61.69.175:8282/api/health

# 測試頁面
curl http://210.61.69.175/test
```

或在瀏覽器中訪問：
- http://210.61.69.175/api/health
- http://210.61.69.175/test

## 故障排除

### 1. SSH 連線失敗

```bash
# 測試 SSH 連線
ssh -v root@210.61.69.175

# 檢查防火牆
ssh root@210.61.69.175 'sudo ufw status'
```

### 2. Docker 容器無法啟動

```bash
# 查看容器狀態
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose ps -a'

# 查看錯誤日誌
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose logs'

# 檢查磁碟空間
ssh root@210.61.69.175 'df -h'
```

### 3. 服務無法訪問

```bash
# 檢查端口監聽
ssh root@210.61.69.175 'netstat -tlnp | grep -E "80|8282"'

# 檢查防火牆規則
ssh root@210.61.69.175 'sudo iptables -L -n | grep -E "80|8282"'

# 檢查 Docker 網路
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose exec api ping -c 3 nginx'
```

### 4. 重建容器

如果遇到嚴重問題，可以完全重建：

```bash
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && docker compose down -v && docker compose up -d --build'
```

## 安全建議

1. **防火牆配置**：只開放必要的端口（80, 443, 22）
2. **SSH 安全**：
   - 使用金鑰認證，禁用密碼登入
   - 更改預設 SSH 端口
   - 設定 fail2ban
3. **SSL/TLS**：使用 Let's Encrypt 配置 HTTPS
4. **定期更新**：定期更新系統和 Docker 映像
5. **備份**：定期備份 `data`、`config` 和 `screenshots` 目錄

## 備份與恢復

### 備份資料

```bash
# 備份整個資料目錄
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && tar -czf backup-$(date +%Y%m%d).tar.gz data/ config/ screenshots/'

# 下載備份到本地
scp root@210.61.69.175:/opt/stream-motion-detect/backup-*.tar.gz ./backups/
```

### 恢復資料

```bash
# 上傳備份到伺服器
scp ./backups/backup-20250112.tar.gz root@210.61.69.175:/opt/stream-motion-detect/

# 解壓恢復
ssh root@210.61.69.175 'cd /opt/stream-motion-detect && tar -xzf backup-20250112.tar.gz'
```

## 監控建議

建議配置以下監控：
- Docker 容器健康狀態
- 磁碟空間使用率
- API 回應時間
- 錯誤日誌告警

可以使用工具如：
- Prometheus + Grafana
- ELK Stack
- Docker Stats

## 技術支援

如遇到問題，請檢查：
1. 容器日誌：`docker compose logs`
2. 系統日誌：`/opt/stream-motion-detect/logs/`
3. Docker 狀態：`docker compose ps`

---

**最後更新**: 2025-01-12
