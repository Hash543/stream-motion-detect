"""
啟動 API 伺服器並整合監控系統
提供 MJPEG 串流功能
"""

import uvicorn
import logging
import sys
from pathlib import Path

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主程式"""
    try:
        logger.info("Starting RTSP Monitoring System with API and Streaming...")

        # 初始化監控系統
        from src.monitoring_system import MonitoringSystem
        monitoring_system = MonitoringSystem(
            config_path="config/config.json",
            stream_config_path="streamSource.json"
        )

        # 初始化並啟動監控系統
        if not monitoring_system.initialize():
            logger.error("Failed to initialize monitoring system")
            sys.exit(1)

        if not monitoring_system.start():
            logger.error("Failed to start monitoring system")
            sys.exit(1)

        logger.info("Monitoring system started successfully")

        # 從資料庫載入並啟動額外的串流來源（只載入 RTSP）
        from api.database import SessionLocal
        from api.models import StreamSource
        from src.managers.database_manager import CameraRecord

        db = SessionLocal()
        try:
            db_streams = db.query(StreamSource).filter(
                StreamSource.enabled == True,
                StreamSource.stream_type == "RTSP"  # 只載入 RTSP
            ).all()
            logger.info(f"Found {len(db_streams)} enabled RTSP streams in database")

            for db_stream in db_streams:
                stream_id = db_stream.stream_id

                # 檢查是否已經在 RTSP manager 中
                if stream_id in monitoring_system.rtsp_manager.streams:
                    logger.info(f"Stream {stream_id} already loaded from config")
                    continue

                # 添加到 RTSP manager
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
                    logger.info(f"Started database stream: {stream_id} (RTSP)")

                    # 添加到資料庫
                    camera_record = CameraRecord(
                        camera_id=stream_id,
                        location=db_stream.location or "Unknown",
                        rtsp_url=db_stream.url
                    )
                    monitoring_system.database_manager.add_camera(camera_record)
                else:
                    logger.error(f"Failed to start stream: {stream_id}")

        except Exception as e:
            logger.error(f"Error loading database streams: {e}")
        finally:
            db.close()

        # 將監控系統實例注入到 streams router
        from api.routers import streams
        streams.set_monitoring_system(monitoring_system)
        logger.info("Monitoring system injected into API routers")

        # 啟動 FastAPI 伺服器
        logger.info("Starting FastAPI server on http://0.0.0.0:8282")
        logger.info("API Docs available at http://localhost:8282/api/docs")
        logger.info("Video streaming endpoint: http://localhost:8282/api/streams/{stream_id}/video")

        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8282,
            reload=False,  # 關閉 reload 以避免監控系統重複初始化
            log_level="info"
        )

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        if 'monitoring_system' in locals():
            monitoring_system.stop()
    except Exception as e:
        logger.error(f"Error starting system: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
