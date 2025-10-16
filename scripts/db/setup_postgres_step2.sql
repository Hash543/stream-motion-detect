-- PostgreSQL 資料庫初始化腳本 - 步驟 2
-- 在 pgAdmin 中執行此腳本
-- 連接到: motion-detector 資料庫，使用 postgres 超級使用者

-- 授予 public schema 的所有權限
GRANT ALL PRIVILEGES ON SCHEMA public TO "face-motion";

-- 授予現有表的權限（如果有的話）
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "face-motion";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "face-motion";

-- 授予未來創建的表的預設權限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "face-motion";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "face-motion";

-- 完成！
-- 現在可以執行 migration_seed_data.sql 來匯入資料
