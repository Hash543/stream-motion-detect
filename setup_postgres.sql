-- PostgreSQL 資料庫初始化腳本
-- 請使用 postgres 超級使用者執行此腳本

-- 1. 創建資料庫（如果不存在）
-- 注意: 無法在事務中創建資料庫，需要分開執行
SELECT 'CREATE DATABASE "motion-detector"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'motion-detector')\gexec

-- 2. 創建使用者（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'face-motion') THEN
        CREATE USER "face-motion" WITH PASSWORD 'kkk12345';
    END IF;
END
$$;

-- 3. 修改使用者密碼（確保密碼正確）
ALTER USER "face-motion" WITH PASSWORD 'kkk12345';

-- 4. 授予資料庫權限
GRANT ALL PRIVILEGES ON DATABASE "motion-detector" TO "face-motion";

-- 5. 連接到目標資料庫並授予 schema 權限
\c motion-detector

-- 授予 public schema 的所有權限
GRANT ALL PRIVILEGES ON SCHEMA public TO "face-motion";

-- 授予現有表的權限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "face-motion";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "face-motion";

-- 授予未來創建的表的預設權限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "face-motion";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "face-motion";

-- 完成
\echo '========================================='
\echo 'PostgreSQL 資料庫設定完成！'
\echo '========================================='
\echo '資料庫: motion-detector'
\echo '使用者: face-motion'
\echo '密碼: kkk12345'
\echo '========================================='
