"""
FastAPI Main Application
RTSP Stream Monitoring System API
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from datetime import datetime

from api.routers import persons, streams, rules, violations
from api.database import engine, Base

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建FastAPI應用
app = FastAPI(
    title="RTSP Stream Monitoring API",
    description="影像監控系統API - 提供人臉識別、影像來源管理、規則引擎等功能",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 創建資料庫表
Base.metadata.create_all(bind=engine)

# 註冊路由
app.include_router(persons.router, prefix="/api/persons", tags=["人臉識別管理"])
app.include_router(streams.router, prefix="/api/streams", tags=["影像來源管理"])
app.include_router(rules.router, prefix="/api/rules", tags=["規則引擎"])
app.include_router(violations.router, prefix="/api/violations", tags=["違規記錄"])


@app.get("/")
def read_root():
    """根路徑"""
    return {
        "message": "RTSP Stream Monitoring API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/api/health")
def health_check():
    """健康檢查"""
    try:
        # 檢查資料庫連接
        from api.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/api/info")
def get_system_info():
    """取得系統資訊"""
    return {
        "system": "RTSP Stream Monitoring System",
        "version": "1.0.0",
        "api_version": "1.0.0",
        "features": {
            "face_recognition": True,
            "helmet_detection": True,
            "drowsiness_detection": True,
            "rule_engine": True,
            "multi_stream": True
        },
        "endpoints": {
            "persons": "/api/persons",
            "streams": "/api/streams",
            "rules": "/api/rules",
            "violations": "/api/violations"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全域例外處理"""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
