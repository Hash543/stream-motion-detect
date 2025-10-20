"""
啟動 API 伺服器並整合監控系統
提供 MJPEG 串流功能
"""

from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

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

        # 從資料庫載入並啟動額外的串流來源
        from api.database import SessionLocal
        from api.models import StreamSource
        from src.managers.database_manager import CameraRecord

        db = SessionLocal()
        try:
            db_streams = db.query(StreamSource).filter(
                StreamSource.enabled == True
            ).all()
            logger.info(f"Found {len(db_streams)} enabled streams in database")

            for db_stream in db_streams:
                stream_id = db_stream.stream_id
                stream_type = db_stream.stream_type

                # 檢查是否已經載入
                if stream_type == "RTSP" and stream_id in monitoring_system.rtsp_manager.streams:
                    logger.info(f"Stream {stream_id} already loaded from config")
                    continue
                elif stream_type != "RTSP" and stream_id in monitoring_system.stream_manager.streams:
                    logger.info(f"Stream {stream_id} already loaded from config")
                    continue

                # 根據類型載入串流
                if stream_type == "RTSP":
                    # 使用 RTSP manager 處理 RTSP 串流
                    monitoring_system.rtsp_manager.add_stream(
                        camera_id=stream_id,
                        rtsp_url=db_stream.url,
                        location=db_stream.location or "Unknown"
                    )
                    monitoring_system.rtsp_manager.set_frame_callback(
                        stream_id,
                        monitoring_system._process_frame
                    )

                    if monitoring_system.rtsp_manager.start_stream(stream_id):
                        logger.info(f"Started database stream: {stream_id} (RTSP)")
                        camera_record = CameraRecord(
                            camera_id=stream_id,
                            location=db_stream.location or "Unknown",
                            rtsp_url=db_stream.url
                        )
                        monitoring_system.database_manager.add_camera(camera_record)
                    else:
                        logger.error(f"Failed to start RTSP stream: {stream_id}")

                else:
                    # 使用 universal stream manager 處理其他類型的串流
                    # 準備配置
                    config = db_stream.config or {}

                    # WEBCAM 特殊處理：將 url 轉換為 device_index
                    if stream_type == "WEBCAM":
                        try:
                            config['device_index'] = int(db_stream.url) if db_stream.url else 0
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid webcam device index: {db_stream.url}, using 0")
                            config['device_index'] = 0

                    stream_config = {
                        'id': stream_id,  # UniversalStreamManager 需要 'id' 欄位
                        'stream_id': stream_id,
                        'name': db_stream.name,
                        'type': stream_type,
                        'url': db_stream.url if stream_type != "WEBCAM" else None,
                        'location': db_stream.location or "Unknown",
                        'enabled': True,
                        'config': config
                    }

                    if monitoring_system.stream_manager.add_stream(stream_config):
                        monitoring_system.stream_manager.set_frame_callback(
                            stream_id,
                            monitoring_system._process_frame
                        )

                        if monitoring_system.stream_manager.start_stream(stream_id):
                            logger.info(f"Started database stream: {stream_id} ({stream_type})")
                            # Add camera record if database_manager exists
                            if hasattr(monitoring_system, 'database_manager') and monitoring_system.database_manager:
                                camera_record = CameraRecord(
                                    camera_id=stream_id,
                                    location=db_stream.location or "Unknown",
                                    rtsp_url=db_stream.url if stream_type == "RTSP" else None
                                )
                                monitoring_system.database_manager.add_camera(camera_record)
                        else:
                            logger.error(f"Failed to start {stream_type} stream: {stream_id}")
                    else:
                        logger.error(f"Failed to add {stream_type} stream: {stream_id}")

        except Exception as e:
            logger.error(f"Error loading database streams: {e}", exc_info=True)
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
