"""
修复 Rule Engine 数据
Fix existing rule data: convert lowercase stream_source_type to uppercase
"""

import sys
import os
import io

# 設定 UTF-8 編碼（Windows）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database import SessionLocal
from api.models import DetectionRule


def fix_rule_data():
    """修复规则数据"""
    db = SessionLocal()

    try:
        print("开始修复规则数据...")
        print("="*60)

        # 查询所有规则
        rules = db.query(DetectionRule).all()

        if not rules:
            print("没有找到任何规则")
            return

        fixed_count = 0

        for rule in rules:
            updated = False

            # 修复 stream_source_type (小写转大写)
            if rule.stream_source_type:
                old_value = rule.stream_source_type
                new_value = rule.stream_source_type.upper()
                if old_value != new_value:
                    rule.stream_source_type = new_value
                    print(f"[修复] {rule.rule_id}: stream_source_type '{old_value}' -> '{new_value}'")
                    updated = True

            if updated:
                fixed_count += 1

        # 提交更改
        if fixed_count > 0:
            db.commit()
            print("="*60)
            print(f"✓ 成功修复 {fixed_count} 条规则")
        else:
            print("所有规则数据已经正确，无需修复")

        print("="*60)

    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    fix_rule_data()
