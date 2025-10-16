# 工具腳本 (Tools Scripts)

本目錄包含系統維護、部署和資料管理工具。

## Python 工具

### `install_requirements.py`
**用途**: 安裝 Python 依賴套件

**功能**:
- 讀取 requirements.txt
- 自動安裝所有依賴
- 處理安裝錯誤

**執行方式**:
```bash
python scripts/tools/install_requirements.py
```

### `fix_rule_data.py`
**用途**: 修復規則資料

**功能**:
- 檢查規則資料完整性
- 修復損壞的規則記錄
- 更新規則配置

**執行方式**:
```bash
python scripts/tools/fix_rule_data.py
```

**使用時機**:
- 規則資料損壞時
- 升級後規則格式不符時
- 手動修正規則錯誤後

### `init_default_rules.py`
**用途**: 初始化預設規則

**功能**:
- 建立系統預設偵測規則
- 檢查規則是否已存在
- 僅插入不存在的規則

**執行方式**:
```bash
python scripts/tools/init_default_rules.py
```

**預設規則包含**:
- 安全帽偵測規則
- 人臉識別規則
- 異常行為偵測規則
- 靜止偵測規則

### `init_default_rules_force.py`
**用途**: 強制重新初始化預設規則

**功能**:
- 刪除所有現有規則
- 重新建立預設規則
- 重置規則配置

**執行方式**:
```bash
python scripts/tools/init_default_rules_force.py
```

**警告**:
- 會刪除所有自訂規則
- 建議先備份資料庫
- 僅在規則系統完全損壞時使用

## Shell 腳本

### `deploy.sh`
**用途**: 部署腳本

**功能**:
- 自動化部署流程
- 建立 Docker 容器
- 啟動服務

**執行方式**:
```bash
bash scripts/tools/deploy.sh
```

**部署流程**:
1. 檢查環境變數
2. 建立/更新 Docker 映像
3. 啟動資料庫服務
4. 執行資料庫遷移
5. 啟動 API 服務
6. 啟動監控服務

**環境需求**:
- Docker
- Docker Compose
- .env 檔案已正確設定

## 使用指南

### 首次部署

```bash
# 1. 安裝依賴
python scripts/tools/install_requirements.py

# 2. 初始化規則
python scripts/tools/init_default_rules.py

# 3. 部署系統
bash scripts/tools/deploy.sh
```

### 維護作業

```bash
# 修復規則資料
python scripts/tools/fix_rule_data.py

# 重置規則（謹慎使用）
python scripts/tools/init_default_rules_force.py
```

## 注意事項

1. **執行權限**: 確保腳本有執行權限
   ```bash
   chmod +x scripts/tools/*.sh
   ```

2. **環境變數**: 執行前確認 .env 檔案已正確設定

3. **備份**: 執行破壞性操作前先備份資料庫
   ```bash
   pg_dump -U face-motion motion-detector > backup.sql
   ```

4. **日誌**: 工具執行時會輸出詳細日誌，注意查看錯誤訊息

## 常見問題

### Q: install_requirements.py 安裝失敗
A:
- 檢查 Python 版本 (需要 Python 3.8+)
- 確認網路連線
- 嘗試使用 pip install -r requirements.txt 手動安裝

### Q: 部署腳本執行失敗
A:
- 檢查 Docker 服務是否運行
- 確認 .env 檔案存在
- 查看 Docker logs 了解詳細錯誤

### Q: 規則初始化後沒有生效
A:
- 重啟 API 服務
- 檢查資料庫連線
- 確認規則資料是否正確寫入
