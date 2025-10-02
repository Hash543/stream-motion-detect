#!/usr/bin/env python3
"""
測試安全帽違規10秒間隔截圖功能
"""

import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime

# 添加src目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.detectors.helmet_detector import HelmetDetector
from src.managers.helmet_violation_manager import HelmetViolationManager
from src.managers.screenshot_manager import ScreenshotManager

def create_test_frame():
    """創建測試用的幀"""
    # 創建一個簡單的測試圖像（黑色背景）
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 添加一些文本以便識別
    cv2.putText(frame, f"Test Frame - {datetime.now().strftime('%H:%M:%S')}",
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return frame

def test_helmet_violation_interval():
    """測試安全帽違規間隔功能"""
    print("開始測試安全帽違規10秒間隔截圖功能...")

    try:
        # 初始化組件
        print("1. 初始化檢測器和管理器...")

        # 創建截圖管理器
        screenshot_manager = ScreenshotManager(
            screenshot_path="./test_screenshots/",
            image_quality=85
        )

        # 創建安全帽檢測器（使用默認模型）
        helmet_detector = HelmetDetector(confidence_threshold=0.5)
        if not helmet_detector.load_model():
            print("警告：無法加載安全帽檢測模型，將使用模擬數據")

        # 創建安全帽違規管理器（設置為5秒間隔便於測試）
        violation_manager = HelmetViolationManager(
            helmet_detector=helmet_detector,
            screenshot_manager=screenshot_manager,
            screenshot_interval=5  # 5秒間隔便於測試
        )

        print("2. 開始模擬檢測...")

        # 模擬檢測結果
        from src.detectors.base_detector import DetectionResult

        # 創建模擬的違規檢測結果
        mock_violation = DetectionResult(
            detection_type="helmet_violation",
            confidence=0.85,
            bbox=(100, 50, 200, 300),  # x, y, w, h
            additional_data={"violation_type": "no_helmet"}
        )

        # 模擬同一個人員多次違規
        test_person_id = "test_person_001"

        for i in range(6):  # 測試6次，應該只有2-3次截圖
            print(f"\n--- 測試輪次 {i+1} ---")

            # 創建測試幀
            frame = create_test_frame()

            # 模擬違規檢測（直接調用處理方法）
            current_time = datetime.now()

            # 檢查是否應該截圖
            should_screenshot = violation_manager._should_take_screenshot(test_person_id, current_time)

            print(f"時間: {current_time.strftime('%H:%M:%S')}")
            print(f"應該截圖: {should_screenshot}")

            # 始終處理違規，讓管理器內部決定是否截圖
            result = violation_manager._process_single_violation(
                mock_violation, frame, "test_camera", current_time, test_person_id
            )

            if result and result.get('screenshot_taken'):
                print(f"[SUCCESS] Screenshot saved: {result.get('image_path')}")
            elif result:
                print("[SKIP] Screenshot skipped (interval not reached)")
            else:
                print("[FAILED] Processing failed")

            # 等待2秒再進行下次測試
            if i < 5:  # 最後一次不等待
                time.sleep(2)

        print("\n3. 檢查統計信息...")
        stats = violation_manager.get_stats()
        print(f"總違規次數: {stats['total_violations']}")
        print(f"截圖次數: {stats['screenshots_taken']}")
        print(f"唯一違規者: {stats['unique_violators']}")

        print("\n4. 檢查違規歷史...")
        history = violation_manager.get_violation_history(test_person_id)
        print(f"歷史記錄數量: {len(history)}")

        for record in history:
            print(f"- {record['detection_time']}: {record['violation_type']} (置信度: {record['confidence']})")

        print("\n✅ 測試完成！")
        print(f"截圖保存在: {screenshot_manager.screenshot_path}")

        # 清理
        violation_manager.cleanup()

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_helmet_violation_interval()