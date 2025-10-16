#!/usr/bin/env python3
"""
測試人臉檢測管理器功能
Test Face Detection Manager functionality
"""

import cv2
import sys
import os
import time
import numpy as np
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.detectors.face_recognizer import FaceRecognizer
from src.managers.face_detection_manager import FaceDetectionManager
from src.managers.notification_sender import NotificationSender
from src.managers.screenshot_manager import ScreenshotManager

def test_face_detection_with_interval():
    """測試人臉檢測間隔控制功能"""

    print("=== 人臉檢測間隔控制測試 ===")

    try:
        # 初始化人臉識別器
        print("1. 初始化人臉識別器...")
        face_recognizer = FaceRecognizer(
            confidence_threshold=0.6,
            face_database_path="data/test_face_database.pkl",
            person_info_path="data/test_person_info.json"
        )

        if not face_recognizer.load_model():
            print("❌ 人臉識別器加載失敗")
            return False

        print("✅ 人臉識別器初始化成功")

        # 初始化通知發送器（模擬）
        print("2. 初始化通知發送器...")
        notification_sender = NotificationSender(
            endpoint="http://localhost:8080/test",
            timeout=5,
            async_mode=False  # 同步模式便於測試
        )

        # 初始化截圖管理器
        print("3. 初始化截圖管理器...")
        screenshot_manager = ScreenshotManager(
            screenshot_path="data/test_screenshots",
            image_quality=85
        )

        # 初始化人臉檢測管理器（5秒間隔用於測試）
        print("4. 初始化人臉檢測管理器...")
        face_detection_manager = FaceDetectionManager(
            face_recognizer=face_recognizer,
            notification_sender=notification_sender,
            screenshot_manager=screenshot_manager,
            notification_interval=5,  # 5秒間隔用於測試
            records_dir="data/test_face_detections"
        )

        print("✅ 所有組件初始化成功")

        # 測試攝像頭
        print("5. 嘗試打開攝像頭...")
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("❌ 無法打開攝像頭，使用測試圖片...")
            return test_with_sample_images(face_detection_manager)

        print("✅ 攝像頭打開成功")
        print("\n開始檢測...")
        print("按 'q' 退出，按 'r' 重置通知歷史")

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ 無法讀取攝像頭畫面")
                break

            frame_count += 1

            # 每5幀處理一次（減少CPU負載）
            if frame_count % 5 == 0:
                # 處理人臉檢測
                results = face_detection_manager.process_frame(frame, "test_camera")

                if results:
                    for result in results:
                        person_name = result.get("person_name", "Unknown")
                        confidence = result.get("confidence", 0)
                        notification_sent = result.get("notification_sent", False)

                        print(f"檢測到: {person_name} (信心度: {confidence:.2f}) "
                              f"通知: {'✅' if notification_sent else '❌'}")

            # 顯示畫面（可選）
            cv2.imshow('Face Detection Test', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                face_detection_manager.reset_notification_history()
                print("🔄 已重置通知歷史")

        cap.release()
        cv2.destroyAllWindows()

        # 顯示統計
        print("\n=== 檢測統計 ===")
        stats = face_detection_manager.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

        return True

    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        return False

def test_with_sample_images(face_detection_manager):
    """使用範例圖片測試"""
    print("使用範例圖片進行測試...")

    # 創建一個簡單的測試圖片
    test_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

    # 添加一些文字
    cv2.putText(test_frame, "Test Face Detection", (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    print("處理測試圖片...")
    for i in range(3):
        print(f"處理第 {i+1} 次...")
        results = face_detection_manager.process_frame(test_frame, "test_camera")
        print(f"結果: {len(results)} 個檢測結果")

        # 等待一下以測試間隔控制
        if i < 2:
            print("等待 3 秒...")
            time.sleep(3)

    return True

def test_database_operations():
    """測試數據庫操作"""
    print("\n=== 測試數據庫操作 ===")

    face_recognizer = FaceRecognizer(
        face_database_path="data/test_face_database.pkl",
        person_info_path="data/test_person_info.json"
    )

    if not face_recognizer.load_model():
        print("❌ 人臉識別器加載失敗")
        return False

    # 測試獲取數據庫統計
    stats = face_recognizer.get_database_stats()
    print(f"數據庫統計: {stats}")

    # 測試獲取所有人員信息
    all_persons = face_recognizer.get_all_persons()
    print(f"已註冊人員數量: {len(all_persons)}")

    for person_id, info in all_persons.items():
        print(f"- {person_id}: {info.get('name', 'Unknown')}")

    return True

def main():
    """主函數"""
    print("Face Recognition with Notification Interval Test")
    print("=" * 50)

    # 確保目錄存在
    os.makedirs("data", exist_ok=True)

    # 測試數據庫操作
    test_database_operations()

    # 測試人臉檢測間隔控制
    success = test_face_detection_with_interval()

    if success:
        print("\n✅ 測試完成")
    else:
        print("\n❌ 測試失敗")

    return success

if __name__ == "__main__":
    main()