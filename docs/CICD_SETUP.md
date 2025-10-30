# CI/CD 自動部署設定指南

## 概述

本專案已經配置了 GitHub Actions 自動部署到生產環境。每次推送到 `main` 分支時，會自動觸發部署流程。

## 前置需求

### 1. GitHub Repository Secrets

需要在 GitHub Repository 設定以下 Secrets：

#### SSH_PRIVATE_KEY

這是用於連接到生產伺服器的 SSH 私鑰。

**設定步驟：**

1. 前往你的 GitHub Repository
2. 點擊 `Settings` > `Secrets and variables` > `Actions`
3. 點擊 `New repository secret`
4. Name: `SSH_PRIVATE_KEY`
5. Value: 貼上你的 SSH 私鑰內容

**取得 SSH 私鑰：**

```bash
# 在本地機器上讀取私鑰內容
cat "C:\Users\alish\我的雲端硬碟\Hash記事本\ssh\macmini\id_ed25519"
```

複製完整的私鑰內容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）。

## 部署流程

### 自動部署觸發條件

1. **Push to main branch**: 當代碼推送到 `main` 分支時自動觸發
2. **手動觸發**: 在 GitHub Actions 頁面可以手動觸發部署

### 部署步驟

GitHub Actions 會自動執行以下步驟：

1. ✅ Checkout 代碼
2. ✅ 設定 SSH 金鑰
3. ✅ 測試 SSH 連線
4. ✅ 清理舊的服務
5. ✅ 創建部署目錄
6. ✅ 部署應用程式檔案
7. ✅ 設定環境變數
8. ✅ 使用 Docker Compose 部署
9. ✅ 驗證部署
10. ✅ 清理 SSH 金鑰

### 手動觸發部署

如果需要手動部署：

1. 前往 GitHub Repository
2. 點擊 `Actions` 標籤
3. 選擇 `Deploy to Production` workflow
4. 點擊 `Run workflow` 按鈕
5. 選擇分支（通常是 `main`）
6. 點擊 `Run workflow` 確認

## 部署環境資訊

- **生產伺服器**: 210.61.69.175
- **SSH 用戶**: ysapi_backup
- **部署目錄**: ~/stream-motion-detect
- **API 端點**: https://detection-api.wyattst.net/api
- **WebSocket 端點**: wss://detection-api.wyattst.net/api/ws/violations

## 監控部署

### 查看部署日誌

在 GitHub Actions 頁面可以查看每次部署的詳細日誌。

### 驗證部署成功

部署完成後，會自動檢查以下項目：

1. API 健康檢查端點返回 200 狀態碼
2. Docker 容器正常運行
3. 資料庫連接正常

### 查看生產環境日誌

```bash
ssh -i "C:\Users\alish\我的雲端硬碟\Hash記事本\ssh\macmini\id_ed25519" ysapi_backup@210.61.69.175 'cd ~/stream-motion-detect && docker compose logs -f'
```

## 故障排除

### SSH 連接失敗

1. 確認 SSH_PRIVATE_KEY secret 已正確設定
2. 確認伺服器 IP 和用戶名正確
3. 檢查伺服器防火牆設定

### Docker Compose 失敗

1. 檢查 docker-compose.yml 配置
2. 確認 Docker 和 Docker Compose 已安裝
3. 查看容器日誌排查問題

### API 健康檢查失敗

1. 檢查容器是否正常運行
2. 查看 API 容器日誌
3. 確認資料庫連接正常
4. 檢查 nginx 配置

## 回滾部署

如果部署失敗需要回滾：

```bash
# SSH 到生產伺服器
ssh -i "C:\Users\alish\我的雲端硬碟\Hash記事本\ssh\macmini\id_ed25519" ysapi_backup@210.61.69.175

# 切換到專案目錄
cd ~/stream-motion-detect

# 拉取特定 commit
git fetch origin
git reset --hard <commit-hash>

# 重新部署
docker compose down
docker compose up -d --build
```

## 本地手動部署

如果 CI/CD 無法使用，可以使用本地部署腳本：

```bash
bash scripts/tools/deploy.sh
```

## 安全注意事項

1. ⚠️ 絕對不要將 SSH 私鑰提交到 Git
2. ⚠️ 定期更換 SSH 金鑰
3. ⚠️ 限制 SSH 金鑰的訪問權限
4. ⚠️ 使用不同的金鑰用於不同的環境（開發、測試、生產）
5. ⚠️ 在生產環境使用強密碼和 SESSION_SECRET

## 環境變數管理

生產環境的敏感資訊應該在伺服器的 `.env` 檔案中管理，不要提交到 Git。

**重要的環境變數：**

- `POSTGRES_PASSWORD`: 資料庫密碼
- `SESSION_SECRET`: Session 加密金鑰
- 其他 API keys 或敏感資訊

## 持續改進

### 未來可以添加的功能

1. 🚀 添加測試階段（單元測試、整合測試）
2. 🚀 添加程式碼品質檢查（linting, formatting）
3. 🚀 添加 Slack/Discord 通知
4. 🚀 添加自動回滾機制
5. 🚀 添加部署前的手動批准步驟
6. 🚀 支援多環境部署（staging, production）

## 聯絡資訊

如有問題，請聯繫開發團隊或查看 GitHub Issues。
