"""
Create PostgreSQL tables using SQLAlchemy models
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
os.environ["POSTGRES_DATABASE"] = "motion-detector"
os.environ["POSTGRES_USER"] = "face-motion"
os.environ["POSTGRES_PASSWORD"] = "kkk12345"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"

from api.database import engine, Base, DATABASE_URL
from api.models import (
    Person, StreamSource, DetectionRule, Violation, SystemLog,
    User, Role, Organization, Positions, AlertEvent, AlertEventAssignUser,
    GPS808, Permission, RolePermission, InspectProperty, RelInspectProperty,
    RelInspectPropertyOrganization, SysParams
)

def create_tables():
    """Create all tables in PostgreSQL"""
    try:
        print("=" * 60)
        print("Creating PostgreSQL Tables")
        print("=" * 60)
        print(f"Database URL: {DATABASE_URL}")
        print()

        # Create all tables
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)

        print("\n[OK] All tables created successfully!")

        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"\n[INFO] Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  - {table}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to create tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
