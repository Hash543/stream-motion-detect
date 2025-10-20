"""
Start API Service with Monitoring System
啟動 API 服務並整合監控系統
"""

from dotenv import load_dotenv
load_dotenv()

import sys
import os
import logging

# 設定編碼
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全域監控系統實例
monitoring_system = None


def initialize_monitoring_system():
    """初始化監控系統"""
    global monitoring_system

    try:
        logger.info("Initializing monitoring system...")
        from src.monitoring_system import MonitoringSystem

        monitoring_system = MonitoringSystem(
            config_path="config/config.json",
            stream_config_path="streamSource.json"
        )

        if not monitoring_system.initialize():
            logger.error("Failed to initialize monitoring system")
            return False

        if not monitoring_system.start():
            logger.error("Failed to start monitoring system")
            return False

        logger.info("Monitoring system started successfully")

        # 從資料庫載入串流（僅 RTSP）
        load_database_streams()

        # 將監控系統注入到 API routers
        from api.routers import streams
        streams.set_monitoring_system(monitoring_system)
        logger.info("Monitoring system injected into API routers")

        return True

    except Exception as e:
        logger.error(f"Error initializing monitoring system: {e}", exc_info=True)
        return False


def load_database_streams():
    """從資料庫載入啟用的 RTSP 串流"""
    global monitoring_system

    if not monitoring_system:
        return

    try:
        from api.database import SessionLocal
        from api.models import StreamSource

        db = SessionLocal()
        try:
            db_streams = db.query(StreamSource).filter(
                StreamSource.enabled == True,
                StreamSource.stream_type == "RTSP"
            ).all()

            logger.info(f"Found {len(db_streams)} enabled RTSP streams in database")

            for db_stream in db_streams:
                stream_id = db_stream.stream_id

                # 檢查是否已載入
                if stream_id in monitoring_system.rtsp_manager.streams:
                    logger.info(f"Stream {stream_id} already loaded")
                    continue

                # 添加串流
                monitoring_system.rtsp_manager.add_stream(
                    camera_id=stream_id,
                    rtsp_url=db_stream.url,
                    location=db_stream.location or "Unknown"
                )
                monitoring_system.rtsp_manager.set_frame_callback(
                    stream_id,
                    monitoring_system._process_frame
                )

                # 啟動串流
                if monitoring_system.rtsp_manager.start_stream(stream_id):
                    logger.info(f"Started stream: {stream_id}")
                    # Camera records are managed via API, no need for database_manager
                else:
                    logger.error(f"Failed to start stream: {stream_id}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error loading database streams: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("RTSP Stream Monitoring API Server")
    print("=" * 60)
    print("\nAPI Documentation: http://localhost:8282/api/docs")
    print("Health Check: http://localhost:8282/api/health")
    print("Video Streaming: http://localhost:8282/api/streams/{stream_id}/video")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)

    # 初始化監控系統
    if not initialize_monitoring_system():
        logger.error("Failed to initialize monitoring system, starting API only...")

    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8282,
            reload=False,  # 關閉 reload 避免監控系統重複初始化
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        if monitoring_system:
            monitoring_system.stop()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        if monitoring_system:
            monitoring_system.stop()
