# psql 命令列工具設定指南

## 快速安裝

### 方法 1: 使用自動化腳本（推薦）

**步驟**:
1. 右鍵點擊 `setup_psql_path.bat`
2. 選擇「以系統管理員身分執行」
3. 按任意鍵確認
4. 等待完成訊息
5. **重新開啟**命令提示字元或 PowerShell

**驗證**:
```bash
psql --version
```

應該顯示類似: `psql (PostgreSQL) 17.x`

### 方法 2: 使用 PowerShell 腳本

**步驟**:
1. 以管理員身份開啟 PowerShell
2. 執行:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\setup_psql_path.ps1
   ```
3. 按 Y 確認
4. **重新開啟** PowerShell

### 方法 3: 手動設定

**步驟**:
1. 按 `Win + R`，輸入 `sysdm.cpl`，按 Enter
2. 點擊「進階」標籤
3. 點擊「環境變數」
4. 在「系統變數」區塊中，找到「Path」，點擊「編輯」
5. 點擊「新增」
6. 輸入: `C:\Program Files\PostgreSQL\17\bin`
7. 點擊「確定」關閉所有視窗
8. **重新開啟**命令提示字元

## 驗證安裝

開啟新的命令提示字元，執行:

```bash
# 檢查版本
psql --version

# 測試連線（會提示輸入密碼）
psql -U postgres -h localhost

# 使用專案資料庫連線
psql -U face-motion -d motion-detector -h localhost
```

## 常用 psql 命令

### 連線到資料庫
```bash
# 連接到 postgres 資料庫
psql -U postgres

# 連接到指定資料庫
psql -U face-motion -d motion-detector

# 指定主機和埠
psql -U postgres -h localhost -p 5432
```

### 執行 SQL 檔案
```bash
# 執行初始化腳本
psql -U postgres -f scripts/db/setup_postgres.sql

# 執行資料遷移
psql -U face-motion -d motion-detector -f scripts/db/migration_seed_data.sql
```

### psql 互動模式命令

連線成功後，在 psql 提示符下可以使用:

```sql
-- 列出所有資料庫
\l

-- 連接到指定資料庫
\c motion-detector

-- 列出所有表
\dt

-- 查看表結構
\d table_name

-- 列出所有使用者
\du

-- 執行 SQL 檔案
\i /path/to/file.sql

-- 顯示查詢執行時間
\timing

-- 退出
\q
```

## 環境變數設定（可選）

為了避免每次都輸入密碼，可以設定環境變數:

### Windows (臨時)
```cmd
set PGPASSWORD=your_password
psql -U postgres
```

### Windows (永久)
1. 在使用者目錄建立 `pgpass.conf` 檔案
2. 位置: `C:\Users\你的使用者名稱\AppData\Roaming\postgresql\pgpass.conf`
3. 內容格式:
   ```
   localhost:5432:*:postgres:your_password
   localhost:5432:motion-detector:face-motion:kkk12345
   ```

### 使用 .pgpass 檔案
```bash
# 建立目錄
mkdir %APPDATA%\postgresql

# 建立檔案（使用記事本編輯）
notepad %APPDATA%\postgresql\pgpass.conf
```

內容範例:
```
# hostname:port:database:username:password
localhost:5432:*:postgres:admin
localhost:5432:motion-detector:face-motion:kkk12345
```

## 常見問題

### Q: psql 命令找不到
A:
1. 確認已重新開啟命令提示字元
2. 檢查 PATH 設定: `echo %PATH%`
3. 確認包含 `C:\Program Files\PostgreSQL\17\bin`

### Q: 連線失敗
A:
1. 檢查 PostgreSQL 服務是否運行: `tasklist | findstr postgres`
2. 檢查連線參數（使用者名稱、密碼、主機）
3. 檢查 `pg_hba.conf` 設定

### Q: 密碼認證失敗
A:
1. 確認使用者密碼正確
2. 檢查 PostgreSQL 的 `pg_hba.conf` 認證方式
3. 使用 pgAdmin 重設密碼

### Q: 執行腳本時出現編碼錯誤
A:
```bash
# 使用 UTF-8 編碼
psql -U postgres --set client_encoding=UTF8 -f script.sql
```

## 進階用法

### 匯出資料
```bash
# 匯出整個資料庫
pg_dump -U face-motion motion-detector > backup.sql

# 僅匯出結構
pg_dump -U face-motion -s motion-detector > schema.sql

# 僅匯出資料
pg_dump -U face-motion -a motion-detector > data.sql
```

### 匯入資料
```bash
# 從備份還原
psql -U face-motion -d motion-detector < backup.sql
```

### 執行單一查詢
```bash
# 不進入互動模式，直接執行查詢
psql -U face-motion -d motion-detector -c "SELECT COUNT(*) FROM users;"
```

## 相關文件

- PostgreSQL 官方文件: https://www.postgresql.org/docs/
- psql 命令參考: https://www.postgresql.org/docs/current/app-psql.html
