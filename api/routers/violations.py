"""
Violation Records API Routes
違規記錄API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from api.database import get_db
from api.models import Violation
from api.schemas import (
    ViolationQuery, ViolationResponse, ViolationUpdate,
    ViolationStatistics, MessageResponse, ViolationStatus
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
def list_violations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = None,
    violation_type: Optional[str] = None,
    person_id: Optional[str] = None,
    rule_id: Optional[str] = None,
    status: Optional[ViolationStatus] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    查詢違規記錄

    - **skip**: 跳過筆數
    - **limit**: 限制筆數
    - **camera_id**: 篩選攝影機ID
    - **violation_type**: 篩選違規類型
    - **person_id**: 篩選人員ID
    - **rule_id**: 篩選規則ID
    - **status**: 篩選狀態
    - **start_time**: 起始時間
    - **end_time**: 結束時間
    """
    query = db.query(Violation)

    if camera_id:
        query = query.filter(Violation.camera_id == camera_id)
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)
    if person_id:
        query = query.filter(Violation.person_id == person_id)
    if rule_id:
        query = query.filter(Violation.rule_id == rule_id)
    if status:
        query = query.filter(Violation.status == status)
    if start_time:
        query = query.filter(Violation.timestamp >= start_time)
    if end_time:
        query = query.filter(Violation.timestamp <= end_time)

    violations = query.order_by(Violation.timestamp.desc()).offset(skip).limit(limit).all()

    return {
        "status": "success",
        "data": {
            "msg": "success",
            "list": violations
        }
    }


@router.get("/{violation_id}", response_model=ViolationResponse)
def get_violation(violation_id: str, db: Session = Depends(get_db)):
    """
    取得特定違規記錄

    - **violation_id**: 違規ID
    """
    violation = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violation


@router.put("/{violation_id}", response_model=ViolationResponse)
def update_violation(
    violation_id: str,
    violation_update: ViolationUpdate,
    db: Session = Depends(get_db)
):
    """
    更新違規記錄

    - **violation_id**: 違規ID
    - **status**: 狀態 (new/acknowledged/resolved)
    - **acknowledged_by**: 確認人員
    - **resolved_by**: 處理人員
    - **notes**: 備註
    """
    violation = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    # 更新欄位
    update_data = violation_update.model_dump(exclude_unset=True)

    # 處理狀態變更時間
    if 'status' in update_data:
        if update_data['status'] == ViolationStatus.ACKNOWLEDGED and not violation.acknowledged_at:
            violation.acknowledged_at = datetime.now()
        elif update_data['status'] == ViolationStatus.RESOLVED and not violation.resolved_at:
            violation.resolved_at = datetime.now()

    for field, value in update_data.items():
        setattr(violation, field, value)

    db.commit()
    db.refresh(violation)

    logger.info(f"Updated violation: {violation_id}")
    return violation


