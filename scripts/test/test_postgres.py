"""
PostgreSQL 連線測試腳本
"""

import sys
import psycopg2
from psycopg2 import sql

def test_postgres_connection():
    """測試 PostgreSQL 連線"""

    # 連線參數
    params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'motion-detector',
        'user': 'face-motion',
        'password': 'kkk12345'
    }

    print("="*80)
    print("PostgreSQL 連線測試")
    print("="*80)
    print(f"Host: {params['host']}")
    print(f"Port: {params['port']}")
    print(f"Database: {params['database']}")
    print(f"User: {params['user']}")
    print(f"Password: {'*' * len(params['password'])}")
    print()

    try:
        print("嘗試連線...")
        conn = psycopg2.connect(**params)
        print("✓ 連線成功！")

        # 測試查詢
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"\nPostgreSQL 版本:")
        print(version[0])

        # 查詢資料庫資訊
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"\n現有的表 ({len(tables)} 個):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\n目前沒有任何表")

        cursor.close()
        conn.close()

        print("\n" + "="*80)
        print("測試完成！")
        print("="*80)
        return True

    except psycopg2.OperationalError as e:
        print(f"❌ 連線失敗: {e}")
        print("\n可能的原因:")
        print("1. PostgreSQL 服務未啟動")
        print("2. 連線參數錯誤（host, port, database, user, password）")
        print("3. PostgreSQL 的 pg_hba.conf 設定不允許此連線")
        print("4. 使用者權限不足")
        print("\n建議檢查:")
        print("- 執行: psql -h localhost -U face-motion -d motion-detector")
        print("- 或使用 pgAdmin 測試連線")
        return False
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        return False


if __name__ == "__main__":
    test_postgres_connection()
