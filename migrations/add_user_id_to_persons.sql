-- Migration: Add user_id column to persons table
-- Date: 2025-10-17
-- Description: 添加 user_id 欄位到 persons 表，用於關聯使用者

-- 添加 user_id 欄位 (PostgreSQL 使用 COMMENT ON 語法)
ALTER TABLE persons
ADD COLUMN user_id INTEGER NULL;

-- 添加欄位註釋
COMMENT ON COLUMN persons.user_id IS '關聯的使用者ID';

-- 添加外鍵約束 (PostgreSQL 中表名需要用引號，因為 "user" 是關鍵字)
ALTER TABLE persons
ADD CONSTRAINT fk_persons_user_id
FOREIGN KEY (user_id) REFERENCES "user"(id)
ON DELETE SET NULL
ON UPDATE CASCADE;

-- 添加索引以提升查詢性能
CREATE INDEX idx_persons_user_id ON persons(user_id);

-- 查詢驗證 (PostgreSQL 使用不同的系統表)
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'persons' AND column_name = 'user_id';
