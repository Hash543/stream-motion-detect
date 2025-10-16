#!/usr/bin/env python3
"""
PostgreSQL 資料庫同步腳本
執行資料庫初始化和資料遷移
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def load_env():
    """載入 .env 檔案"""
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def connect_postgres(dbname='postgres'):
    """連接到 PostgreSQL"""
    load_env()

    return psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'localhost'),
        port=os.environ.get('POSTGRES_PORT', '5432'),
        database=dbname,
        user=os.environ.get('POSTGRES_USER', 'face-motion'),
        password=os.environ.get('POSTGRES_PASSWORD', 'kkk12345')
    )

def execute_sql_file(conn, filename):
    """執行 SQL 檔案"""
    print(f"\n{'='*50}")
    print(f"執行 {filename}...")
    print('='*50)

    with open(filename, 'r', encoding='utf-8') as f:
        sql = f.read()

    cursor = conn.cursor()

    # 分割成單獨的語句（簡單版本）
    # 跳過 psql 專用命令
    statements = []
    current = []

    for line in sql.split('\n'):
        # 跳過 psql 命令
        if line.strip().startswith('\\'):
            continue

        current.append(line)

        # 簡單的分號偵測（不考慮字串中的分號）
        if line.strip().endswith(';'):
            statements.append('\n'.join(current))
            current = []

    if current:
        statements.append('\n'.join(current))

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt or stmt.startswith('--'):
            continue

        try:
            cursor.execute(stmt)
            conn.commit()

            # 如果有結果，顯示
            if cursor.description:
                results = cursor.fetchall()
                if results:
                    for row in results:
                        print(' '.join(str(x) for x in row))
        except Exception as e:
            # 某些錯誤可以忽略（如資料庫已存在）
            error_msg = str(e)
            if 'already exists' in error_msg:
                print(f"⚠ 警告: {error_msg}")
                conn.rollback()
            else:
                print(f"✗ 錯誤: {error_msg}")
                print(f"語句: {stmt[:100]}...")
                conn.rollback()

    cursor.close()

def setup_database():
    """設定資料庫"""
    print("="*50)
    print("PostgreSQL 資料庫同步工具")
    print("="*50)

    # 步驟1: 連接到 postgres 資料庫以建立目標資料庫
    print("\n步驟 1: 連接到 PostgreSQL...")
    try:
        # 使用 postgres 超級使用者連接
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=os.environ.get('POSTGRES_PORT', '5432'),
            database='postgres',
            user='postgres',
            password=os.environ.get('POSTGRES_ADMIN_PASSWORD', 'admin')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print("✓ 已連接到 PostgreSQL (postgres 資料庫)")
    except Exception as e:
        print(f"✗ 無法連接到 PostgreSQL: {e}")
        print("\n請確認:")
        print("1. PostgreSQL 服務正在運行")
        print("2. 連線參數正確 (POSTGRES_HOST, POSTGRES_PORT)")
        print("3. postgres 使用者密碼正確")
        sys.exit(1)

    # 步驟2: 建立資料庫和使用者
    print("\n步驟 2: 建立資料庫和使用者...")
    cursor = conn.cursor()

    db_name = os.environ.get('POSTGRES_DATABASE', 'motion-detector')
    db_user = os.environ.get('POSTGRES_USER', 'face-motion')
    db_password = os.environ.get('POSTGRES_PASSWORD', 'kkk12345')

    try:
        # 建立使用者
        cursor.execute(f"SELECT 1 FROM pg_user WHERE usename = '{db_user}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE USER \"{db_user}\" WITH PASSWORD '{db_password}'")
            print(f"✓ 已建立使用者: {db_user}")
        else:
            cursor.execute(f"ALTER USER \"{db_user}\" WITH PASSWORD '{db_password}'")
            print(f"✓ 使用者已存在，已更新密碼: {db_user}")

        # 建立資料庫
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE \"{db_name}\" OWNER \"{db_user}\"")
            print(f"✓ 已建立資料庫: {db_name}")
        else:
            print(f"✓ 資料庫已存在: {db_name}")

        # 授予權限
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE \"{db_name}\" TO \"{db_user}\"")
        print(f"✓ 已授予資料庫權限")

    except Exception as e:
        print(f"✗ 建立資料庫/使用者時發生錯誤: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

    cursor.close()
    conn.close()

    # 步驟3: 連接到目標資料庫並授予 schema 權限
    print(f"\n步驟 3: 設定 {db_name} 資料庫權限...")
    try:
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=os.environ.get('POSTGRES_PORT', '5432'),
            database='postgres',
            user='postgres',
            password=os.environ.get('POSTGRES_ADMIN_PASSWORD', 'admin')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()

        # 切換到目標資料庫執行權限設定
        cursor.close()
        conn.close()

        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=os.environ.get('POSTGRES_PORT', '5432'),
            database=db_name,
            user='postgres',
            password=os.environ.get('POSTGRES_ADMIN_PASSWORD', 'admin')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO \"{db_user}\"")
        cursor.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{db_user}\"")
        cursor.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"{db_user}\"")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"{db_user}\"")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \"{db_user}\"")

        print("✓ 已設定 schema 權限")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"✗ 設定權限時發生錯誤: {e}")

    # 步驟4: 執行遷移腳本
    print(f"\n步驟 4: 執行資料遷移...")
    try:
        conn = connect_postgres(db_name)
        execute_sql_file(conn, 'migration_seed_data.sql')
        conn.close()
        print("✓ 資料遷移完成")
    except Exception as e:
        print(f"✗ 執行遷移腳本時發生錯誤: {e}")
        sys.exit(1)

    # 步驟5: 驗證
    print(f"\n步驟 5: 驗證資料...")
    try:
        conn = connect_postgres(db_name)
        cursor = conn.cursor()

        tables = ['organization', 'role', 'user', 'permission', 'role_permission']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            print(f"  ✓ {table}: {count} 筆記錄")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"✗ 驗證時發生錯誤: {e}")

    print("\n" + "="*50)
    print("資料庫同步完成！")
    print("="*50)
    print(f"資料庫: {db_name}")
    print(f"使用者: {db_user}")
    print(f"主機: {os.environ.get('POSTGRES_HOST', 'localhost')}")
    print(f"連接埠: {os.environ.get('POSTGRES_PORT', '5432')}")
    print("="*50)

if __name__ == '__main__':
    load_env()
    setup_database()
