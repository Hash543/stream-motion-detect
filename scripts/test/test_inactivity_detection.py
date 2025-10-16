"""
測試無活動檢測邏輯
驗證：
1. 30秒沒有偵測到人臉且沒有動作時觸發通知
2. 檢測間隔控制（30秒內不重複通知）
3. 多攝影機獨立追蹤
"""

import cv2
import time
import logging
import numpy as np
from datetime import datetime
from src.managers.inactivity_detection_manager import InactivityDetectionManager

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockFaceDetection:
    """模擬人臉檢測結果"""
    def __init__(self, person_id: str, bbox: tuple):
        self.person_id = person_id
        self.bbox = bbox  # (x, y, width, height)


def create_static_frame():
    """創建靜態測試影像（無動作）"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # 添加一些靜態內容
    cv2.rectangle(frame, (100, 100), (200, 200), (100, 100, 100), -1)
    cv2.putText(frame, "Static Scene", (220, 150), cv2.FONT_HERSHEY_SIMPLEX,
                1, (200, 200, 200), 2)
    return frame


def create_moving_frame(frame_num):
    """創建有動作的測試影像"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # 添加移動的物體
    x = 100 + (frame_num * 10) % 400
    cv2.rectangle(frame, (x, 100), (x + 100, 200), (100, 100, 100), -1)
    cv2.putText(frame, f"Moving Scene {frame_num}", (220, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
    return frame


def test_no_activity_detection():
    """測試無活動檢測（無人臉 + 無動作）"""
    print("\n" + "="*60)
    print("測試: 無活動檢測 (30秒無人臉 + 無動作)")
    print("="*60)

    # 初始化管理器（設定較短的閾值用於測試）
    manager = InactivityDetectionManager(
        inactivity_threshold=5,  # 5秒用於快速測試
        motion_threshold=5.0,
        check_interval=5
    )

    # 創建靜態測試影像
    frame = create_static_frame()
    camera_id = "test_cam_001"

    print("\n[測試1] 持續無人臉且無動作")
    print("預期: 5秒後觸發無活動檢測")

    # 模擬10秒的處理（每秒1次）
    for i in range(10):
        print(f"\n第 {i+1} 秒...")
        results = manager.process_frame(
            frame=frame,
            camera_id=camera_id,
            face_detections=None  # 無人臉
        )

        if results and len(results) > 0:
            result = results[0]
            print(f"[OK] 無活動檢測觸發!")
            print(f"  檢測類型: {result.detection_type}")
            print(f"  信心度: {result.confidence}")
            if result.additional_data:
                print(f"  無人臉時間: {result.additional_data.get('time_since_face_seconds', 0):.0f}秒")
                print(f"  無動作時間: {result.additional_data.get('time_since_motion_seconds', 0):.0f}秒")
                print(f"  動作分數: {result.additional_data.get('motion_score', 0):.2f}%")
            break
        else:
            print(f"  尚未觸發（需要累積 5 秒）")

        time.sleep(1)
    else:
        print("[ERROR] 測試失敗：未觸發無活動檢測")
        return False

    print("\n[OK] 測試通過：成功檢測到無活動狀態")
    return True


def test_motion_prevents_detection():
    """測試有動作時不觸發檢測"""
    print("\n" + "="*60)
    print("測試: 有動作時不觸發無活動檢測")
    print("="*60)

    manager = InactivityDetectionManager(
        inactivity_threshold=5,
        motion_threshold=5.0,
        check_interval=5
    )

    camera_id = "test_cam_002"

    print("\n[測試2] 無人臉但有動作")
    print("預期: 不觸發無活動檢測")

    # 模擬10秒，提供有動作的影像
    for i in range(10):
        frame = create_moving_frame(i)
        results = manager.process_frame(
            frame=frame,
            camera_id=camera_id,
            face_detections=None
        )

        if results and len(results) > 0:
            print(f"[ERROR] 測試失敗：不應該觸發檢測（第{i+1}秒有動作）")
            return False

        time.sleep(1)

    print("[OK] 測試通過：有動作時不觸發檢測")
    return True


def test_face_prevents_detection():
    """測試有人臉時不觸發檢測"""
    print("\n" + "="*60)
    print("測試: 有人臉時不觸發無活動檢測")
    print("="*60)

    manager = InactivityDetectionManager(
        inactivity_threshold=5,
        motion_threshold=5.0,
        check_interval=5
    )

    frame = create_static_frame()
    camera_id = "test_cam_003"
    face_detections = [
        MockFaceDetection("person_001", (100, 100, 200, 200))
    ]

    print("\n[測試3] 有人臉但無動作")
    print("預期: 不觸發無活動檢測")

    # 模擬10秒
    for i in range(10):
        results = manager.process_frame(
            frame=frame,
            camera_id=camera_id,
            face_detections=face_detections
        )

        if results and len(results) > 0:
            print(f"[ERROR] 測試失敗：不應該觸發檢測（有人臉）")
            return False

        time.sleep(1)

    print("[OK] 測試通過：有人臉時不觸發檢測")
    return True


def test_detection_interval():
    """測試檢測間隔控制"""
    print("\n" + "="*60)
    print("測試: 檢測間隔控制（避免重複通知）")
    print("="*60)

    manager = InactivityDetectionManager(
        inactivity_threshold=3,
        motion_threshold=5.0,
        check_interval=5  # 5秒間隔
    )

    frame = create_static_frame()
    camera_id = "test_cam_004"

    print("\n[測試4] 檢測間隔控制")

    # 第一次應該觸發
    time.sleep(3.5)
    results1 = manager.process_frame(frame, camera_id, None)
    if results1 and len(results1) > 0:
        print("[OK] 第1次檢測: 觸發通知")
    else:
        print("[ERROR] 第1次檢測: 未觸發（應該要觸發）")
        return False

    # 立即第二次應該不觸發（未滿5秒間隔）
    results2 = manager.process_frame(frame, camera_id, None)
    if results2 and len(results2) > 0:
        print("[ERROR] 第2次檢測: 不應該觸發（未滿間隔時間）")
        return False
    else:
        print("[OK] 第2次檢測: 未觸發（間隔控制生效）")

    # 等待5秒後應該再次觸發
    time.sleep(5.5)
    results3 = manager.process_frame(frame, camera_id, None)
    if results3 and len(results3) > 0:
        print("[OK] 第3次檢測: 觸發通知（已滿間隔時間）")
    else:
        print("[ERROR] 第3次檢測: 未觸發（應該要觸發）")
        return False

    print("\n[OK] 測試通過：間隔控制正常運作")
    return True


def test_multiple_cameras():
    """測試多攝影機獨立追蹤"""
    print("\n" + "="*60)
    print("測試: 多攝影機獨立追蹤")
    print("="*60)

    manager = InactivityDetectionManager(
        inactivity_threshold=3,
        motion_threshold=5.0,
        check_interval=5
    )

    static_frame = create_static_frame()
    moving_frame = create_moving_frame(0)

    print("\n[測試5] 兩個攝影機不同狀態")
    print("  Camera A: 無活動")
    print("  Camera B: 有動作")

    time.sleep(3.5)

    # Camera A 應該觸發
    results_a = manager.process_frame(static_frame, "camera_a", None)
    if results_a and len(results_a) > 0:
        print("[OK] Camera A: 觸發無活動檢測")
    else:
        print("[ERROR] Camera A: 未觸發（應該要觸發）")
        return False

    # Camera B 不應該觸發
    results_b = manager.process_frame(moving_frame, "camera_b", None)
    if results_b and len(results_b) > 0:
        print("[ERROR] Camera B: 不應該觸發（有動作）")
        return False
    else:
        print("[OK] Camera B: 未觸發（有動作）")

    print("\n[OK] 測試通過：多攝影機獨立追蹤正常")
    return True


def test_statistics():
    """測試統計資訊"""
    print("\n" + "="*60)
    print("測試: 統計資訊")
    print("="*60)

    manager = InactivityDetectionManager(
        inactivity_threshold=2,
        motion_threshold=5.0,
        check_interval=3
    )

    frame = create_static_frame()

    # 觸發幾次檢測
    time.sleep(2.5)
    manager.process_frame(frame, "cam_1", None)
    time.sleep(3.5)
    manager.process_frame(frame, "cam_1", None)

    # 獲取統計
    stats = manager.get_stats()

    print("\n[統計資訊]")
    print(f"  總檢測次數: {stats['total_detections']}")
    print(f"  截圖次數: {stats['screenshots_taken']}")
    print(f"  追蹤攝影機數: {stats['tracked_cameras']}")
    print(f"  無活動閾值: {stats['inactivity_threshold_seconds']}秒")
    print(f"  動作閾值: {stats['motion_threshold']}%")
    print(f"  檢測間隔: {stats['check_interval_seconds']}秒")

    if stats['total_detections'] > 0:
        print("\n[OK] 測試通過：統計資訊正常")
        return True
    else:
        print("\n[ERROR] 測試失敗：統計資訊異常")
        return False


def main():
    """執行所有測試"""
    print("\n" + "="*70)
    print("無活動檢測測試")
    print("規則:")
    print("1. 30秒沒有偵測到人臉 + 30秒沒有動作 → 觸發通知")
    print("2. 有人臉或有動作 → 不觸發")
    print("3. 檢測間隔控制（避免重複通知）")
    print("4. 多攝影機獨立追蹤")
    print("="*70)

    results = []

    try:
        print("\n開始測試...")

        # 執行所有測試
        results.append(("無活動檢測", test_no_activity_detection()))
        results.append(("動作防止檢測", test_motion_prevents_detection()))
        results.append(("人臉防止檢測", test_face_prevents_detection()))
        results.append(("間隔控制", test_detection_interval()))
        results.append(("多攝影機追蹤", test_multiple_cameras()))
        results.append(("統計資訊", test_statistics()))

        # 顯示測試結果摘要
        print("\n" + "="*70)
        print("測試結果摘要")
        print("="*70)

        for test_name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {test_name}")

        # 計算通過率
        passed = sum(1 for _, result in results if result)
        total = len(results)
        pass_rate = (passed / total) * 100

        print("\n" + "="*70)
        print(f"測試完成: {passed}/{total} 通過 ({pass_rate:.1f}%)")
        print("="*70)

        return pass_rate == 100.0

    except Exception as e:
        print(f"\n[ERROR] 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
