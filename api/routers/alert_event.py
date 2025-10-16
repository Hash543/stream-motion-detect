"""
警報事件 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import base64
from pathlib import Path

from api.database import get_db
from api.models import AlertEvent, AlertEventAssignUser, User
from api.routers.auth import verify_token

router = APIRouter(prefix="/api/alertEvent", tags=["AlertEvent"])

# 上傳目錄
UPLOAD_DIR = os.getenv("UPLOAD_PUBLIC_DIR", "./public/uploads")
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


class AlertEventCreate(BaseModel):
    camera_id: Optional[str] = None
    code: Optional[int] = None
    type: Optional[int] = None  # 7: type code
    length: Optional[int] = None
    area: Optional[int] = None
    time: Optional[str] = None  # Format: "2025-08-31 13:50:43"
    severity: Optional[str] = None  # 中等, 高等, 低等
    image: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = ""  # If empty, auto-fetch from lat/lng
    order_no: Optional[str] = None
    uIds: Optional[List[int]] = None  # User IDs for assignment
    oIds: Optional[List[int]] = None  # Organization IDs
    report_status: Optional[int] = None  # 1:未處理, 2:處理中, 3:已處理


class AlertEventResponse(BaseModel):
    id: int
    camera_id: Optional[str]
    code: Optional[str]
    type: Optional[str]
    severity: Optional[str]
    time: Optional[datetime]
    report_status: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/add")
async def add_alert_event(
    event: AlertEventCreate,
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    新增警報事件
    支持自動分配使用者和組織
    """
    event_data = event.dict(exclude={"uIds", "oIds"})

    # 如果 time 是字串，轉換為 datetime
    if isinstance(event_data.get('time'), str):
        try:
            event_data['time'] = datetime.strptime(event_data['time'], "%Y-%m-%d %H:%M:%S")
        except:
            event_data['time'] = None

    # TODO: 如果 address 為空且有經緯度，自動解析地址
    # if not event_data.get('address') and event_data.get('lat') and event_data.get('lng'):
    #     event_data['address'] = reverse_geocode(event_data['lat'], event_data['lng'])

    # 建立 alert_event
    new_event = AlertEvent(**event_data)
    db.add(new_event)
    db.flush()  # Get ID without committing

    # 如果提供了 uIds, oIds, report_status，自動進行分配
    if event.uIds and event.oIds is not None and event.report_status:
        # 更新 report_status
        new_event.report_status = event.report_status

        # 分配給使用者
        for user_id in event.uIds:
            assignment = AlertEventAssignUser(
                ae_id=new_event.id,
                user_id=user_id,
                status=event.report_status
            )
            db.add(assignment)

    db.commit()
    db.refresh(new_event)

    return {
        "status": "success",
        "data": {
            "id": new_event.id,
            "created_at": new_event.created_at
        }
    }


