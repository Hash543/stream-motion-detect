"""
Initialize API Service
初始化API服務 - 建立資料庫表和必要目錄
"""

import os
import sys

# 設定編碼
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_directories():
    """建立必要的目錄"""
    directories = [
        "data",
        "screenshots",
        "logs",
        "models",
        "config"
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"[OK] Created directory: {directory}")
        else:
            print(f"[EXIST] Directory exists: {directory}")


def init_database():
    """初始化資料庫"""
    from api.database import engine, Base
    from api.models import Person, StreamSource, DetectionRule, Violation, SystemLog

    print("\n[DB] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully")


def main():
    print("=== Initializing RTSP Stream Monitoring API Service ===\n")

    # 建立目錄
    print("[INIT] Creating directories...")
    create_directories()

    # 初始化資料庫
    try:
        init_database()
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n[SUCCESS] API Service initialized successfully!")
    print("\nNext steps:")
    print("1. Run: python start_api.py")
    print("2. Visit: http://localhost:8000/api/docs")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
