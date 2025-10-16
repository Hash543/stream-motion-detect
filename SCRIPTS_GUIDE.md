# 腳本使用指南

本文件提供專案中所有腳本的快速參考。

## 目錄結構

```
scripts/
├── db/          # 資料庫腳本 (8 個檔案)
│   ├── setup_postgres.sql                  # PostgreSQL 初始化
│   ├── migration_seed_data.sql             # 資料遷移和種子資料
│   ├── sync_database.py                    # 自動化同步工具
│   ├── migrate_to_postgres.py              # MySQL → PostgreSQL
│   ├── migrate_sqlite_to_postgres.py       # SQLite → PostgreSQL
│   ├── create_pg_tables.py                 # 建立表結構
│   ├── verify_pg_migration.py              # 驗證遷移
│   ├── check_sqlite_data.py                # 檢查 SQLite
│   └── README.md
│
├── tools/       # 工具腳本 (5 個檔案)
│   ├── install_requirements.py             # 安裝依賴
│   ├── fix_rule_data.py                    # 修復規則
│   ├── init_default_rules.py               # 初始化規則
│   ├── init_default_rules_force.py         # 強制重置規則
│   ├── deploy.sh                           # 部署腳本
│   └── README.md
│
└── test/        # 測試腳本 (12 個檔案)
    ├── test_api.py                         # API 測試
    ├── test_users_api.py                   # 使用者 API 測試
    ├── test_postgres.py                    # PostgreSQL 測試
    ├── test_pg_connection.py               # 連線測試
    ├── test_app_pg_connection.py           # 應用程式連線測試
    ├── test_streams.py                     # 串流測試 (中文)
    ├── test_streams_en.py                  # 串流測試 (英文)
    ├── test_face_detection.py              # 人臉偵測測試
    ├── test_face_filing.py                 # 人臉歸檔測試
    ├── test_helmet_detection_with_face.py  # 安全帽偵測測試
    ├── test_helmet_interval.py             # 間隔偵測測試
    ├── test_inactivity_detection.py        # 靜止偵測測試
    └── README.md
```

## 常用操作快速參考

### 資料庫初始化

```bash
# 方法1: 使用 pgAdmin (推薦)
# 1. 開啟 pgAdmin
# 2. 使用 postgres 使用者連接
# 3. 執行 scripts/db/setup_postgres.sql
# 4. 執行 scripts/db/migration_seed_data.sql

# 方法2: 使用命令列
python scripts/db/sync_database.py
```

### 首次部署

```bash
# 1. 安裝依賴
python scripts/tools/install_requirements.py

# 2. 初始化資料庫（使用 pgAdmin）
# 執行 scripts/db/setup_postgres.sql
# 執行 scripts/db/migration_seed_data.sql

# 3. 初始化規則
python scripts/tools/init_default_rules.py

# 4. 啟動系統
python start_api.py
# 或使用 Docker
bash scripts/tools/deploy.sh
```

### 測試驗證

```bash
# 測試資料庫連線
python scripts/test/test_pg_connection.py

# 測試 API
python scripts/test/test_api.py

# 測試影像串流
python scripts/test/test_streams.py

# 測試人臉偵測
python scripts/test/test_face_detection.py
```

### 維護操作

```bash
# 修復規則資料
python scripts/tools/fix_rule_data.py

# 驗證資料庫完整性
python scripts/db/verify_pg_migration.py

# 重置規則（謹慎使用）
python scripts/tools/init_default_rules_force.py
```

## 資料庫配置

所有腳本使用 `.env` 檔案中的資料庫配置:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=motion-detector
POSTGRES_USER=face-motion
POSTGRES_PASSWORD=kkk12345
```

## 詳細文件

每個目錄都有詳細的 README.md 文件:

- **資料庫腳本**: `scripts/db/README.md`
- **工具腳本**: `scripts/tools/README.md`
- **測試腳本**: `scripts/test/README.md`

## 腳本分類索引

### 按功能分類

#### 資料庫管理
- `scripts/db/setup_postgres.sql` - 初始化
- `scripts/db/sync_database.py` - 同步
- `scripts/db/verify_pg_migration.py` - 驗證

#### 資料遷移
- `scripts/db/migrate_to_postgres.py` - MySQL 遷移
- `scripts/db/migrate_sqlite_to_postgres.py` - SQLite 遷移
- `scripts/db/migration_seed_data.sql` - 種子資料

#### 系統部署
- `scripts/tools/deploy.sh` - 自動部署
- `scripts/tools/install_requirements.py` - 安裝依賴

#### 規則管理
- `scripts/tools/init_default_rules.py` - 初始化
- `scripts/tools/init_default_rules_force.py` - 強制重置
- `scripts/tools/fix_rule_data.py` - 修復

#### 功能測試
- `scripts/test/test_api.py` - API 測試
- `scripts/test/test_postgres.py` - 資料庫測試
- `scripts/test/test_streams.py` - 串流測試
- `scripts/test/test_face_detection.py` - 偵測測試

## 執行順序建議

### 全新安裝
1. `scripts/tools/install_requirements.py` - 安裝依賴
2. `scripts/db/setup_postgres.sql` - 建立資料庫（pgAdmin）
3. `scripts/db/migration_seed_data.sql` - 匯入資料（pgAdmin）
4. `scripts/tools/init_default_rules.py` - 初始化規則
5. `scripts/test/test_pg_connection.py` - 驗證連線
6. 啟動系統

### 資料庫遷移
1. `scripts/db/check_sqlite_data.py` - 檢查來源資料
2. `scripts/db/setup_postgres.sql` - 準備目標資料庫
3. `scripts/db/migrate_sqlite_to_postgres.py` - 執行遷移
4. `scripts/db/verify_pg_migration.py` - 驗證結果

### 問題排查
1. `scripts/test/test_pg_connection.py` - 檢查連線
2. `scripts/db/verify_pg_migration.py` - 檢查資料
3. `scripts/tools/fix_rule_data.py` - 修復規則
4. `scripts/test/test_api.py` - 測試 API

## 注意事項

1. **執行權限**:
   ```bash
   chmod +x scripts/**/*.sh
   chmod +x scripts/**/*.py
   ```

2. **環境需求**:
   - Python 3.8+
   - PostgreSQL 12+
   - 正確設定的 .env 檔案

3. **備份建議**:
   執行破壞性操作前先備份:
   ```bash
   pg_dump -U face-motion motion-detector > backup_$(date +%Y%m%d).sql
   ```

4. **日誌位置**:
   - 應用程式日誌: `logs/`
   - 測試輸出: 終端機
   - 錯誤截圖: `screenshots/test_*`

## 常見問題

### Q: 腳本執行失敗怎麼辦？
A:
1. 檢查 Python 版本: `python --version`
2. 檢查依賴安裝: `pip list`
3. 檢查 .env 配置
4. 查看詳細錯誤訊息

### Q: 如何更新腳本？
A:
1. Git 拉取最新版本: `git pull`
2. 重新安裝依賴: `python scripts/tools/install_requirements.py`
3. 執行資料庫遷移（如有）

### Q: 測試失敗怎麼辦？
A:
1. 確認服務運行中
2. 檢查測試資料是否準備好
3. 查看測試腳本的 README
4. 檢查日誌檔案

## 貢獻指南

新增腳本時請:
1. 放在正確的目錄 (db/tools/test)
2. 遵循命名規範
3. 添加腳本說明到對應的 README.md
4. 更新本文件

## 聯絡支援

如有問題請:
1. 查看各目錄的 README.md
2. 檢查日誌檔案
3. 聯絡開發團隊
