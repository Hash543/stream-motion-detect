#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試所有串流格式的腳本
"""

import sys
import os
import time
import logging
from pathlib import Path

# 設定編碼
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.managers.universal_stream_manager import UniversalStreamManager

# 設定基本日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_stream_manager():
    """測試串流管理器"""
    print("=== 測試通用串流管理器 ===")

    stream_manager = UniversalStreamManager("streamSource.json")

    print("\n1. 載入串流設定...")
    if stream_manager.load_config():
        print(f"✓ 成功載入設定")
        print(f"  - 全域設定: {stream_manager.global_settings}")
        print(f"  - 串流數量: {len(stream_manager.stream_configs)}")

        for config in stream_manager.stream_configs:
            enabled = "OK" if config.get('enabled', True) else "SKIP"
            print(f"  {enabled} {config['id']} ({config['type']}) - {config['name']}")
    else:
        print("✗ 載入設定失敗")
        return False

    print("\n2. 初始化串流...")
    results = stream_manager.initialize_streams()

    success_count = 0
    for stream_id, success in results.items():
        status = "OK" if success else "FAIL"
        print(f"  {status} {stream_id}")
        if success:
            success_count += 1

    print(f"\n初始化結果: {success_count}/{len(results)} 成功")

    print("\n3. 取得支援的串流類型...")
    supported_types = stream_manager.get_supported_stream_types()
    for stream_type, description in supported_types.items():
        print(f"  • {stream_type}: {description}")

    print("\n4. 測試啟動串流...")
    if stream_manager.streams:
        start_results = stream_manager.start_all_streams()

        for stream_id, success in start_results.items():
            status = "OK" if success else "FAIL"
            print(f"  {status} 啟動 {stream_id}")

        print("\n5. 等待串流數據...")
        time.sleep(3)

        print("\n6. 檢查串流狀態...")
        all_status = stream_manager.get_all_streams_status()

        for stream_id, status in all_status.items():
            running = "運行中" if status['is_running'] else "已停止"
            connected = "已連接" if status['is_connected'] else "未連接"
            queue_size = status.get('queue_size', 0)

            print(f"  • {stream_id}: {running}, {connected}, 佇列: {queue_size}")

            if status.get('last_error'):
                print(f"    錯誤: {status['last_error']}")

        print("\n7. 系統統計...")
        stats = stream_manager.get_statistics()
        print(f"  • 總串流數: {stats['total_streams']}")
        print(f"  • 運行中: {stats['running_streams']}")
        print(f"  • 已連接: {stats['connected_streams']}")
        print(f"  • 處理FPS: {stats['processing_fps']}")

        if stats['stream_types']:
            print("  • 串流類型分布:")
            for stream_type, count in stats['stream_types'].items():
                print(f"    - {stream_type}: {count}")

        print("\n8. 停止串流...")
        stream_manager.stop_all_streams()
        print("OK 所有串流已停止")

    else:
        print("沒有可用的串流進行測試")

    stream_manager.cleanup()
    return True

def test_individual_streams():
    """測試個別串流類型"""
    print("\n=== 測試個別串流類型 ===")

    # 測試本地攝影機
    print("\n測試本地攝影機...")
    from src.streams.http_stream import WebcamStream

    webcam_config = {
        'device_index': 0,
        'resolution': {'width': 640, 'height': 480},
        'fps': 30
    }

    webcam = WebcamStream("test_webcam", "測試攝影機", "本機", webcam_config)

    if webcam.connect():
        print("OK 本地攝影機連接成功")

        if webcam.start_capture():
            print("OK 開始擷取畫面")
            time.sleep(2)

            frame_data = webcam.get_latest_frame()
            if frame_data:
                print(f"OK 成功取得畫面: {frame_data.frame.shape}")
            else:
                print("FAIL 無法取得畫面")

            webcam.stop_capture()
            print("OK 停止擷取")
        else:
            print("FAIL 無法開始擷取")
    else:
        print("FAIL 本地攝影機連接失敗")

def main():
    """主程式"""
    print("開始測試串流系統...")

    try:
        # 檢查設定檔是否存在
        if not os.path.exists("streamSource.json"):
            print("錯誤: 找不到 streamSource.json 設定檔")
            return 1

        # 測試串流管理器
        if not test_stream_manager():
            print("串流管理器測試失敗")
            return 1

        # 測試個別串流
        test_individual_streams()

        print("\n=== 測試完成 ===")
        print("所有測試已完成，檢查上述輸出以了解各串流格式的狀態。")

        return 0

    except KeyboardInterrupt:
        print("\n測試被用戶中斷")
        return 1
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)