# PostgreSQL 設定指南

## 快速設定步驟

### 方法 1: 使用 psql 命令列（推薦）

1. **以 postgres 超級使用者登入**
```bash
psql -U postgres
```

2. **執行以下 SQL 命令**
```sql
-- 創建資料庫
CREATE DATABASE "motion-detector";

-- 創建使用者並設定密碼
CREATE USER "face-motion" WITH PASSWORD 'kkk12345';

-- 授予權限
GRANT ALL PRIVILEGES ON DATABASE "motion-detector" TO "face-motion";

-- 連接到新資料庫
\c motion-detector

-- 授予 schema 權限
GRANT ALL PRIVILEGES ON SCHEMA public TO "face-motion";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "face-motion";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "face-motion";

-- 退出
\q
```

### 方法 2: 使用 SQL 腳本

```bash
psql -U postgres -f setup_postgres.sql
```

### 方法 3: 使用 pgAdmin

1. 打開 pgAdmin
2. 右鍵點擊 Databases → Create → Database
   - Database: `motion-detector`
   - Owner: postgres
3. 右鍵點擊 Login/Group Roles → Create → Login/Group Role
   - Name: `face-motion`
   - Password: `kkk12345`
   - Privileges: Can login
4. 右鍵點擊 motion-detector → Properties → Security
   - 添加 `face-motion` 並授予 ALL 權限

## 驗證設定

執行測試腳本：
```bash
python test_postgres.py
```

如果連線成功，會顯示：
```
✓ 連線成功！
PostgreSQL 版本: ...
```

## 資料遷移

### 從 SQLite 遷移到 PostgreSQL

```bash
# 遷移資料
python migrate_to_postgres.py

# 強制重新遷移（會清空現有資料）
python migrate_to_postgres.py --force
```

## 連線資訊

- **Host**: localhost
- **Port**: 5432
- **Database**: motion-detector
- **User**: face-motion
- **Password**: kkk12345

## 環境變數設定

在 `.env` 檔案中已配置：
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=motion-detector
POSTGRES_USER=face-motion
POSTGRES_PASSWORD=kkk12345
```

## 常見問題

### 1. 密碼驗證失敗

確認使用者和密碼是否正確：
```sql
-- 重設密碼
ALTER USER "face-motion" WITH PASSWORD 'kkk12345';
```

### 2. 資料庫不存在

```sql
CREATE DATABASE "motion-detector";
```

### 3. 權限不足

```sql
\c motion-detector
GRANT ALL PRIVILEGES ON SCHEMA public TO "face-motion";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "face-motion";
```

### 4. pg_hba.conf 配置問題

編輯 PostgreSQL 的 `pg_hba.conf` 檔案，確保有以下設定：
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
```

修改後重啟 PostgreSQL：
```bash
# Windows
net stop postgresql-x64-15
net start postgresql-x64-15

# Linux
sudo systemctl restart postgresql
```

## 啟動應用程式

配置完成後，重啟應用程式即可使用 PostgreSQL：

```bash
python monitoring_system.py
```

應該會看到：
```
Using PostgreSQL database: motion-detector at localhost:5432
```
