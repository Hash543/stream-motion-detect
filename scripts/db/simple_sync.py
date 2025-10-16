# -*- coding: utf-8 -*-
"""
簡化版資料庫同步腳本
假設資料庫和使用者已經建立，僅執行資料遷移
"""

import os
import sys
import psycopg2

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

def execute_sql_file(conn, filename):
    """執行 SQL 檔案"""
    print(f"\n{'='*50}")
    print(f"執行 {filename}...")
    print('='*50)

    with open(filename, 'r', encoding='utf-8') as f:
        sql = f.read()

    cursor = conn.cursor()

    try:
        # 直接執行整個檔案（PostgreSQL 支援）
        cursor.execute(sql)
        conn.commit()
        print("執行成功！")

    except Exception as e:
        error_msg = str(e)
        print(f"執行時發生錯誤: {error_msg}")
        conn.rollback()

    cursor.close()

def main():
    load_env()

    print("="*50)
    print("PostgreSQL 資料遷移工具")
    print("="*50)

    db_name = os.environ.get('POSTGRES_DATABASE', 'motion-detector')
    db_user = os.environ.get('POSTGRES_USER', 'face-motion')
    db_password = os.environ.get('POSTGRES_PASSWORD', 'kkk12345')
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5432')

    print(f"\n連接資訊:")
    print(f"  主機: {db_host}:{db_port}")
    print(f"  資料庫: {db_name}")
    print(f"  使用者: {db_user}")

    try:
        print(f"\n連接到資料庫...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        print("連接成功！")

        # 執行遷移腳本
        execute_sql_file(conn, 'scripts/db/migration_seed_data.sql')

        # 驗證資料
        print(f"\n{'='*50}")
        print("驗證資料...")
        print('='*50)

        cursor = conn.cursor()
        tables = ['organization', 'role', 'user', 'permission', 'role_permission']

        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} 筆記錄")

        cursor.close()
        conn.close()

        print(f"\n{'='*50}")
        print("資料遷移完成！")
        print('='*50)

    except Exception as e:
        print(f"\n錯誤: {e}")
        print("\n請確認:")
        print("1. PostgreSQL 服務正在運行")
        print("2. 資料庫 motion-detector 已建立")
        print("3. 使用者 face-motion 已建立且有權限")
        print("4. .env 中的連線參數正確")
        sys.exit(1)

if __name__ == '__main__':
    main()
