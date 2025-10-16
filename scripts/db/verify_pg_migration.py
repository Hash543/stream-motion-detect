"""
Verify PostgreSQL migration
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
os.environ["POSTGRES_DATABASE"] = "motion-detector"
os.environ["POSTGRES_USER"] = "face-motion"
os.environ["POSTGRES_PASSWORD"] = "kkk12345"

from sqlalchemy import create_engine, text, inspect
import sqlite3

PG_DATABASE_URL = "postgresql+psycopg2://face-motion:kkk12345@localhost:5432/motion-detector"
SQLITE_DB = "data/monitoring.db"

def verify_migration():
    """Verify the data migration from SQLite to PostgreSQL"""
    print("=" * 60)
    print("Migration Verification")
    print("=" * 60)
    print()

    # Connect to PostgreSQL
    pg_engine = create_engine(PG_DATABASE_URL)

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    # Tables to verify
    tables = [
        ('stream_sources', 'stream_id'),
        ('detection_rules', 'rule_id'),
        ('violations', 'violation_id'),
    ]

    print("[INFO] Comparing record counts:\n")

    total_sqlite = 0
    total_postgres = 0

    for table_name, id_column in tables:
        # Count SQLite records
        if table_name == 'stream_sources':
            # Also count cameras table
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            sqlite_count_streams = sqlite_cursor.fetchone()[0]
            sqlite_cursor.execute("SELECT COUNT(*) FROM cameras")
            sqlite_count_cameras = sqlite_cursor.fetchone()[0]
            sqlite_count = sqlite_count_streams + sqlite_count_cameras
        else:
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            sqlite_count = sqlite_cursor.fetchone()[0]

        # Count PostgreSQL records
        with pg_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            pg_count = result.scalar()

        total_sqlite += sqlite_count
        total_postgres += pg_count

        match_symbol = "[OK]" if pg_count >= sqlite_count else "[WARNING]"
        print(f"{match_symbol} {table_name}:")
        print(f"  SQLite:     {sqlite_count:,} records")
        print(f"  PostgreSQL: {pg_count:,} records")

        if pg_count < sqlite_count:
            print(f"  Missing:    {sqlite_count - pg_count:,} records")
        print()

    # Show summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total SQLite records:     {total_sqlite:,}")
    print(f"Total PostgreSQL records: {total_postgres:,}")

    if total_postgres >= total_sqlite:
        print("\n[OK] Migration verified successfully!")
        print("All data has been migrated to PostgreSQL.")
    else:
        print(f"\n[WARNING] Migration incomplete!")
        print(f"Missing {total_sqlite - total_postgres:,} records.")

    # List all tables in PostgreSQL
    print("\n" + "=" * 60)
    print("PostgreSQL Database Tables")
    print("=" * 60)

    inspector = inspect(pg_engine)
    all_tables = inspector.get_table_names()

    print(f"\nFound {len(all_tables)} tables in PostgreSQL:")
    for table in sorted(all_tables):
        with pg_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
        print(f"  - {table:40s} {count:,} records")

    sqlite_conn.close()
    return True

if __name__ == "__main__":
    try:
        verify_migration()
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
