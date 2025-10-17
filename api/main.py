"""
FastAPI Main Application
RTSP Stream Monitoring System API
"""

from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from datetime import datetime

from api.routers import persons, streams, rules, violations, auth, alert_event, role, positions, organization, equipment_assets, dashboard, dropdown, gps808, users, websocket
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

# Face Motion 整合路由
app.include_router(auth.router, tags=["認證管理"])
app.include_router(users.router, tags=["使用者管理"])
app.include_router(alert_event.router, tags=["警報事件管理"])
app.include_router(role.router, prefix="/api/role", tags=["角色管理"])
app.include_router(positions.router, prefix="/api/positions", tags=["職位管理"])
app.include_router(organization.router, prefix="/api/organization", tags=["組織管理"])
app.include_router(equipment_assets.router, prefix="/api/equipmentAssets", tags=["設備資產管理"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["儀表板"])
app.include_router(dropdown.router, prefix="/api/dropdown", tags=["下拉選單"])
app.include_router(gps808.router, prefix="/api/gps808", tags=["GPS808 位置追蹤"])
app.include_router(websocket.router, tags=["WebSocket 即時通知"])


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
            "violations": "/api/violations",
            "auth": "/api/auth",
            "alertEvent": "/api/alertEvent"
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
