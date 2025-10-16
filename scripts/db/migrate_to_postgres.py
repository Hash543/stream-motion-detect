"""
資料遷移腳本: SQLite -> PostgreSQL
Migrate data from SQLite to PostgreSQL
"""

import sys
import os
import io

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from api.database import Base
from api.models import (
    Person, StreamSource, DetectionRule, Violation, SystemLog,
    User, Role, Organization, Positions, AlertEvent, AlertEventAssignUser,
    GPS808, Permission, RolePermission, InspectProperty, RelInspectProperty,
    RelInspectPropertyOrganization, SysParams
)
from datetime import datetime


def migrate_data():
    """遷移資料從 SQLite 到 PostgreSQL"""

    print("="*80)
    print("資料遷移: SQLite -> PostgreSQL")
    print("="*80)

    # SQLite 連線
    sqlite_url = "sqlite:///./data/monitoring.db"
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SqliteSession = sessionmaker(bind=sqlite_engine)

    # PostgreSQL 連線
    postgres_url = "postgresql+psycopg2://face-motion:kkk12345@localhost:5432/motion-detector"
    postgres_engine = create_engine(
        postgres_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )
    PostgresSession = sessionmaker(bind=postgres_engine)

    # 檢查 SQLite 資料庫是否存在
    if not os.path.exists("./data/monitoring.db"):
        print("\n❌ SQLite 資料庫不存在: ./data/monitoring.db")
        print("跳過遷移，直接初始化 PostgreSQL 資料庫...")
        Base.metadata.create_all(bind=postgres_engine)
        print("✓ PostgreSQL 資料庫表已創建")
        return

    try:
        # 測試 PostgreSQL 連線
        print("\n正在測試 PostgreSQL 連線...")
        postgres_engine.connect()
        print("✓ PostgreSQL 連線成功")

        # 創建 PostgreSQL 表結構
        print("\n正在創建 PostgreSQL 表結構...")
        Base.metadata.create_all(bind=postgres_engine)
        print("✓ 表結構創建完成")

        # 檢查 SQLite 資料庫表
        print("\n檢查 SQLite 資料庫...")
        inspector = inspect(sqlite_engine)
        tables = inspector.get_table_names()
        print(f"找到 {len(tables)} 個表: {', '.join(tables)}")

        sqlite_db = SqliteSession()
        postgres_db = PostgresSession()

        # 定義遷移順序（考慮外鍵依賴）
        migration_models = [
            # 基礎表（無外鍵依賴）
            ("persons", Person),
            ("stream_sources", StreamSource),
            ("detection_rules", DetectionRule),
            ("system_logs", SystemLog),
            ("organization", Organization),
            ("role", Role),
            ("positions", Positions),
            ("permission", Permission),

            # 有外鍵依賴的表
            ("violations", Violation),
            ("user", User),
            ("role_permission", RolePermission),
            ("alert_event", AlertEvent),
            ("alert_event_assign_user", AlertEventAssignUser),
            ("gps808", GPS808),
            ("inspect_property", InspectProperty),
            ("rel_inspect_property", RelInspectProperty),
            ("rel_inspect_property_organization", RelInspectPropertyOrganization),
            ("sys_params", SysParams),
        ]

        total_migrated = 0

        print("\n" + "="*80)
        print("開始遷移資料...")
        print("="*80)

        for table_name, model_class in migration_models:
            if table_name not in tables:
                print(f"\n⊘ 跳過 {table_name} (表不存在)")
                continue

            try:
                # 查詢 SQLite 資料
                records = sqlite_db.query(model_class).all()

                if not records:
                    print(f"\n⊘ {table_name}: 無資料")
                    continue

                print(f"\n正在遷移 {table_name}...")
                print(f"  找到 {len(records)} 筆記錄")

                # 批次插入到 PostgreSQL
                migrated = 0
                for record in records:
                    # 將 SQLite 記錄轉換為字典
                    record_dict = {}
                    for column in model_class.__table__.columns:
                        value = getattr(record, column.name)
                        record_dict[column.name] = value

                    # 創建新記錄
                    new_record = model_class(**record_dict)
                    postgres_db.add(new_record)
                    migrated += 1

                    # 每 100 筆提交一次
                    if migrated % 100 == 0:
                        postgres_db.commit()
                        print(f"  已遷移 {migrated}/{len(records)} 筆...")

                # 提交剩餘記錄
                postgres_db.commit()
                total_migrated += migrated
                print(f"  ✓ 完成遷移 {migrated} 筆記錄")

            except Exception as e:
                print(f"  ❌ 遷移 {table_name} 時發生錯誤: {e}")
                postgres_db.rollback()
                continue

        print("\n" + "="*80)
        print(f"遷移完成！共遷移 {total_migrated} 筆記錄")
        print("="*80)

        # 顯示各表記錄數
        print("\nPostgreSQL 資料庫統計:")
        print("-"*80)
        for table_name, model_class in migration_models:
            try:
                count = postgres_db.query(model_class).count()
                if count > 0:
                    print(f"  {table_name:40} {count:>6} 筆")
            except:
                pass
        print("-"*80)

        sqlite_db.close()
        postgres_db.close()

    except Exception as e:
        print(f"\n❌ 遷移過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_connection():
    """測試 PostgreSQL 連線"""
    try:
        postgres_url = "postgresql+psycopg2://face-motion:kkk12345@localhost:5432/motion-detector"
        engine = create_engine(postgres_url)
        connection = engine.connect()
        print("✓ PostgreSQL 連線測試成功")
        connection.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL 連線測試失敗: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='遷移資料從 SQLite 到 PostgreSQL')
    parser.add_argument('--test', action='store_true', help='只測試連線，不遷移資料')
    parser.add_argument('--force', action='store_true', help='強制重新遷移（會清空 PostgreSQL 資料）')

    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.force:
        print("警告: 即將清空 PostgreSQL 資料庫並重新遷移！")
        confirm = input("確定要繼續嗎? (yes/no): ")
        if confirm.lower() == 'yes':
            # 清空表
            postgres_url = "postgresql+psycopg2://face-motion:kkk12345@localhost:5432/motion-detector"
            postgres_engine = create_engine(postgres_url)
            Base.metadata.drop_all(bind=postgres_engine)
            print("已清空所有表")
            migrate_data()
        else:
            print("取消操作")
    else:
        migrate_data()