@router.post("/{violation_id}/acknowledge", response_model=ViolationResponse)
def acknowledge_violation(
    violation_id: str,
    acknowledged_by: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    確認違規

    - **violation_id**: 違規ID
    - **acknowledged_by**: 確認人員
    - **notes**: 備註
    """
    violation = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    violation.status = ViolationStatus.ACKNOWLEDGED
    violation.acknowledged_by = acknowledged_by
    violation.acknowledged_at = datetime.now()
    if notes:
        violation.notes = notes

    db.commit()
    db.refresh(violation)

    logger.info(f"Acknowledged violation: {violation_id} by {acknowledged_by}")
    return violation


@router.post("/{violation_id}/resolve", response_model=ViolationResponse)
def resolve_violation(
    violation_id: str,
    resolved_by: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    處理完成違規

    - **violation_id**: 違規ID
    - **resolved_by**: 處理人員
    - **notes**: 處理備註
    """
    violation = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    violation.status = ViolationStatus.RESOLVED
    violation.resolved_by = resolved_by
    violation.resolved_at = datetime.now()
    if notes:
        violation.notes = notes

    db.commit()
    db.refresh(violation)

    logger.info(f"Resolved violation: {violation_id} by {resolved_by}")
    return violation


@router.delete("/{violation_id}", response_model=MessageResponse)
def delete_violation(violation_id: str, db: Session = Depends(get_db)):
    """
    刪除違規記錄

    - **violation_id**: 違規ID
    """
    violation = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    db.delete(violation)
    db.commit()

    logger.info(f"Deleted violation: {violation_id}")
    return MessageResponse(message="Violation deleted successfully")


@router.get("/statistics/summary", response_model=ViolationStatistics)
def get_violation_statistics(
    days: int = Query(7, ge=1, le=365),
    camera_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    取得違規統計資訊

    - **days**: 統計天數
    - **camera_id**: 篩選特定攝影機
    """
    from sqlalchemy import func

    # 計算時間範圍
    start_time = datetime.now() - timedelta(days=days)

    # 基礎查詢
    query = db.query(Violation).filter(Violation.timestamp >= start_time)
    if camera_id:
        query = query.filter(Violation.camera_id == camera_id)

    # 總違規數
    total_violations = query.count()

    # 按類型統計
    violations_by_type = {}
    type_stats = query.with_entities(
        Violation.violation_type,
        func.count(Violation.id)
    ).group_by(Violation.violation_type).all()
    for vtype, count in type_stats:
        violations_by_type[vtype] = count

    # 按攝影機統計
    violations_by_camera = {}
    camera_stats = query.with_entities(
        Violation.camera_id,
        func.count(Violation.id)
    ).group_by(Violation.camera_id).all()
    for cam_id, count in camera_stats:
        violations_by_camera[cam_id] = count

    # 按人員統計
    violations_by_person = {}
    person_stats = query.filter(Violation.person_id.isnot(None)).with_entities(
        Violation.person_id,
        func.count(Violation.id)
    ).group_by(Violation.person_id).all()
    for person_id, count in person_stats:
        violations_by_person[person_id] = count

    # 按狀態統計
    violations_by_status = {}
    status_stats = query.with_entities(
        Violation.status,
        func.count(Violation.id)
    ).group_by(Violation.status).all()
    for status, count in status_stats:
        violations_by_status[status] = count

    return ViolationStatistics(
        total_violations=total_violations,
        violations_by_type=violations_by_type,
        violations_by_camera=violations_by_camera,
        violations_by_person=violations_by_person,
        violations_by_status=violations_by_status,
        period_days=days
    )


@router.get("/statistics/timeline")
def get_violation_timeline(
    days: int = Query(7, ge=1, le=365),
    camera_id: Optional[str] = None,
    violation_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    取得違規時間線統計

    - **days**: 統計天數
    - **camera_id**: 篩選特定攝影機
    - **violation_type**: 篩選違規類型
    """
    from sqlalchemy import func, cast, Date

    start_time = datetime.now() - timedelta(days=days)

    query = db.query(Violation).filter(Violation.timestamp >= start_time)
    if camera_id:
        query = query.filter(Violation.camera_id == camera_id)
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)

    # 按日期統計
    daily_stats = query.with_entities(
        cast(Violation.timestamp, Date).label('date'),
        func.count(Violation.id).label('count')
    ).group_by(cast(Violation.timestamp, Date)).all()

    timeline = [
        {
            "date": str(date),
            "count": count
        }
        for date, count in daily_stats
    ]

    return {
        "period_days": days,
        "timeline": timeline
    }


@router.post("/cleanup")
def cleanup_old_violations(
    days: int = Query(30, ge=1),
    dry_run: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    清理舊的違規記錄

    - **days**: 保留天數 (刪除超過此天數的記錄)
    - **dry_run**: 是否為測試模式 (不實際刪除)
    """
    cutoff_time = datetime.now() - timedelta(days=days)

    query = db.query(Violation).filter(Violation.timestamp < cutoff_time)
    count = query.count()

    if not dry_run:
        query.delete()
        db.commit()
        logger.info(f"Cleaned up {count} violations older than {days} days")
        message = f"Deleted {count} violations"
    else:
        message = f"Found {count} violations that would be deleted"

    return {
        "message": message,
        "count": count,
        "cutoff_date": cutoff_time.isoformat(),
        "dry_run": dry_run
    }
