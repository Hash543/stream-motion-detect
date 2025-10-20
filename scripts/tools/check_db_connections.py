"""
檢查 PostgreSQL 資料庫連線狀態
用於監控資料庫連線是否正常釋放
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# 載入 .env
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

def check_connections():
    """檢查資料庫連線狀態"""
    try:
        # 連接資料庫
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DATABASE", "motion-detector"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        cur = conn.cursor()

        # 查詢連線狀態
        cur.execute("""
            SELECT
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active,
                count(*) FILTER (WHERE state = 'idle') as idle,
                count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
            FROM pg_stat_activity
            WHERE datname = %s
        """, (os.getenv("POSTGRES_DATABASE", "motion-detector"),))

        result = cur.fetchone()

        print("=" * 50)
        print("PostgreSQL 連線狀態")
        print("=" * 50)
        print(f"總連線數: {result[0]}")
        print(f"  - Active (執行中): {result[1]}")
        print(f"  - Idle (閒置): {result[2]}")
        print(f"  - Idle in Transaction (交易中閒置): {result[3]}")
        print("=" * 50)

        # 如果有異常的 idle in transaction 連線，顯示詳細資訊
        if result[3] > 0:
            print("\n⚠️  警告: 發現閒置的交易連線")
            print("-" * 50)

            cur.execute("""
                SELECT
                    pid,
                    usename,
                    application_name,
                    state,
                    state_change,
                    NOW() - state_change as duration,
                    query
                FROM pg_stat_activity
                WHERE datname = %s
                  AND state = 'idle in transaction'
                ORDER BY state_change
            """, (os.getenv("POSTGRES_DATABASE", "motion-detector"),))

            idle_conns = cur.fetchall()
            for conn_info in idle_conns:
                print(f"PID: {conn_info[0]}")
                print(f"User: {conn_info[1]}")
                print(f"App: {conn_info[2]}")
                print(f"State: {conn_info[3]}")
                print(f"Duration: {conn_info[5]}")
                print(f"Last Query: {conn_info[6][:100]}...")
                print("-" * 50)

        # 顯示所有連線詳情（可選）
        if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
            print("\n詳細連線資訊:")
            print("-" * 50)

            cur.execute("""
                SELECT
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    state,
                    NOW() - state_change as duration
                FROM pg_stat_activity
                WHERE datname = %s
                ORDER BY state_change
            """, (os.getenv("POSTGRES_DATABASE", "motion-detector"),))

            all_conns = cur.fetchall()
            for i, conn_info in enumerate(all_conns, 1):
                print(f"{i}. PID: {conn_info[0]} | User: {conn_info[1]} | "
                      f"App: {conn_info[2]} | State: {conn_info[4]} | "
                      f"Duration: {conn_info[5]}")

        cur.close()
        conn.close()

        # 建議
        print("\n💡 建議:")
        if result[0] == 0:
            print("  ✓ 目前沒有活動連線")
        elif result[0] <= 5:
            print("  ✓ 連線數量正常")
        elif result[0] <= 10:
            print("  ⚠  連線數量偏高，請注意監控")
        else:
            print("  ❌ 連線數量過高，可能存在連線洩漏")

        if result[3] > 0:
            print("  ❌ 存在未完成的交易，可能導致資料庫鎖定")
            print("     請使用 --kill-idle 參數終止這些連線")

        return result[0]

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return -1


def kill_idle_transactions():
    """終止長時間閒置的交易連線"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DATABASE", "motion-detector"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        cur = conn.cursor()

        # 查詢要終止的連線
        cur.execute("""
            SELECT pid
            FROM pg_stat_activity
            WHERE datname = %s
              AND state = 'idle in transaction'
              AND state_change < NOW() - INTERVAL '5 minutes'
              AND pid <> pg_backend_pid()
        """, (os.getenv("POSTGRES_DATABASE", "motion-detector"),))

        pids = cur.fetchall()

        if not pids:
            print("✓ 沒有需要終止的閒置交易連線")
            return

        print(f"準備終止 {len(pids)} 個閒置交易連線...")

        # 終止連線
        for pid in pids:
            cur.execute("SELECT pg_terminate_backend(%s)", (pid[0],))
            result = cur.fetchone()[0]
            if result:
                print(f"  ✓ 已終止 PID: {pid[0]}")
            else:
                print(f"  ❌ 無法終止 PID: {pid[0]}")

        conn.commit()
        cur.close()
        conn.close()

        print("完成！")

    except Exception as e:
        print(f"❌ 錯誤: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--kill-idle":
        print("=" * 50)
        print("終止閒置交易連線")
        print("=" * 50)
        kill_idle_transactions()
    else:
        check_connections()

        if len(sys.argv) > 1 and sys.argv[1] == "--help":
            print("\n使用方式:")
            print("  python check_db_connections.py              # 檢查連線狀態")
            print("  python check_db_connections.py --verbose    # 顯示詳細資訊")
            print("  python check_db_connections.py --kill-idle  # 終止閒置交易")
