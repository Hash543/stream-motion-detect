#!/bin/bash

# Stream Motion Detect - 部署腳本
# 使用方法: ./deploy.sh

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 固定配置
REMOTE_HOST="210.61.69.175"
REMOTE_USER="ysapi_backup"
REMOTE_DIR="~/stream-motion-detect"
PROJECT_NAME="stream-motion-detect"
SSH_KEY="C:\Users\alish\我的雲端硬碟\Hash記事本\ssh\macmini\id_ed25519"
SSH_OPTS="-i \"${SSH_KEY}\""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stream Motion Detect 部署腳本${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "目標伺服器: ${YELLOW}${REMOTE_USER}@${REMOTE_HOST}${NC}"
echo -e "部署目錄: ${YELLOW}${REMOTE_DIR}${NC}"
echo ""

# 檢查 SSH 金鑰是否存在
echo -e "${YELLOW}[1/9] 檢查 SSH 金鑰...${NC}"
if [ ! -f "${SSH_KEY}" ]; then
    echo -e "${RED}✗ SSH 金鑰不存在: ${SSH_KEY}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH 金鑰存在${NC}"

# 檢查 SSH 連線
echo -e "${YELLOW}[2/9] 檢查 SSH 連線...${NC}"
if ssh -i "${SSH_KEY}" -o ConnectTimeout=5 -o BatchMode=yes "${REMOTE_USER}@${REMOTE_HOST}" exit 2>/dev/null; then
    echo -e "${GREEN}✓ SSH 連線成功${NC}"
else
    echo -e "${RED}✗ SSH 連線失敗，請檢查:${NC}"
    echo "  1. 伺服器 IP 是否正確: ${REMOTE_HOST}"
    echo "  2. SSH 金鑰權限: ${SSH_KEY}"
    echo "  3. 使用者名稱: ${REMOTE_USER}"
    echo "  4. 防火牆是否允許 SSH 連線"
    exit 1
fi

# 檢查遠端 Docker 環境
echo -e "${YELLOW}[3/9] 檢查遠端 Docker 環境...${NC}"
if ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" 'eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null; docker --version && docker compose version' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker 環境正常${NC}"
else
    echo -e "${RED}✗ 遠端伺服器未安裝 Docker 或 Docker Compose${NC}"
    echo "請先在遠端伺服器安裝 Docker"
    exit 1
fi

# 清理舊的 port 8001 服務
echo -e "${YELLOW}[4/9] 清理舊的 port 8001 服務...${NC}"
ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null

    # 查找並停止使用 port 8001 的容器
    OLD_CONTAINERS=$(docker ps -a --filter "publish=8001" --format "{{.ID}}" 2>/dev/null)
    if [ ! -z "$OLD_CONTAINERS" ]; then
        echo "發現舊容器，正在停止並移除..."
        docker stop $OLD_CONTAINERS 2>/dev/null || true
        docker rm $OLD_CONTAINERS 2>/dev/null || true
        echo "✓ 已移除使用 port 8001 的容器"
    else
        echo "未發現使用 port 8001 的容器"
    fi

    # 檢查是否有程序佔用 port 8001 (macOS 使用 lsof)
    if lsof -i :8001 2>/dev/null | grep -q "LISTEN"; then
        echo "警告: port 8001 仍被佔用"
        lsof -i :8001
    fi
ENDSSH
echo -e "${GREEN}✓ 舊服務清理完成${NC}"

# 建立遠端目錄
echo -e "${YELLOW}[5/9] 建立遠端部署目錄...${NC}"
ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_DIR}/{config,screenshots,logs,data,models}"
echo -e "${GREEN}✓ 目錄建立完成${NC}"

# 同步專案檔案到遠端伺服器
echo -e "${YELLOW}[6/9] 同步專案檔案到遠端伺服器...${NC}"

# 建立臨時 tar 檔案，排除不必要的檔案
tar -czf /tmp/deploy-stream-motion-detect.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='env' \
  --exclude='.vscode' \
  --exclude='.idea' \
  --exclude='logs/*.log' \
  --exclude='data/*.db' \
  --exclude='screenshots/*' \
  --exclude='test_screenshots' \
  --exclude='.env' \
  .

# 上傳並解壓
scp -i "${SSH_KEY}" /tmp/deploy-stream-motion-detect.tar.gz "${REMOTE_USER}@${REMOTE_HOST}:~/"
ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR} && tar -xzf ~/deploy-stream-motion-detect.tar.gz && rm ~/deploy-stream-motion-detect.tar.gz"
rm /tmp/deploy-stream-motion-detect.tar.gz

echo -e "${GREEN}✓ 檔案同步完成${NC}"

# 檢查並創建 .env 檔案
echo -e "${YELLOW}[7/9] 配置環境變數...${NC}"
ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR} && if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || echo '# PostgreSQL 資料庫設定
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DATABASE=motion-detector
POSTGRES_USER=face-motion
POSTGRES_PASSWORD=kkk12345

# Session Secret
SESSION_SECRET=your-secret-key-change-this-in-production

# 日誌設定
LOG_LEVEL=INFO

# 時區設定
TZ=Asia/Taipei' > .env; fi"
echo -e "${GREEN}✓ 環境變數配置完成${NC}"

# 部署 Docker 容器
echo -e "${YELLOW}[8/9] 啟動 Docker 容器...${NC}"
ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" 'eval "$(/opt/homebrew/bin/brew shellenv)" && cd '"${REMOTE_DIR}"' && docker compose down && docker compose up -d --build'
echo -e "${GREEN}✓ 容器啟動完成${NC}"

# 檢查服務狀態
echo -e "${YELLOW}[9/9] 檢查服務狀態...${NC}"
sleep 5
ssh -i "${SSH_KEY}" "${REMOTE_USER}@${REMOTE_HOST}" 'eval "$(/opt/homebrew/bin/brew shellenv)" && cd '"${REMOTE_DIR}"' && docker compose ps'

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "服務訪問地址:"
echo -e "  HTTP:  ${YELLOW}http://${REMOTE_HOST}${NC}"
echo -e "  API:   ${YELLOW}http://${REMOTE_HOST}/api/health${NC}"
echo -e "  直連:  ${YELLOW}http://${REMOTE_HOST}:8282/api/health${NC}"
echo ""
echo -e "查看服務日誌:"
echo -e "  ${YELLOW}ssh -i \"${SSH_KEY}\" ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR} && docker compose logs -f'${NC}"
echo ""
echo -e "停止服務:"
echo -e "  ${YELLOW}ssh -i \"${SSH_KEY}\" ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR} && docker compose down'${NC}"
echo ""
