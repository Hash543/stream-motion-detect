"""
Dashboard API Router
儀表板 API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from api.database import get_db
from api.models import AlertEvent, InspectProperty, RelInspectProperty

router = APIRouter()


class TrendDataResponse(BaseModel):
    time: str
    count: int


def format_date_by_range_type(date: datetime, range_type: str) -> str:
    """根據時間區間類型格式化日期"""
    if range_type == "hour":
        return date.strftime("%Y/%m/%d %H:00:00")
    elif range_type == "day":
        return date.strftime("%Y/%m/%d 00:00:00")
    elif range_type == "month":
        return date.strftime("%Y/%m/01 00:00:00")
    return date.isoformat()


def get_interval_minutes(range_type: str) -> int:
    """根據時間區間類型取得間隔分鐘數"""
    if range_type == "hour":
        return 60
    elif range_type == "day":
        return 24 * 60
    elif range_type == "month":
        return 31 * 24 * 60
    return 60


@router.get("/-/overview", response_model=dict)
async def get_overview(db: Session = Depends(get_db)):
    """取得儀表板概覽數據"""
    try:
        # 取得告警數量
        alert_events_count = db.query(AlertEvent).count()
        alert_events_unhandled = db.query(AlertEvent).filter(AlertEvent.report_status == 1).count()
        alert_events_handling = db.query(AlertEvent).filter(AlertEvent.report_status == 2).count()
        alert_events_handled = db.query(AlertEvent).filter(AlertEvent.report_status == 3).count()

        # 取得今日建立的告警數量
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        alert_events_today_created = db.query(AlertEvent).filter(
            and_(
                AlertEvent.created_at >= today_start,
                AlertEvent.created_at <= today_end
            )
        ).count()

        # 取得設備資產數量
        equipment_assets_car_count = db.query(InspectProperty).filter(
            InspectProperty.prop_type == 1
        ).count()

        # 設備在線數量 (GPS + 攝像頭，狀態=1)
        equipment_assets_device_online = db.query(InspectProperty).filter(
            and_(
                InspectProperty.prop_type.in_([2, 3]),
                InspectProperty.status == 1
            )
        ).count()

        # 設備離線數量 (GPS + 攝像頭，狀態=2)
        equipment_assets_device_offline = db.query(InspectProperty).filter(
            and_(
                InspectProperty.prop_type.in_([2, 3]),
                InspectProperty.status == 2
            )
        ).count()

        # 未分配設備數量 (GPS + 攝像頭，沒有在 rel_inspect_property 中作為 device)
        # 查詢所有已分配的設備ID
        assigned_device_ids = db.query(RelInspectProperty.inspect_property_device_id).distinct().all()
        assigned_device_ids = [item[0] for item in assigned_device_ids if item[0] is not None]

        # 未分配 = 所有設備 - 已分配設備
        if assigned_device_ids:
            equipment_assets_device_unassign = db.query(InspectProperty).filter(
                and_(
                    InspectProperty.prop_type.in_([2, 3]),
                    ~InspectProperty.id.in_(assigned_device_ids)
                )
            ).count()
        else:
            equipment_assets_device_unassign = db.query(InspectProperty).filter(
                InspectProperty.prop_type.in_([2, 3])
            ).count()

        return {
            "alertEvent": {
                "all": alert_events_count,
                "unhandled": alert_events_unhandled,
                "handling": alert_events_handling,
                "handled": alert_events_handled,
                "todayCreated": alert_events_today_created
            },
            "EquipmentAsset": {
                "car": equipment_assets_car_count,
                "online": equipment_assets_device_online,
                "offline": equipment_assets_device_offline,
                "unassign": equipment_assets_device_unassign
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/-/trend/{type}", response_model=list)
async def get_trend_data(
    type: str,
    startTime: str = Query(..., description="開始時間"),
    endTime: str = Query(..., description="結束時間"),
    rangeType: str = Query(..., description="時間區間類型: hour, day, month"),
    db: Session = Depends(get_db)
):
    """取得告警事件時間區間趨勢資料"""
    try:
        # 驗證類型
        if type != "alert-event":
            raise HTTPException(status_code=400, detail="請提供正確的類型")

        # 驗證時間區間類型
        if rangeType not in ["hour", "day", "month"]:
            raise HTTPException(status_code=400, detail="請提供正確的時間區間類型")

        # 解析時間
        try:
            start_date = datetime.fromisoformat(startTime.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(endTime.replace('Z', '+00:00'))
        except:
            raise HTTPException(status_code=400, detail="時間格式錯誤")

        # 根據時間區間類型格式化 SQL 查詢
        if rangeType == "hour":
            time_format = func.date_format(AlertEvent.created_at, '%Y/%m/%d %H:00:00')
        elif rangeType == "day":
            time_format = func.date_format(AlertEvent.created_at, '%Y/%m/%d 00:00:00')
        else:  # month
            time_format = func.date_format(AlertEvent.created_at, '%Y/%m/01 00:00:00')

        # 查詢資料庫
        rows = db.query(
            time_format.label('time'),
            func.count(AlertEvent.id).label('count')
        ).filter(
            and_(
                AlertEvent.created_at >= start_date,
                AlertEvent.created_at <= end_date
            )
        ).group_by(time_format).all()

        # 建立結果字典以便快速查找
        result_dict = {row.time: row.count for row in rows}

        # 填充時間區間資料
        result = []
        current_date = start_date
        interval_minutes = get_interval_minutes(rangeType)

        while current_date <= end_date:
            formatted_date = format_date_by_range_type(current_date, rangeType)
            count = result_dict.get(formatted_date, 0)

            result.append({
                "time": formatted_date,
                "count": count
            })

            # 增加時間間隔
            current_date = current_date + timedelta(minutes=interval_minutes)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