@router.get("/search")
async def search_alert_events(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    camera_id: Optional[str] = None,
    type: Optional[str] = None,
    severity: Optional[str] = None,
    report_status: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    搜尋警報事件
    """
    query = db.query(AlertEvent)

    # 篩選條件
    if camera_id:
        query = query.filter(AlertEvent.camera_id == camera_id)
    if type:
        query = query.filter(AlertEvent.type == type)
    if severity:
        query = query.filter(AlertEvent.severity == severity)
    if report_status is not None:
        query = query.filter(AlertEvent.report_status == report_status)
    if start_date:
        query = query.filter(AlertEvent.created_at >= start_date)
    if end_date:
        query = query.filter(AlertEvent.created_at <= end_date)

    # 總數
    total = query.count()

    # 分頁
    offset = (page - 1) * pageSize
    events = query.order_by(AlertEvent.created_at.desc()).offset(offset).limit(pageSize).all()

    return {
        "status": "success",
        "data": {
            "msg": "success",
            "list": events,
            "total": total,
            "page": page,
            "pageSize": pageSize
        }
    }


@router.get("/single")
async def get_alert_event(
    id: int = Query(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    取得單一警報事件
    """
    event = db.query(AlertEvent).filter(AlertEvent.id == id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")

    return {
        "status": "success",
        "data": event
    }


@router.delete("/delete")
async def delete_alert_event(
    id: int = Query(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    刪除警報事件
    """
    event = db.query(AlertEvent).filter(AlertEvent.id == id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")

    db.delete(event)
    db.commit()

    return {
        "status": "success",
        "message": "Alert event deleted"
    }


@router.delete("/batchDelete")
async def batch_delete_alert_events(
    ids: List[int],
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    批次刪除警報事件
    """
    db.query(AlertEvent).filter(AlertEvent.id.in_(ids)).delete(synchronize_session=False)
    db.commit()

    return {
        "status": "success",
        "message": f"Deleted {len(ids)} alert events"
    }


@router.post("/assignWork")
async def assign_work(
    ae_id: int = Form(...),
    user_ids: List[int] = Form(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    分配工作給使用者
    """
    # 刪除舊的分配記錄
    db.query(AlertEventAssignUser).filter(AlertEventAssignUser.ae_id == ae_id).delete()

    # 新增分配記錄
    for user_id in user_ids:
        assignment = AlertEventAssignUser(ae_id=ae_id, user_id=user_id)
        db.add(assignment)

    # 更新警報事件狀態為處理中
    event = db.query(AlertEvent).filter(AlertEvent.id == ae_id).first()
    if event:
        event.report_status = 2  # 處理中

    db.commit()

    return {
        "status": "success",
        "message": "Work assigned successfully"
    }


@router.post("/saveNote")
async def save_note(
    id: int = Form(...),
    note: str = Form(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    儲存備註
    """
    event = db.query(AlertEvent).filter(AlertEvent.id == id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")

    event.note = note
    db.commit()

    return {
        "status": "success",
        "message": "Note saved"
    }


@router.get("/trend")
async def get_trend_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = Query("hour", regex="^(hour|day|week|month)$"),
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    取得趨勢數據
    """
    # 預設時間範圍
    if not start_date:
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
    if not end_date:
        end_date = datetime.now().isoformat()

    # 根據時間間隔設定格式 (PostgreSQL)
    format_map = {
        "hour": "YYYY-MM-DD HH24:00:00",
        "day": "YYYY-MM-DD",
        "week": "IYYY-IW",  # ISO week
        "month": "YYYY-MM"
    }
    pg_format = format_map[interval]

    # 查詢數據 (使用 PostgreSQL 的 to_char)
    results = db.query(
        func.to_char(AlertEvent.created_at, pg_format).label("time_group"),
        func.count(AlertEvent.id).label("count")
    ).filter(
        AlertEvent.created_at.between(start_date, end_date)
    ).group_by("time_group").all()

    return {
        "status": "success",
        "data": [{"time": r.time_group, "count": r.count} for r in results]
    }


@router.get("/overview")
async def get_overview(
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    取得總覽統計
    """
    total = db.query(func.count(AlertEvent.id)).scalar()
    pending = db.query(func.count(AlertEvent.id)).filter(AlertEvent.report_status == 1).scalar()
    processing = db.query(func.count(AlertEvent.id)).filter(AlertEvent.report_status == 2).scalar()
    completed = db.query(func.count(AlertEvent.id)).filter(AlertEvent.report_status == 3).scalar()

    # 今日新增
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(func.count(AlertEvent.id)).filter(AlertEvent.created_at >= today).scalar()

    return {
        "status": "success",
        "data": {
            "total": total or 0,
            "pending": pending or 0,
            "processing": processing or 0,
            "completed": completed or 0,
            "today": today_count or 0
        }
    }


@router.get("/assignedAlertEvents")
async def get_assigned_alert_events(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    """
    取得分配給使用者的警報事件
    """
    # 如果沒有指定使用者，使用當前登入使用者
    if not user_id:
        user_id = token_data.get("data")

    assignments = db.query(AlertEventAssignUser).filter(
        AlertEventAssignUser.user_id == user_id
    ).all()

    event_ids = [a.ae_id for a in assignments]
    events = db.query(AlertEvent).filter(AlertEvent.id.in_(event_ids)).all()

    return {
        "status": "success",
        "data": {
            "msg": "success",
            "list": events
        }
    }
