-- PostgreSQL 資料庫初始化腳本 - 步驟 1
-- 在 pgAdmin 中執行此腳本
-- 連接到: postgres 資料庫，使用 postgres 超級使用者

-- 1. 創建使用者（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'face-motion') THEN
        CREATE USER "face-motion" WITH PASSWORD 'kkk12345';
        RAISE NOTICE '已建立使用者: face-motion';
    ELSE
        RAISE NOTICE '使用者已存在: face-motion';
    END IF;
END
$$;

-- 2. 修改使用者密碼（確保密碼正確）
ALTER USER "face-motion" WITH PASSWORD 'kkk12345';

-- 3. 創建資料庫（如果不存在）
-- 注意: 如果資料庫已存在會報錯，這是正常的
CREATE DATABASE "motion-detector" OWNER "face-motion";

-- 4. 授予資料庫權限
GRANT ALL PRIVILEGES ON DATABASE "motion-detector" TO "face-motion";

-- 完成步驟 1
-- 請切換到 motion-detector 資料庫，執行 setup_postgres_step2.sql
