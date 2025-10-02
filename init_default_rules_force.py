"""
強制重新初始化預設 Rule Engine 規則
"""

import sys
import os
import io

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database import SessionLocal, engine, Base
from api.models import DetectionRule
from datetime import datetime

def main():
    """強制重新初始化預設規則"""

    # 創建資料庫表（如果不存在）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # 刪除所有現有規則
        existing_count = db.query(DetectionRule).count()
        if existing_count > 0:
            db.query(DetectionRule).delete()
            db.commit()
            print(f"已刪除 {existing_count} 條現有規則")

        print("\n開始創建預設規則...")

        # 規則 1: 安全帽檢測 - 全部攝影機
        helmet_rule = DetectionRule(
            rule_id="default_helmet_detection",
            name="預設安全帽檢測規則",
            description="檢測所有RTSP攝影機的安全帽違規（需先偵測到人臉）",
            stream_source_type=None,  # 所有類型
            stream_source_ids=None,   # 所有攝影機
            person_ids=None,          # 所有人員
            detection_types=["helmet"],
            confidence_threshold=0.6,
            time_threshold=None,
            notification_enabled=True,
            notification_config={
                "methods": ["api"],
                "priority": "high"
            },
            schedule_enabled=True,
            schedule_config={
                "weekdays": [1, 2, 3, 4, 5],  # 週一到週五
                "time_ranges": [
                    {"start": "08:00", "end": "18:00"}  # 上班時間
                ]
            },
            priority=80,
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(helmet_rule)
        print("[建立] 安全帽檢測規則")

        # 規則 2: 疲勞駕駛檢測 - 全部攝影機
        drowsiness_rule = DetectionRule(
            rule_id="default_drowsiness_detection",
            name="預設疲勞駕駛檢測規則",
            description="檢測所有攝影機的疲勞駕駛狀況",
            stream_source_type=None,
            stream_source_ids=None,
            person_ids=None,
            detection_types=["drowsiness"],
            confidence_threshold=0.7,
            time_threshold=3,  # 持續3秒
            notification_enabled=True,
            notification_config={
                "methods": ["api"],
                "priority": "critical"
            },
            schedule_enabled=False,  # 全天候監控
            schedule_config=None,
            priority=90,  # 高優先級
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(drowsiness_rule)
        print("[建立] 疲勞駕駛檢測規則")

        # 規則 3: 人臉識別 - 全部攝影機
        face_rule = DetectionRule(
            rule_id="default_face_recognition",
            name="預設人臉識別規則",
            description="識別所有攝影機中的已知人員",
            stream_source_type=None,
            stream_source_ids=None,
            person_ids=None,  # 所有已知人員
            detection_types=["face"],
            confidence_threshold=0.5,
            time_threshold=None,
            notification_enabled=True,
            notification_config={
                "methods": ["api"],
                "priority": "medium"
            },
            schedule_enabled=False,
            schedule_config=None,
            priority=70,
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(face_rule)
        print("[建立] 人臉識別規則")

        # 規則 4: 無活動檢測 - 全部攝影機
        inactivity_rule = DetectionRule(
            rule_id="default_inactivity_detection",
            name="預設無活動檢測規則",
            description="檢測所有攝影機的無人無動作狀態（30秒）",
            stream_source_type=None,
            stream_source_ids=None,
            person_ids=None,
            detection_types=["inactivity"],
            confidence_threshold=0.9,  # 無活動檢測的信心度通常是1.0
            time_threshold=30,  # 30秒
            notification_enabled=True,
            notification_config={
                "methods": ["api"],
                "priority": "medium"
            },
            schedule_enabled=True,
            schedule_config={
                "weekdays": [1, 2, 3, 4, 5, 6, 7],  # 全週
                "time_ranges": [
                    {"start": "08:00", "end": "22:00"}  # 工作時段
                ]
            },
            priority=60,
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(inactivity_rule)
        print("[建立] 無活動檢測規則")

        # 規則 5: 綜合檢測 - RTSP 攝影機專用（高優先級）
        comprehensive_rule = DetectionRule(
            rule_id="default_rtsp_comprehensive",
            name="RTSP攝影機綜合檢測",
            description="針對RTSP攝影機的所有檢測類型（不包含無活動檢測）",
            stream_source_type="rtsp",
            stream_source_ids=None,
            person_ids=None,
            detection_types=["helmet", "drowsiness", "face"],
            confidence_threshold=0.65,
            time_threshold=None,
            notification_enabled=True,
            notification_config={
                "methods": ["api"],
                "priority": "high"
            },
            schedule_enabled=False,
            schedule_config=None,
            priority=85,
            enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(comprehensive_rule)
        print("[建立] RTSP綜合檢測規則")

        # 提交所有規則
        db.commit()

        print("\n" + "="*60)
        print("預設規則初始化完成！")
        print("="*60)
        print("\n已創建的規則：")
        print("1. 安全帽檢測規則 (優先級: 80)")
        print("   - 適用: 所有攝影機")
        print("   - 時段: 週一至週五 08:00-18:00")
        print("   - 信心度閾值: 0.6")
        print()
        print("2. 疲勞駕駛檢測規則 (優先級: 90)")
        print("   - 適用: 所有攝影機")
        print("   - 時段: 全天候")
        print("   - 信心度閾值: 0.7")
        print("   - 持續時間: 3秒")
        print()
        print("3. 人臉識別規則 (優先級: 70)")
        print("   - 適用: 所有攝影機")
        print("   - 時段: 全天候")
        print("   - 信心度閾值: 0.5")
        print()
        print("4. 無活動檢測規則 (優先級: 60)")
        print("   - 適用: 所有攝影機")
        print("   - 時段: 全週 08:00-22:00")
        print("   - 信心度閾值: 0.9")
        print("   - 無活動時間: 30秒")
        print()
        print("5. RTSP綜合檢測規則 (優先級: 85)")
        print("   - 適用: 僅RTSP攝影機")
        print("   - 時段: 全天候")
        print("   - 信心度閾值: 0.65")
        print("   - 檢測類型: 安全帽、疲勞駕駛、人臉")
        print()
        print("="*60)
        print("提示：")
        print("- 可透過 API (http://localhost:8232/api/docs) 管理這些規則")
        print("- 規則按優先級從高到低匹配")
        print("- 可隨時啟用/停用規則")
        print("- 可修改信心度閾值、時段等參數")
        print("="*60)

    except Exception as e:
        print(f"錯誤: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
