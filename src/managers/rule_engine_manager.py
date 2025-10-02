"""
Rule Engine Manager
規則引擎管理器 - 根據規則處理檢測結果
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import DetectionRule


class RuleEngineManager:
    """規則引擎管理器"""

    def __init__(self):
        """初始化規則引擎"""
        self.logger = logging.getLogger(__name__)
        self.rules_cache = {}
        self.last_reload_time = None
        self.reload_interval = 300  # 5分鐘重新載入規則

    def reload_rules(self):
        """重新載入規則"""
        try:
            db = SessionLocal()
            rules = db.query(DetectionRule).filter(DetectionRule.enabled == True).all()

            self.rules_cache = {}
            for rule in rules:
                self.rules_cache[rule.rule_id] = {
                    'id': rule.id,
                    'rule_id': rule.rule_id,
                    'name': rule.name,
                    'stream_source_type': rule.stream_source_type,
                    'stream_source_ids': rule.stream_source_ids or [],
                    'person_ids': rule.person_ids or [],
                    'detection_types': rule.detection_types or [],
                    'confidence_threshold': rule.confidence_threshold,
                    'time_threshold': rule.time_threshold,
                    'notification_enabled': rule.notification_enabled,
                    'notification_config': rule.notification_config or {},
                    'schedule_enabled': rule.schedule_enabled,
                    'schedule_config': rule.schedule_config or {},
                    'priority': rule.priority
                }

            self.last_reload_time = datetime.now()
            self.logger.info(f"Loaded {len(self.rules_cache)} active rules")
            db.close()

        except Exception as e:
            self.logger.error(f"Failed to reload rules: {e}")

    def should_reload_rules(self) -> bool:
        """檢查是否應該重新載入規則"""
        if not self.last_reload_time:
            return True

        elapsed = (datetime.now() - self.last_reload_time).total_seconds()
        return elapsed > self.reload_interval

    def get_enabled_detection_types(self, stream_id: str, stream_type: str) -> List[str]:
        """
        取得該攝影機需要執行的檢測類型

        Args:
            stream_id: 影像來源ID
            stream_type: 影像來源類型

        Returns:
            需要執行的檢測類型列表
        """
        # 自動重新載入規則
        if self.should_reload_rules():
            self.reload_rules()

        enabled_types = set()

        for rule_id, rule in self.rules_cache.items():
            # 檢查影像來源類型
            if rule['stream_source_type'] and rule['stream_source_type'] != stream_type:
                continue

            # 檢查特定影像來源ID
            if rule['stream_source_ids'] and stream_id not in rule['stream_source_ids']:
                continue

            # 檢查排程
            if rule['schedule_enabled'] and not self._check_schedule(rule['schedule_config']):
                continue

            # 添加該規則的所有檢測類型
            enabled_types.update(rule['detection_types'])

        return list(enabled_types)

    def get_matching_rules(
        self,
        stream_id: str,
        stream_type: str,
        detection_type: str,
        person_id: Optional[str] = None
    ) -> List[Dict]:
        """
        取得匹配的規則

        Args:
            stream_id: 影像來源ID
            stream_type: 影像來源類型
            detection_type: 檢測類型
            person_id: 人員ID (可選)

        Returns:
            匹配的規則列表
        """
        # 自動重新載入規則
        if self.should_reload_rules():
            self.reload_rules()

        matching_rules = []

        for rule_id, rule in self.rules_cache.items():
            # 檢查檢測類型是否匹配
            if detection_type not in rule['detection_types']:
                continue

            # 檢查影像來源類型
            if rule['stream_source_type'] and rule['stream_source_type'] != stream_type:
                continue

            # 檢查特定影像來源ID
            if rule['stream_source_ids'] and stream_id not in rule['stream_source_ids']:
                continue

            # 檢查人員ID (僅用於人臉識別)
            if detection_type == 'face' and rule['person_ids']:
                if not person_id or person_id not in rule['person_ids']:
                    continue

            # 檢查排程
            if rule['schedule_enabled'] and not self._check_schedule(rule['schedule_config']):
                continue

            matching_rules.append(rule)

        # 按優先級排序
        matching_rules.sort(key=lambda x: x['priority'], reverse=True)

        return matching_rules

    def _check_schedule(self, schedule_config: Dict) -> bool:
        """
        檢查當前時間是否在排程範圍內

        Args:
            schedule_config: 排程配置

        Returns:
            是否在排程範圍內
        """
        if not schedule_config:
            return True

        now = datetime.now()

        # 檢查星期
        weekdays = schedule_config.get('weekdays', [])
        if weekdays and now.weekday() + 1 not in weekdays:
            return False

        # 檢查時間範圍
        time_ranges = schedule_config.get('time_ranges', [])
        if time_ranges:
            current_time = now.time()
            in_range = False

            for time_range in time_ranges:
                start_time = self._parse_time(time_range.get('start', '00:00'))
                end_time = self._parse_time(time_range.get('end', '23:59'))

                if start_time <= current_time <= end_time:
                    in_range = True
                    break

            if not in_range:
                return False

        return True

    def _parse_time(self, time_str: str) -> time:
        """
        解析時間字串

        Args:
            time_str: 時間字串 (HH:MM)

        Returns:
            time物件
        """
        try:
            parts = time_str.split(':')
            return time(int(parts[0]), int(parts[1]))
        except:
            return time(0, 0)

    def should_trigger_violation(
        self,
        stream_id: str,
        stream_type: str,
        detection_type: str,
        confidence: float,
        person_id: Optional[str] = None
    ) -> tuple[bool, Optional[Dict]]:
        """
        判斷是否應該觸發違規

        Args:
            stream_id: 影像來源ID
            stream_type: 影像來源類型
            detection_type: 檢測類型
            confidence: 信心度
            person_id: 人員ID

        Returns:
            (是否觸發, 匹配的規則)
        """
        # 取得匹配的規則
        matching_rules = self.get_matching_rules(
            stream_id=stream_id,
            stream_type=stream_type,
            detection_type=detection_type,
            person_id=person_id
        )

        if not matching_rules:
            return False, None

        # 使用優先級最高的規則
        rule = matching_rules[0]

        # 檢查信心度閾值
        if confidence < rule['confidence_threshold']:
            return False, None

        return True, rule

    def get_notification_config(self, rule: Dict) -> Dict:
        """
        取得通知配置

        Args:
            rule: 規則

        Returns:
            通知配置
        """
        if not rule['notification_enabled']:
            return {}

        return rule['notification_config']

    def log_rule_trigger(
        self,
        rule_id: str,
        stream_id: str,
        detection_type: str,
        violation_id: str
    ):
        """
        記錄規則觸發

        Args:
            rule_id: 規則ID
            stream_id: 影像來源ID
            detection_type: 檢測類型
            violation_id: 違規ID
        """
        self.logger.info(
            f"Rule triggered: {rule_id} | "
            f"Stream: {stream_id} | "
            f"Detection: {detection_type} | "
            f"Violation: {violation_id}"
        )

    def get_active_rules_count(self) -> int:
        """取得啟用的規則數量"""
        if self.should_reload_rules():
            self.reload_rules()
        return len(self.rules_cache)

    def get_rules_by_detection_type(self, detection_type: str) -> List[Dict]:
        """
        取得特定檢測類型的規則

        Args:
            detection_type: 檢測類型

        Returns:
            規則列表
        """
        if self.should_reload_rules():
            self.reload_rules()

        return [
            rule for rule in self.rules_cache.values()
            if detection_type in rule['detection_types']
        ]
