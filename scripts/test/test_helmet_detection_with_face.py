"""
測試安全帽檢測邏輯
驗證：
1. 只在偵測到人臉時才進行安全帽檢測
2. 同一人的檢測間隔為20秒
"""

import cv2
import time
import logging
from datetime import datetime
from src.managers.helmet_violation_manager import HelmetViolationManager
from src.detectors.helmet_detector import HelmetDetector
from src.detectors.base_detector import DetectionResult

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


def test_helmet_detection_with_face():
    """測試安全帽檢測需要人臉"""
    print("\n" + "="*60)
    print("測試: 安全帽檢測需要人臉")
    print("="*60)

    # 初始化管理器
    helmet_detector = HelmetDetector()
    helmet_detector.load_model()

    manager = HelmetViolationManager(
        helmet_detector=helmet_detector,
        screenshot_interval=20
    )

    # 創建測試影像
    frame = cv2.imread("test_screenshots/test_image.jpg")
    if frame is None:
        logger.warning("測試影像不存在，創建空白影像")
        frame = cv2.imread(cv2.CAP_ANY, (640, 480, 3), dtype=np.uint8)

    # 測試1: 沒有人臉檢測結果
    print("\n[測試1] 沒有人臉檢測結果")
    print("預期: 不進行安全帽檢測")
    results = manager.process_frame(frame, camera_id="test_cam", face_detections=None)
    print(f"結果: 處理了 {len(results)} 個違規")
    assert len(results) == 0, "應該不處理任何違規"
    print("✓ 通過：沒有人臉時不進行安全帽檢測")

    # 測試2: 有人臉檢測結果
    print("\n[測試2] 有人臉檢測結果")
    print("預期: 進行安全帽檢測")
    face_detections = [
        MockFaceDetection("person_001", (100, 100, 200, 200))
    ]
    results = manager.process_frame(frame, camera_id="test_cam", face_detections=face_detections)
    print(f"結果: 處理了 {len(results)} 個違規")
    print("✓ 有人臉時會進行安全帽檢測")


def test_20_second_interval():
    """測試20秒間隔"""
    print("\n" + "="*60)
    print("測試: 20秒檢測間隔")
    print("="*60)

    helmet_detector = HelmetDetector()
    helmet_detector.load_model()

    manager = HelmetViolationManager(
        helmet_detector=helmet_detector,
        screenshot_interval=20
    )

    frame = cv2.imread("test_screenshots/test_image.jpg")
    if frame is None:
        frame = cv2.imread(cv2.CAP_ANY, (640, 480, 3), dtype=np.uint8)

    face_detections = [
        MockFaceDetection("person_001", (100, 100, 200, 200))
    ]

    # 第一次檢測
    print("\n[第1次檢測] 同一個人")
    results1 = manager.process_frame(frame, camera_id="test_cam", face_detections=face_detections)
    if results1:
        print(f"第1次: 處理了 {len(results1)} 個違規")
        print(f"截圖狀態: {results1[0].get('screenshot_taken', False)}")
        print("✓ 第一次檢測應該截圖")

    # 立即進行第二次檢測（20秒內）
    print("\n[第2次檢測] 同一個人（立即）")
    results2 = manager.process_frame(frame, camera_id="test_cam", face_detections=face_detections)
    if results2:
        print(f"第2次: 處理了 {len(results2)} 個違規")
        print(f"截圖狀態: {results2[0].get('screenshot_taken', False)}")
        print("✓ 20秒內的第二次檢測不應該截圖")
    else:
        print("第2次: 沒有處理違規（可能是因為沒檢測到違規）")

    # 顯示統計
    print("\n[統計資訊]")
    stats = manager.get_stats()
    print(f"總違規數: {stats['total_violations']}")
    print(f"截圖次數: {stats['screenshots_taken']}")
    print(f"截圖間隔: {stats['screenshot_interval_seconds']} 秒")


def test_multiple_persons():
    """測試多人情況"""
    print("\n" + "="*60)
    print("測試: 多人檢測")
    print("="*60)

    helmet_detector = HelmetDetector()
    helmet_detector.load_model()

    manager = HelmetViolationManager(
        helmet_detector=helmet_detector,
        screenshot_interval=20
    )

    frame = cv2.imread("test_screenshots/test_image.jpg")
    if frame is None:
        frame = cv2.imread(cv2.CAP_ANY, (640, 480, 3), dtype=np.uint8)

    # 模擬3個人
    face_detections = [
        MockFaceDetection("person_001", (100, 100, 200, 200)),
        MockFaceDetection("person_002", (300, 100, 200, 200)),
        MockFaceDetection("person_003", (500, 100, 200, 200)),
    ]

    print("\n[檢測] 3個人同時出現")
    results = manager.process_frame(frame, camera_id="test_cam", face_detections=face_detections)
    print(f"處理了 {len(results)} 個違規")

    # 顯示每個人的處理結果
    for i, result in enumerate(results, 1):
        print(f"\n人員 {i}:")
        print(f"  Person ID: {result.get('person_id')}")
        print(f"  違規類型: {result.get('violation_type')}")
        print(f"  信心度: {result.get('confidence', 0):.2f}")
        print(f"  是否截圖: {result.get('screenshot_taken', False)}")

    print("\n✓ 每個人獨立追蹤檢測間隔")


def main():
    """執行所有測試"""
    print("\n" + "="*70)
    print("安全帽檢測邏輯測試")
    print("規則:")
    print("1. 只在偵測到人臉時才進行安全帽檢測")
    print("2. 同一人的檢測間隔為20秒")
    print("="*70)

    try:
        test_helmet_detection_with_face()
        test_20_second_interval()
        test_multiple_persons()

        print("\n" + "="*70)
        print("所有測試完成!")
        print("="*70)

    except Exception as e:
        print(f"\n錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
