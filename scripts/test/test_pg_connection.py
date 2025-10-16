import psycopg2
from psycopg2 import OperationalError
import sys

# 設定輸出編碼為 UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def test_postgres_connection():
    """測試 PostgreSQL 資料庫連線"""
    try:
        # 嘗試連線到資料庫
        connection = psycopg2.connect(
            database='motion-detector',
            user='face-motion',
            password='kkk12345',
            host='localhost',  # 預設使用 localhost
            port='5432'        # PostgreSQL 預設埠號
        )

        # 取得游標
        cursor = connection.cursor()

        # 執行簡單的查詢來驗證連線
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()

        print("[OK] Database connection successful!")
        print(f"[OK] PostgreSQL version: {db_version[0]}")

        # 檢查資料庫名稱
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()
        print(f"[OK] Current database: {current_db[0]}")

        # 檢查當前使用者
        cursor.execute("SELECT current_user;")
        current_user = cursor.fetchone()
        print(f"[OK] Current user: {current_user[0]}")

        # 列出資料庫中的資料表
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"\n[OK] Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\n[INFO] No tables found in database")

        # 關閉連線
        cursor.close()
        connection.close()
        print("\n[OK] Connection closed successfully")

        return True

    except OperationalError as e:
        print("[ERROR] Database connection failed!")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print("[ERROR] Unexpected error occurred!")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("開始測試 PostgreSQL 連線...")
    print("=" * 50)
    test_postgres_connection()
