# PostgreSQL 資料庫連線問題修正

## 問題描述

**症狀**: 程式停止後，pgAdmin 無法瀏覽資料表的 rows（資料庫鎖定或連線未釋放）

**原因**:
1. 資料庫連線池設定過大（pool_size=10, max_overflow=20），佔用過多連線
2. 健康檢查端點 (`/api/health`) 沒有正確關閉連線
3. 應用程式關閉時沒有釋放連線池
4. `get_db()` 函數缺少錯誤處理和回滾機制

## 修正內容

### 1. 優化連線池設定 (`api/database.py`)

**修改前**:
```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 10},
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

**修改後**:
```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 10},
    pool_size=5,  # 減少連線池大小
    max_overflow=10,  # 減少最大溢出連線
    pool_pre_ping=True,  # 連線前先 ping，確保連線有效
    pool_recycle=1800,  # 30分鐘回收連線（改為較短時間）
    pool_timeout=30,  # 等待連線的超時時間
    echo=False
)
```

**改善效果**:
- 減少同時佔用的資料庫連線數量
- 縮短連線回收時間，避免長時間佔用
- 增加連線超時設定，避免無限等待

### 2. 改善 get_db() 錯誤處理 (`api/database.py`)

**修改前**:
```python
def get_db():
    """取得資料庫Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**修改後**:
```python
def get_db():
    """取得資料庫Session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 發生錯誤時回滾
        db.rollback()
        raise
    finally:
        # 確保 session 正確關閉
        db.close()
```

**改善效果**:
- 錯誤發生時自動回滾交易，避免留下未完成的交易
- 確保無論是否發生錯誤，連線都會被正確關閉

### 3. 新增連線池釋放函數 (`api/database.py`)

**新增**:
```python
def dispose_engine():
    """關閉所有資料庫連線池"""
    try:
        engine.dispose()
        print("Database connection pool disposed")
    except Exception as e:
        print(f"Error disposing database: {e}")
```

**用途**: 應用程式關閉時釋放所有連線池連線

### 4. 修正健康檢查端點 (`api/main.py`)

**修改前**:
```python
@app.get("/api/health")
def health_check():
    try:
        from api.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()  # 可能在異常時未執行

        return {"status": "healthy", ...}
    except Exception as e:
        ...
```

**修改後**:
```python
@app.get("/api/health")
def health_check():
    from api.database import SessionLocal
    from sqlalchemy import text

    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return {"status": "healthy", ...}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, ...)
    finally:
        # 確保連線被關閉
        if db:
            db.close()
```

**改善效果**:
- 使用 `finally` 確保連線一定會被關閉
- 修正 SQLAlchemy 2.0 的語法（使用 `text()`）

### 5. 新增應用程式生命週期管理 (`api/main.py`)

**新增**:
```python
@app.on_event("startup")
async def startup_event():
    """應用程式啟動時執行"""
    logger.info("Application starting up...")
    logger.info(f"Database engine pool size: {engine.pool.size()}")


@app.on_event("shutdown")
async def shutdown_event():
    """應用程式關閉時執行"""
    logger.info("Application shutting down...")
    # 關閉所有資料庫連線
    dispose_engine()
    logger.info("Database connections disposed")
```

**改善效果**:
- 應用程式正常關閉時釋放所有連線
- 即使異常終止，也會觸發 shutdown 事件

## 測試建議

### 1. 測試正常啟動/關閉

```bash
# 啟動 API
python start_api.py

# 觀察日誌應顯示:
# "Application starting up..."
# "Database engine pool size: ..."

# 按 Ctrl+C 停止

# 觀察日誌應顯示:
# "Application shutting down..."
# "Database connection pool disposed"
# "Database connections disposed"
```

### 2. 測試 pgAdmin 連線

```bash
# 1. 啟動 API
python start_api.py

# 2. 在 pgAdmin 中查看資料表（應該可以正常查看）

# 3. 停止 API (Ctrl+C)

# 4. 在 pgAdmin 中重新整理並查看資料表（應該可以正常查看）
```

### 3. 檢查資料庫連線狀態

在 PostgreSQL 中執行以下查詢:

```sql
-- 查看當前所有連線
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query,
    state_change
FROM pg_stat_activity
WHERE datname = 'motion-detector';

-- 查看連線數量
SELECT
    datname,
    count(*) as connections
FROM pg_stat_activity
WHERE datname = 'motion-detector'
GROUP BY datname;
```

**預期結果**:
- API 運行時: 應該看到 0-5 個活動連線
- API 停止後: 應該看到 0 個連線（或很快降至 0）

### 4. 壓力測試

```bash
# 使用 Apache Bench 或類似工具測試
ab -n 100 -c 10 http://localhost:8282/api/health

# 測試完成後檢查:
# 1. API 是否仍正常運作
# 2. 資料庫連線數量是否正常
# 3. pgAdmin 是否可以正常查看資料
```

## 如果問題仍然存在

### 手動終止殭屍連線

如果仍有未關閉的連線，可以使用以下 SQL 手動終止:

```sql
-- 查看所有 idle 狀態的連線
SELECT
    pid,
    usename,
    application_name,
    state,
    state_change
FROM pg_stat_activity
WHERE datname = 'motion-detector'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes';

-- 終止長時間 idle 的連線
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'motion-detector'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes'
  AND pid <> pg_backend_pid();
```

### 調整 PostgreSQL 設定

編輯 `postgresql.conf`:

```ini
# 設定連線超時（單位: 毫秒）
tcp_keepalives_idle = 60        # 60秒後開始發送 keepalive
tcp_keepalives_interval = 10    # 每10秒發送一次
tcp_keepalives_count = 3        # 3次失敗後斷開連線

# 限制最大連線數
max_connections = 100

# 設定 statement_timeout（單位: 毫秒）
statement_timeout = 30000  # 30秒後終止長時間執行的查詢
```

重啟 PostgreSQL 使設定生效:
```bash
# Windows
net stop postgresql-x64-14
net start postgresql-x64-14
```

## 監控建議

### 定期檢查連線狀態

建立監控腳本 `scripts/tools/check_db_connections.py`:

```python
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    database=os.getenv("POSTGRES_DATABASE", "motion-detector"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)

cur = conn.cursor()
cur.execute("""
    SELECT
        count(*) as total_connections,
        count(*) FILTER (WHERE state = 'active') as active,
        count(*) FILTER (WHERE state = 'idle') as idle
    FROM pg_stat_activity
    WHERE datname = %s
""", (os.getenv("POSTGRES_DATABASE", "motion-detector"),))

result = cur.fetchone()
print(f"Total Connections: {result[0]}")
print(f"Active: {result[1]}")
print(f"Idle: {result[2]}")

cur.close()
conn.close()
```

執行:
```bash
python scripts/tools/check_db_connections.py
```

## 相關檔案

- `api/database.py`: 資料庫連線設定和連線池管理
- `api/main.py`: FastAPI 應用程式主檔案，包含生命週期事件
- `.env`: 環境變數設定

## 注意事項

1. **連線池大小**: 根據實際負載調整 `pool_size` 和 `max_overflow`
2. **回收時間**: `pool_recycle` 應小於 PostgreSQL 的 `idle_in_transaction_session_timeout`
3. **超時設定**: 確保 `pool_timeout` 合理，避免請求等待過久
4. **生產環境**: 建議使用 PgBouncer 等連線池管理工具

## 參考連結

- [SQLAlchemy Engine Configuration](https://docs.sqlalchemy.org/en/14/core/engines.html)
- [PostgreSQL Connection Pooling](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
