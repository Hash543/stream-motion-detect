"""
Database Configuration - PostgreSQL Only
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# PostgreSQL 連線設定（必需）
POSTGRES_HOST = os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost"))
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", os.getenv("POSTGRES_DB", "motion-detector"))
POSTGRES_USER = os.getenv("POSTGRES_USER", os.getenv("POSTGRES_USERNAME", "face-motion"))
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# 檢查必要的環境變數
if not POSTGRES_DATABASE or not POSTGRES_USER:
    raise ValueError(
        "PostgreSQL configuration is required. "
        "Please set POSTGRES_DATABASE and POSTGRES_USER environment variables."
    )

# 建立 PostgreSQL 連線 URL
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
print(f"Using PostgreSQL database: {POSTGRES_DATABASE} at {POSTGRES_HOST}:{POSTGRES_PORT}")

# 創建引擎 - 僅支援 PostgreSQL
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 10},
    pool_size=5,  # 減少連線池大小
    max_overflow=10,  # 減少最大溢出連線
    pool_pre_ping=True,  # 連線前先 ping，確保連線有效
    pool_recycle=1800,  # 30分鐘回收連線（改為較短時間）
    pool_timeout=30,  # 等待連線的超時時間
    echo=False  # 設為 True 可以看到 SQL 查詢
)

# 創建Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 創建Base類
Base = declarative_base()


def get_db():
    """取得資料庫Session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 發生錯誤時回滾
        db.rollback()
        raise
    finally:
        # 確保 session 正確關閉
        db.close()


def dispose_engine():
    """關閉所有資料庫連線池"""
    try:
        engine.dispose()
        print("Database connection pool disposed")
    except Exception as e:
        print(f"Error disposing database: {e}")
