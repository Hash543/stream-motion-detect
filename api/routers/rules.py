"""
Detection Rule Engine API Routes
規則引擎CRUD API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from api.database import get_db
from api.models import DetectionRule
from api.schemas import (
    DetectionRuleCreate, DetectionRuleUpdate, DetectionRuleResponse,
    MessageResponse, StreamType, DetectionType
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[DetectionRuleResponse])
def list_rules(
    skip: int = 0,
    limit: int = 100,
    enabled: Optional[bool] = None,
    stream_type: Optional[StreamType] = None,
    detection_type: Optional[DetectionType] = None,
    db: Session = Depends(get_db)
):
    """
    取得檢測規則列表

    - **skip**: 跳過筆數
    - **limit**: 限制筆數
    - **enabled**: 篩選是否啟用
    - **stream_type**: 篩選影像來源類型
    - **detection_type**: 篩選檢測類型
    """
    query = db.query(DetectionRule)

    if enabled is not None:
        query = query.filter(DetectionRule.enabled == enabled)
    if stream_type:
        query = query.filter(DetectionRule.stream_source_type == stream_type)
    if detection_type:
        # 篩選包含特定檢測類型的規則
        query = query.filter(DetectionRule.detection_types.contains([detection_type]))

    rules = query.order_by(DetectionRule.priority.desc()).offset(skip).limit(limit).all()
    return rules


@router.get("/{rule_id}", response_model=DetectionRuleResponse)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    """
    取得特定檢測規則

    - **rule_id**: 規則ID
    """
    rule = db.query(DetectionRule).filter(DetectionRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")
    return rule


@router.post("/", response_model=DetectionRuleResponse)
def create_rule(
    rule: DetectionRuleCreate,
    db: Session = Depends(get_db)
):
    """
    建立檢測規則

    - **rule_id**: 規則ID (唯一)
    - **name**: 規則名稱
    - **description**: 規則描述
    - **enabled**: 是否啟用
    - **stream_source_type**: 影像來源類型篩選 (可選，空=所有類型)
    - **stream_source_ids**: 特定影像來源ID列表 (可選，空=所有來源)
    - **person_ids**: 特定人員ID列表 (可選，空=所有人員)
    - **detection_types**: 檢測類型列表 (必填，如: ["helmet", "drowsiness"])
    - **confidence_threshold**: 信心度閾值 (0.0-1.0)
    - **time_threshold**: 時間閾值(秒)，用於需要持續時間的檢測
    - **notification_enabled**: 是否啟用通知
    - **notification_config**: 通知配置
    - **schedule_enabled**: 是否啟用排程
    - **schedule_config**: 排程配置
    - **priority**: 優先級

    範例:
    ```json
    {
        "rule_id": "rule_001",
        "name": "工廠入口安全帽檢測",
        "description": "檢測工廠入口人員是否佩戴安全帽",
        "enabled": true,
        "stream_source_type": "RTSP",
        "stream_source_ids": ["camera_001", "camera_002"],
        "person_ids": null,
        "detection_types": ["helmet"],
        "confidence_threshold": 0.8,
        "notification_enabled": true,
        "notification_config": {
            "api_endpoint": "https://api.example.com/violations",
            "include_image": true
        },
        "schedule_enabled": true,
        "schedule_config": {
            "weekdays": [1, 2, 3, 4, 5],
            "time_ranges": [
                {"start": "08:00", "end": "17:00"}
            ]
        },
        "priority": 10
    }
    ```
    """
    # 檢查是否已存在
    existing = db.query(DetectionRule).filter(DetectionRule.rule_id == rule.rule_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Rule ID already exists")

    # 驗證檢測類型不為空
    if not rule.detection_types:
        raise HTTPException(status_code=400, detail="detection_types cannot be empty")

    # 建立規則
    db_rule = DetectionRule(
        rule_id=rule.rule_id,
        name=rule.name,
        description=rule.description,
        enabled=rule.enabled,
        stream_source_type=rule.stream_source_type,
        stream_source_ids=rule.stream_source_ids,
        person_ids=rule.person_ids,
        detection_types=[dt.value for dt in rule.detection_types],
        confidence_threshold=rule.confidence_threshold,
        time_threshold=rule.time_threshold,
        notification_enabled=rule.notification_enabled,
        notification_config=rule.notification_config,
        schedule_enabled=rule.schedule_enabled,
        schedule_config=rule.schedule_config,
        priority=rule.priority
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    logger.info(f"Created detection rule: {rule.rule_id} - {rule.name}")
    return db_rule


@router.put("/{rule_id}", response_model=DetectionRuleResponse)
def update_rule(
    rule_id: str,
    rule_update: DetectionRuleUpdate,
    db: Session = Depends(get_db)
):
    """
    更新檢測規則

    - **rule_id**: 規則ID
    """
    rule = db.query(DetectionRule).filter(DetectionRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    # 更新欄位
    update_data = rule_update.model_dump(exclude_unset=True)

    # 處理detection_types
    if 'detection_types' in update_data and update_data['detection_types']:
        update_data['detection_types'] = [dt.value for dt in update_data['detection_types']]

    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)

    logger.info(f"Updated detection rule: {rule_id}")
    return rule


@router.delete("/{rule_id}", response_model=MessageResponse)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    """
    刪除檢測規則

    - **rule_id**: 規則ID
    """
    rule = db.query(DetectionRule).filter(DetectionRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    db.delete(rule)
    db.commit()

    logger.info(f"Deleted detection rule: {rule_id}")
    return MessageResponse(message="Detection rule deleted successfully")


@router.post("/{rule_id}/enable", response_model=DetectionRuleResponse)
def enable_rule(rule_id: str, db: Session = Depends(get_db)):
    """
    啟用檢測規則

    - **rule_id**: 規則ID
    """
    rule = db.query(DetectionRule).filter(DetectionRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    rule.enabled = True
    db.commit()
    db.refresh(rule)

    logger.info(f"Enabled detection rule: {rule_id}")
    return rule


@router.post("/{rule_id}/disable", response_model=DetectionRuleResponse)
def disable_rule(rule_id: str, db: Session = Depends(get_db)):
    """
    停用檢測規則

    - **rule_id**: 規則ID
    """
    rule = db.query(DetectionRule).filter(DetectionRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    rule.enabled = False
    db.commit()
    db.refresh(rule)

    logger.info(f"Disabled detection rule: {rule_id}")
    return rule


@router.post("/{rule_id}/test")
async def test_rule(rule_id: str, db: Session = Depends(get_db)):
    """
    測試檢測規則

    - **rule_id**: 規則ID

    測試規則配置是否正確，並返回會被此規則匹配的條件
    """
    rule = db.query(DetectionRule).filter(DetectionRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Detection rule not found")

    from api.models import StreamSource, Person

    # 檢查規則會應用到哪些影像來源
    matched_streams = []
    if rule.stream_source_ids:
        # 有指定特定來源
        matched_streams = db.query(StreamSource).filter(
            StreamSource.stream_id.in_(rule.stream_source_ids)
        ).all()
    elif rule.stream_source_type:
        # 指定類型
        matched_streams = db.query(StreamSource).filter(
            StreamSource.stream_type == rule.stream_source_type
        ).all()
    else:
        # 所有來源
        matched_streams = db.query(StreamSource).all()

    # 檢查規則會應用到哪些人員
    matched_persons = []
    if rule.person_ids:
        matched_persons = db.query(Person).filter(
            Person.person_id.in_(rule.person_ids)
        ).all()
    else:
        matched_persons = db.query(Person).all()

    return {
        "rule_id": rule_id,
        "rule_name": rule.name,
        "enabled": rule.enabled,
        "matched_streams": [
            {"stream_id": s.stream_id, "name": s.name, "type": s.stream_type}
            for s in matched_streams
        ],
        "matched_persons": [
            {"person_id": p.person_id, "name": p.name}
            for p in matched_persons
        ] if rule.detection_types and "face" in rule.detection_types else None,
        "detection_types": rule.detection_types,
        "confidence_threshold": rule.confidence_threshold,
        "notification_enabled": rule.notification_enabled,
        "schedule_enabled": rule.schedule_enabled
    }


@router.get("/statistics/summary")
def get_rule_statistics(db: Session = Depends(get_db)):
    """
    取得規則統計資訊
    """
    from sqlalchemy import func

    total = db.query(DetectionRule).count()
    enabled = db.query(DetectionRule).filter(DetectionRule.enabled == True).count()
    disabled = db.query(DetectionRule).filter(DetectionRule.enabled == False).count()

    # 按檢測類型統計
    # 注意: 這是簡化版本，實際需要更複雜的查詢來處理JSON數組
    rules = db.query(DetectionRule).all()
    detection_type_count = {}
    for rule in rules:
        if rule.detection_types:
            for dt in rule.detection_types:
                detection_type_count[dt] = detection_type_count.get(dt, 0) + 1

    return {
        "total_rules": total,
        "enabled_rules": enabled,
        "disabled_rules": disabled,
        "by_detection_type": detection_type_count
    }


@router.get("/templates/list")
def list_rule_templates():
    """
    取得預設規則範本列表
    """
    templates = [
        {
            "template_id": "helmet_detection",
            "name": "安全帽檢測規則",
            "description": "檢測人員是否佩戴安全帽",
            "detection_types": ["helmet"],
            "recommended_confidence": 0.75,
            "use_cases": ["工廠", "建築工地", "倉庫"]
        },
        {
            "template_id": "drowsiness_detection",
            "name": "瞌睡檢測規則",
            "description": "檢測駕駛或操作員瞌睡狀態",
            "detection_types": ["drowsiness"],
            "recommended_confidence": 0.7,
            "recommended_time_threshold": 3.0,
            "use_cases": ["車輛", "控制室", "監控中心"]
        },
        {
            "template_id": "face_recognition",
            "name": "人臉識別規則",
            "description": "識別和記錄人員身份",
            "detection_types": ["face"],
            "recommended_confidence": 0.6,
            "use_cases": ["門禁", "考勤", "安全監控"]
        },
        {
            "template_id": "comprehensive",
            "name": "綜合檢測規則",
            "description": "同時進行多種檢測",
            "detection_types": ["helmet", "drowsiness", "face"],
            "recommended_confidence": 0.7,
            "use_cases": ["全方位監控"]
        }
    ]

    return {"templates": templates}


@router.post("/templates/{template_id}/apply")
def apply_rule_template(
    template_id: str,
    rule_id: str,
    name: str,
    stream_source_ids: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    應用規則範本快速創建規則

    - **template_id**: 範本ID
    - **rule_id**: 新規則ID
    - **name**: 新規則名稱
    - **stream_source_ids**: 要應用的影像來源ID列表
    """
    # 範本配置
    templates_config = {
        "helmet_detection": {
            "detection_types": ["helmet"],
            "confidence_threshold": 0.75,
            "description": "檢測人員是否佩戴安全帽"
        },
        "drowsiness_detection": {
            "detection_types": ["drowsiness"],
            "confidence_threshold": 0.7,
            "time_threshold": 3.0,
            "description": "檢測駕駛或操作員瞌睡狀態"
        },
        "face_recognition": {
            "detection_types": ["face"],
            "confidence_threshold": 0.6,
            "description": "識別和記錄人員身份"
        },
        "comprehensive": {
            "detection_types": ["helmet", "drowsiness", "face"],
            "confidence_threshold": 0.7,
            "description": "綜合檢測規則"
        }
    }

    if template_id not in templates_config:
        raise HTTPException(status_code=404, detail="Template not found")

    config = templates_config[template_id]

    # 建立規則
    rule = DetectionRule(
        rule_id=rule_id,
        name=name,
        description=config["description"],
        enabled=True,
        stream_source_ids=stream_source_ids,
        detection_types=config["detection_types"],
        confidence_threshold=config["confidence_threshold"],
        time_threshold=config.get("time_threshold"),
        notification_enabled=True,
        priority=0
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    logger.info(f"Applied template {template_id} to create rule: {rule_id}")
    return rule
