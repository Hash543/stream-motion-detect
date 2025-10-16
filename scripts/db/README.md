# 資料庫腳本 (Database Scripts)

本目錄包含所有資料庫相關的腳本和工具。

## SQL 腳本

### `setup_postgres.sql`
**用途**: PostgreSQL 資料庫初始化腳本（psql 命令列版本）

**功能**:
- 建立資料庫 `motion-detector`
- 建立使用者 `face-motion`
- 設定使用者密碼
- 授予所有必要權限

**執行方式** (使用 postgres 超級使用者):
```bash
# 使用 psql 命令列
psql -U postgres -f setup_postgres.sql
```

**注意**: 此檔案包含 psql 專用命令（`\gexec`, `\c`, `\echo`），無法在 pgAdmin 中直接執行。

### `setup_postgres_step1.sql` + `setup_postgres_step2.sql`
**用途**: PostgreSQL 資料庫初始化腳本（pgAdmin 版本）

**功能**: 與 `setup_postgres.sql` 相同，但分成兩個步驟，可在 pgAdmin 中執行

**執行方式** (使用 pgAdmin):
```
步驟 1: 連接到 postgres 資料庫
1. 在 pgAdmin 中連接到 PostgreSQL 伺服器 (使用 postgres 使用者)
2. 右鍵點擊 postgres 資料庫 → Query Tool
3. 開啟並執行 setup_postgres_step1.sql
   - 建立使用者 face-motion
   - 建立資料庫 motion-detector

步驟 2: 連接到 motion-detector 資料庫
1. 在左側樹狀目錄展開 Databases
2. 右鍵點擊 motion-detector → Query Tool
3. 開啟並執行 setup_postgres_step2.sql
   - 授予 schema 權限
```

### `migration_seed_data.sql`
**用途**: 資料遷移和種子資料

**功能**:
- 插入組織資料 (organization)
- 插入角色資料 (role)
- 插入使用者資料 (user)
- 插入權限資料 (permission)
- 設定角色權限對應 (role_permission)

**執行方式** (連接到 motion-detector 資料庫):
```bash
# 方法1: 使用 psql
psql -U face-motion -d motion-detector -f migration_seed_data.sql

# 方法2: 使用 pgAdmin
# 1. 連接到 motion-detector 資料庫
# 2. 開啟 Query Tool
# 3. 載入此檔案並執行
```

## Python 腳本

### `sync_database.py`
**用途**: 自動化資料庫同步工具

**功能**:
- 自動建立資料庫和使用者
- 執行資料遷移
- 驗證資料完整性

**執行方式**:
```bash
python scripts/db/sync_database.py
```

**注意**: 需要在 .env 中設定 POSTGRES_ADMIN_PASSWORD (postgres 使用者密碼)

### `migrate_to_postgres.py`
**用途**: MySQL 到 PostgreSQL 遷移工具

**功能**:
- 從 MySQL 遷移資料到 PostgreSQL
- 自動轉換資料類型
- 保留資料完整性

**執行方式**:
```bash
python scripts/db/migrate_to_postgres.py
```

### `migrate_sqlite_to_postgres.py`
**用途**: SQLite 到 PostgreSQL 遷移工具

**功能**:
- 從 SQLite 遷移資料到 PostgreSQL
- 自動建立表結構
- 資料轉換和驗證

**執行方式**:
```bash
python scripts/db/migrate_sqlite_to_postgres.py
```

### `create_pg_tables.py`
**用途**: 建立 PostgreSQL 表結構

**功能**:
- 建立所有必要的資料表
- 設定外鍵約束
- 建立索引

**執行方式**:
```bash
python scripts/db/create_pg_tables.py
```

### `verify_pg_migration.py`
**用途**: 驗證資料庫遷移結果

**功能**:
- 檢查表結構
- 驗證資料完整性
- 顯示統計資訊

**執行方式**:
```bash
python scripts/db/verify_pg_migration.py
```

### `check_sqlite_data.py`
**用途**: 檢查 SQLite 資料庫內容

**功能**:
- 列出所有表
- 顯示記錄數量
- 查看資料樣本

**執行方式**:
```bash
python scripts/db/check_sqlite_data.py
```

## 資料庫配置

資料庫連線參數設定在專案根目錄的 `.env` 檔案中:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=motion-detector
POSTGRES_USER=face-motion
POSTGRES_PASSWORD=kkk12345
```

## 完整資料庫初始化流程

### 方法 A: 使用 pgAdmin（推薦）

1. **確認 PostgreSQL 服務運行中**
   ```bash
   # Windows
   tasklist | findstr postgres
   ```

2. **步驟 1: 建立資料庫和使用者**
   - 開啟 pgAdmin
   - 連接到 PostgreSQL 伺服器（使用 postgres 使用者）
   - 右鍵點擊 **postgres** 資料庫 → Query Tool
   - 開啟檔案：`scripts/db/setup_postgres_step1.sql`
   - 點擊執行 (F5)

3. **步驟 2: 設定權限**
   - 在 pgAdmin 左側展開 Databases
   - 右鍵點擊 **motion-detector** 資料庫 → Query Tool
   - 開啟檔案：`scripts/db/setup_postgres_step2.sql`
   - 點擊執行 (F5)

4. **步驟 3: 匯入資料**
   - 在同一個 Query Tool（連接到 motion-detector）
   - 開啟檔案：`scripts/db/migration_seed_data.sql`
   - 點擊執行 (F5)

5. **驗證資料**
   ```sql
   -- 在 Query Tool 中執行
   SELECT 'organization' as table_name, COUNT(*) FROM organization
   UNION ALL SELECT 'role', COUNT(*) FROM role
   UNION ALL SELECT 'user', COUNT(*) FROM "user"
   UNION ALL SELECT 'permission', COUNT(*) FROM permission
   UNION ALL SELECT 'role_permission', COUNT(*) FROM role_permission;
   ```

### 方法 B: 使用 psql 命令列

1. **確認 PostgreSQL 服務運行中**
   ```bash
   tasklist | findstr postgres
   ```

2. **執行初始化腳本**
   ```bash
   psql -U postgres -f scripts/db/setup_postgres.sql
   ```

3. **執行資料遷移**
   ```bash
   psql -U face-motion -d motion-detector -f scripts/db/migration_seed_data.sql
   ```

4. **驗證資料**
   ```bash
   python scripts/db/verify_pg_migration.py
   ```

## 預設使用者

遷移後會建立以下預設使用者:

| 使用者名稱 | 密碼 (Base64) | 角色 |
|----------|--------------|------|
| 管理者 | 566h55CG6ICFMDAxQWRtaW4xMjNf | 管理員 |
| superuser | c3VwZXJ1c2VyMTIzNDU2Nw== | 管理員 |

**注意**: 密碼需要透過 Base64 解碼後才能使用。

## 常見問題

### Q: 執行 SQL 時出現權限錯誤
A: 確認使用正確的使用者執行:
- `setup_postgres.sql` 需要使用 `postgres` 超級使用者
- `migration_seed_data.sql` 需要先執行 setup 後才能執行

### Q: 連線失敗
A: 檢查以下項目:
1. PostgreSQL 服務是否運行
2. .env 中的連線參數是否正確
3. 防火牆設定
4. PostgreSQL 的 pg_hba.conf 權限設定

### Q: 資料遷移失敗
A:
1. 檢查來源資料庫是否可連線
2. 確認目標資料庫已建立
3. 查看錯誤訊息並根據提示修正
