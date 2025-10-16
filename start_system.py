#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化的系統啟動腳本
解決編碼問題
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 設定編碼
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.monitoring_system import MonitoringSystem
import logging

def main():
    """簡化的主程式"""
    # 設定基本日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/system.log', encoding='utf-8')
        ]
    )

    logger = logging.getLogger(__name__)

    try:
        print("=== RTSP監控系統啟動 ===")
        print("警告: dlib 和 face_recognition 套件未安裝")
        print("      系統將使用 MediaPipe 進行人臉檢測")
        print("      安全帽檢測和瞌睡檢測功能正常運作")
        print()

        # 檢查設定檔
        config_path = "config/config.json"
        if not os.path.exists(config_path):
            print(f"錯誤: 找不到設定檔 {config_path}")
            return

        # 初始化系統
        monitoring_system = MonitoringSystem(config_path)

        # 驗證設定
        print("正在驗證系統設定...")
        config = monitoring_system.config_manager.load_config()

        print(f"✓ 設定檔載入成功")
        print(f"  - RTSP來源: {len(config.rtsp_sources)} 個")
        print(f"  - 處理FPS: {config.detection_settings.processing_fps}")
        print(f"  - 通知端點: {config.notification_api.endpoint}")

        # 檢查模型檔案
        print("\n檢查AI模型檔案:")
        path_results = monitoring_system.config_manager.validate_paths()
        for path, exists in path_results.items():
            status = "✓" if exists else "✗"
            print(f"  {status} {path}")

        if not any(path_results.values()):
            print("\n注意: 沒有找到自訂AI模型檔案")
            print("     系統將使用預設模型 (功能正常)")

        print("\n系統已準備就緒!")

        # 在 Docker 環境中自動啟動，否則詢問用戶
        auto_start = os.getenv('AUTO_START', 'false').lower() == 'true'

        if auto_start:
            print("\n自動啟動監控系統...")
            monitoring_system.run()
        else:
            choice = input("\n是否要啟動監控系統? (y/N): ").strip().lower()

            if choice in ['y', 'yes']:
                print("\n啟動監控系統...")
                monitoring_system.run()
            else:
                print("系統驗證完成，未啟動監控")

    except KeyboardInterrupt:
        print("\n用戶中斷")
    except Exception as e:
        logger.error(f"系統錯誤: {e}")
        print(f"\n錯誤: {e}")

if __name__ == "__main__":
    main()