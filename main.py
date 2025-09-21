#!/usr/bin/env python3
"""
RTSP影像監控系統主程式
主要功能：
- RTSP串流影像處理
- 安全帽檢測
- 瞌睡檢測
- 人臉識別
- 違規截圖與通知
"""

import argparse
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.monitoring_system import MonitoringSystem
import logging

def setup_basic_logging():
    """Setup basic logging before system initialization"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="RTSP影像監控系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python main.py                                    # 使用預設設定檔啟動
  python main.py --config custom_config.json       # 使用自訂設定檔
  python main.py --status                          # 顯示系統狀態(需要系統正在運行)

設定檔範例請參考: config/config.json
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/config.json",
        help="設定檔路徑 (預設: config/config.json)"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="顯示系統狀態並退出"
    )

    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="測試通知API連接並退出"
    )

    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="驗證設定檔格式並退出"
    )

    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="設定日誌等級 (預設: INFO)"
    )

    args = parser.parse_args()

    # Setup basic logging
    setup_basic_logging()
    logger = logging.getLogger(__name__)

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Check if config file exists
        if not os.path.exists(args.config):
            logger.error(f"設定檔不存在: {args.config}")
            logger.info("請確認設定檔路徑，或參考 config/config.json 建立設定檔")
            sys.exit(1)

        # Initialize monitoring system
        monitoring_system = MonitoringSystem(args.config)

        # Handle different modes
        if args.validate_config:
            # Validate configuration
            logger.info("驗證設定檔...")
            try:
                config = monitoring_system.config_manager.load_config()
                logger.info("✓ 設定檔格式正確")

                # Validate paths
                path_results = monitoring_system.config_manager.validate_paths()
                for path, exists in path_results.items():
                    status = "✓" if exists else "✗"
                    logger.info(f"{status} 模型檔案: {path}")

                logger.info("設定檔驗證完成")
                sys.exit(0)

            except Exception as e:
                logger.error(f"✗ 設定檔格式錯誤: {e}")
                sys.exit(1)

        elif args.test_connection:
            # Test notification API connection
            logger.info("測試通知API連接...")
            try:
                config = monitoring_system.config_manager.load_config()
                from src.managers.notification_sender import NotificationSender

                sender = NotificationSender(
                    endpoint=config.notification_api.endpoint,
                    timeout=config.notification_api.timeout
                )

                if sender.test_connection():
                    logger.info("✓ 通知API連接測試成功")
                    sys.exit(0)
                else:
                    logger.error("✗ 通知API連接測試失敗")
                    sys.exit(1)

            except Exception as e:
                logger.error(f"✗ 通知API測試錯誤: {e}")
                sys.exit(1)

        elif args.status:
            # Show system status (if running)
            logger.info("取得系統狀態...")
            # This would need to be implemented with a proper status endpoint
            # For now, just show that the config is loadable
            try:
                config = monitoring_system.config_manager.load_config()
                logger.info("系統設定檔載入成功")
                logger.info(f"RTSP來源數量: {len(config.rtsp_sources)}")
                logger.info(f"處理FPS: {config.detection_settings.processing_fps}")
                logger.info(f"通知API: {config.notification_api.endpoint}")
                sys.exit(0)
            except Exception as e:
                logger.error(f"無法載入系統設定: {e}")
                sys.exit(1)

        else:
            # Normal operation - start monitoring system
            logger.info("=== RTSP影像監控系統啟動 ===")
            logger.info(f"設定檔: {args.config}")
            logger.info(f"日誌等級: {args.log_level}")

            # Run the monitoring system
            monitoring_system.run()

    except KeyboardInterrupt:
        logger.info("使用者中斷程式執行")
        sys.exit(0)
    except Exception as e:
        logger.error(f"系統執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()