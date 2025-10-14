"""
Database Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 資料庫URL - 支援 SQLite、PostgreSQL 和 MySQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/monitoring.db")

# PostgreSQL 連線設定 (最高優先級)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost"))
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", os.getenv("POSTGRES_DB"))
POSTGRES_USER = os.getenv("POSTGRES_USER", os.getenv("POSTGRES_USERNAME"))
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# MySQL 連線設定
MYSQL_HOST = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USERNAME", os.getenv("MYSQL_USER", "root"))
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))

# 優先順序: PostgreSQL > MySQL > SQLite
if POSTGRES_DATABASE and POSTGRES_USER and POSTGRES_PASSWORD:
    DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
    print(f"Using PostgreSQL database: {POSTGRES_DATABASE} at {POSTGRES_HOST}:{POSTGRES_PORT}")
elif MYSQL_DATABASE and MYSQL_USER:
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}?charset=utf8mb4"
    print(f"Using MySQL database: {MYSQL_DATABASE}")
else:
    print(f"Using SQLite database: {DATABASE_URL}")

# 創建引擎
connect_args = {}
engine_kwargs = {
    "echo": False  # 設為 True 可以看到 SQL 查詢
}

if "sqlite" in DATABASE_URL:
    # SQLite 不支援連接池參數
    connect_args = {"check_same_thread": False}
elif "postgresql" in DATABASE_URL:
    # PostgreSQL 連接池設定
    connect_args = {"connect_timeout": 10}
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 3600
elif "mysql" in DATABASE_URL:
    # MySQL 連接池設定
    connect_args = {"connect_timeout": 60}
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 3600

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
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
