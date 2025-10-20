"""
檢查檢測規則設定
Check Detection Rules Configuration
"""

import psycopg2
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# 載入 .env
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

def check_rules():
    """檢查檢測規則"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DATABASE", "motion-detector"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        cur = conn.cursor()

        print("=" * 70)
        print("檢測規則狀態 (Detection Rules Status)")
        print("=" * 70)

        # 查詢所有規則
        cur.execute("""
            SELECT
                rule_id,
                name,
                enabled,
                detection_types,
                confidence_threshold,
                notification_enabled,
                created_at
            FROM detection_rules
            ORDER BY created_at DESC
        """)

        rules = cur.fetchall()

        if not rules:
            print("⚠️  沒有找到任何檢測規則！")
            print("\n建議:")
            print("  1. 使用 API 創建檢測規則: POST /api/rules")
            print("  2. 或執行測試腳本創建預設規則")
            return

        print(f"\n找到 {len(rules)} 個檢測規則:\n")

        for i, rule in enumerate(rules, 1):
            rule_id, name, enabled, detection_types, confidence, notification, created = rule

            status = "✓ 啟用" if enabled else "✗ 停用"
            status_color = "32" if enabled else "31"  # Green or Red

            print(f"{i}. {name} ({rule_id})")
            print(f"   狀態: {status}")
            print(f"   檢測類型: {detection_types}")
            print(f"   信心度閾值: {confidence}")
            print(f"   通知: {'啟用' if notification else '停用'}")
            print(f"   建立時間: {created}")
            print("-" * 70)

        # 統計
        print("\n統計資訊:")
        enabled_count = sum(1 for r in rules if r[2])
        print(f"  總規則數: {len(rules)}")
        print(f"  啟用: {enabled_count}")
        print(f"  停用: {len(rules) - enabled_count}")

        # 檢查檢測類型分佈
        all_types = []
        for rule in rules:
            if rule[2]:  # 只統計啟用的規則
                types = rule[3] if isinstance(rule[3], list) else json.loads(rule[3] or '[]')
                all_types.extend(types)

        if all_types:
            print("\n啟用規則的檢測類型分佈:")
            from collections import Counter
            type_counts = Counter(all_types)
            for det_type, count in type_counts.items():
                print(f"  - {det_type}: {count} 個規則")

        # 建議
        print("\n💡 建議:")
        if enabled_count == 0:
            print("  ❌ 所有規則都已停用，不會進行任何檢測")
            print("     請使用 PUT /api/rules/{rule_id} 啟用規則")
        elif 'helmet' not in all_types:
            print("  ⚠  沒有啟用安全帽檢測規則")
        elif 'face' not in all_types:
            print("  ⚠  沒有啟用人臉辨識規則（安全帽檢測需要人臉辨識）")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ 錯誤: {e}")


def create_default_rule():
    """創建預設檢測規則"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DATABASE", "motion-detector"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        cur = conn.cursor()

        # 檢查是否已有規則
        cur.execute("SELECT COUNT(*) FROM detection_rules")
        count = cur.fetchone()[0]

        if count > 0:
            print(f"已有 {count} 個規則存在")
            response = input("是否要創建新的預設規則? (y/N): ")
            if response.lower() != 'y':
                return

        # 創建預設規則
        rule_id = "default_all_detection"
        name = "預設全類型檢測規則"
        detection_types = json.dumps(["helmet", "drowsiness", "face", "inactivity"])

        cur.execute("""
            INSERT INTO detection_rules (
                rule_id, name, description, enabled,
                detection_types, confidence_threshold,
                notification_enabled, notification_config,
                priority
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (rule_id) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                detection_types = EXCLUDED.detection_types
        """, (
            rule_id,
            name,
            "自動創建的預設檢測規則，包含所有檢測類型",
            True,  # enabled
            detection_types,
            0.7,  # confidence_threshold
            True,  # notification_enabled
            json.dumps({"methods": ["database", "websocket"]}),
            10  # priority
        ))

        conn.commit()
        print(f"✓ 已創建預設規則: {rule_id}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ 錯誤: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--create":
        print("=" * 70)
        print("創建預設檢測規則")
        print("=" * 70)
        create_default_rule()
    else:
        check_rules()

        print("\n使用方式:")
        print("  python check_detection_rules.py           # 檢查規則")
        print("  python check_detection_rules.py --create  # 創建預設規則")
