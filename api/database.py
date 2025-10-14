"""
Database Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 資料庫URL - 支援 SQLite 和 MySQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/monitoring.db")

# MySQL 連線設定 (如果設定了 MYSQL_DATABASE 環境變數)
MYSQL_HOST = os.getenv("DB_HOST", "localhost")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USERNAME", os.getenv("MYSQL_USER", "root"))
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))

# 如果有設定 MySQL 環境變數，優先使用 MySQL
if MYSQL_DATABASE and MYSQL_USER:
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}?charset=utf8mb4"
    print(f"Using MySQL database: {MYSQL_DATABASE}")
else:
    print(f"Using SQLite database: {DATABASE_URL}")

# 創建引擎
connect_args = {}
engine_kwargs = {
    "pool_size": 10,
    "max_overflow": 20,
    "echo": False  # 設為 True 可以看到 SQL 查詢
}

if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
elif "mysql" in DATABASE_URL:
    connect_args = {"connect_timeout": 60}
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
