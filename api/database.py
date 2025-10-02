"""
Database Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 資料庫URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/monitoring.db")

# 創建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
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
