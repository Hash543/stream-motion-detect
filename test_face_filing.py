#!/usr/bin/env python3
"""
測試人臉檢測自動建檔功能
"""

import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime

# 添加src目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.detectors.face_recognizer import FaceRecognizer
from src.detectors.base_detector import DetectionResult
from src.managers.face_detection_manager import FaceDetectionManager
from src.managers.screenshot_manager import ScreenshotManager
from src.managers.database_manager import DatabaseManager

def create_test_frame():
    """創建測試用的幀"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, f"Face Test Frame - {datetime.now().strftime('%H:%M:%S')}",
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame

def create_mock_face_detections():
    """創建模擬的人臉檢測結果"""
    detections = []

    # 模擬幾個不同的人員
    test_persons = [
        {"person_id": "EMP001", "name": "張小明", "confidence": 0.92},
        {"person_id": "EMP002", "name": "李美華", "confidence": 0.89},
        {"person_id": "VIS001", "name": "王訪客", "confidence": 0.85},
        {"person_id": "unknown", "name": "Unknown", "confidence": 0.45}  # 未知人員
    ]

    for i, person in enumerate(test_persons):
        detection = DetectionResult(
            detection_type="face",
            confidence=person["confidence"],
            bbox=(100 + i*100, 50, 80, 100),  # x, y, w, h
            person_id=person["person_id"],
            additional_data={
                "person_name": person["name"],
                "face_embedding": f"mock_embedding_{person['person_id']}"
            }
        )
        detections.append(detection)

    return detections

def test_face_auto_filing():
    """測試人臉檢測自動建檔功能"""
    print("開始測試人臉檢測自動建檔功能...")

    try:
        # 初始化組件
        print("1. 初始化檢測器和管理器...")

        # 創建資料庫管理器
        db_manager = DatabaseManager("test_filing.db")

        # 創建截圖管理器
        screenshot_manager = ScreenshotManager(
            screenshot_path="./test_face_screenshots/",
            image_quality=85
        )

        # 創建人臉識別器（使用默認配置）
        face_recognizer = FaceRecognizer(confidence_threshold=0.7)
        if not face_recognizer.load_model():
            print("警告：無法加載人臉識別模型，將使用模擬數據")

        # 創建人臉檢測管理器（啟用自動建檔）
        face_manager = FaceDetectionManager(
            face_recognizer=face_recognizer,
            screenshot_manager=screenshot_manager,
            database_manager=db_manager,
            notification_interval=3,  # 3秒間隔便於測試
            auto_filing=True  # 啟用自動建檔
        )

        print("2. 檢查資料庫初始狀態...")
        initial_persons = db_manager.get_all_persons()
        print(f"初始人員記錄數量: {len(initial_persons)}")

        print("3. 開始模擬人臉檢測...")

        # 創建模擬檢測結果
        mock_detections = create_mock_face_detections()

        # 模擬多輪檢測
        for round_num in range(3):
            print(f"\n--- 檢測輪次 {round_num + 1} ---")

            frame = create_test_frame()

            # 直接使用模擬的檢測結果處理
            for detection in mock_detections:
                result = face_manager._process_single_detection(
                    detection, frame, "test_camera", datetime.now()
                )

                if result:
                    person_id = result["person_id"]
                    person_name = result["person_name"]
                    notification_sent = result["notification_sent"]

                    print(f"  處理人員: {person_name} ({person_id})")
                    print(f"    通知狀態: {'已發送' if notification_sent else '已跳過'}")

            time.sleep(1)  # 等待1秒進行下一輪

        print("\n4. 檢查建檔結果...")

        # 檢查資料庫中的人員記錄
        all_persons = db_manager.get_all_persons()
        print(f"總人員記錄數量: {len(all_persons)}")

        for person in all_persons:
            print(f"  - {person['name']} ({person['person_id']})")
            print(f"    創建時間: {person['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    最後更新: {person['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            if person['additional_info']:
                import json
                info = json.loads(person['additional_info'])
                if 'last_seen_at' in info:
                    print(f"    最後出現: {info['last_seen_at']}")
                if 'last_seen_camera' in info:
                    print(f"    最後攝像頭: {info['last_seen_camera']}")
            print()

        print("5. 檢查統計信息...")
        stats = face_manager.get_stats()
        print(f"總檢測次數: {stats['total_detections']}")
        print(f"建檔人數: {stats['persons_filed']}")
        print(f"唯一人員數: {stats['unique_persons_detected']}")
        print(f"通知次數: {stats['notifications_sent']}")

        print("6. 測試重複檢測...")
        # 再次檢測同一人員，確認不會重複建檔
        print("再次檢測已存在的人員...")

        detection = mock_detections[0]  # 重複檢測第一個人員
        result = face_manager._process_single_detection(
            detection, frame, "test_camera", datetime.now()
        )

        final_stats = face_manager.get_stats()
        print(f"重複檢測後建檔人數: {final_stats['persons_filed']} (應該沒有增加)")

        print("\n[COMPLETED] 測試完成！")
        print(f"資料庫文件: test_filing.db")
        print(f"截圖目錄: test_face_screenshots/")

        # 清理
        face_manager.cleanup()

    except Exception as e:
        print(f"[ERROR] 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_face_auto_filing()