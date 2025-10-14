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
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
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
    finally:
        db.close()
