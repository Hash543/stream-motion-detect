"""
GPS808 API Router
GPS808 位置追蹤 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from api.database import get_db
from api.models import GPS808

router = APIRouter()


# Pydantic Models
class LocationData(BaseModel):
    warnBit: int
    statusBit: int
    latitude: int
    longitude: int
    lat: float
    lng: float
    altitude: int
    speed: float
    speedKph: float
    direction: int
    deviceTime: str


class GPS808Item(BaseModel):
    deviceId: str
    mobileNo: str
    plateNo: str
    protocolVersion: int
    location: LocationData


class GPS808BulkCreate(BaseModel):
    data: List[GPS808Item]


class GPS808Response(BaseModel):
    id: int
    device_id: str
    mobile_no: Optional[str]
    plate_no: Optional[str]
    protocol_version: Optional[int]
    warn_bit: Optional[int]
    status_bit: Optional[int]
    latitude: Optional[int]
    longitude: Optional[int]
    lat: Optional[float]
    lng: Optional[float]
    altitude: Optional[int]
    speed: Optional[float]
    speed_kph: Optional[float]
    direction: Optional[int]
    device_time: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/list", response_model=List[GPS808Response])
async def get_gps808_list(db: Session = Depends(get_db)):
    """取得所有 GPS808 資料"""
    try:
        gps_list = db.query(GPS808).all()
        return gps_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=dict)
async def add_gps808_bulk(data: GPS808BulkCreate, db: Session = Depends(get_db)):
    """批次新增 GPS808 資料"""
    try:
        created_count = 0

        for item in data.data:
            # 解析設備時間
            try:
                device_time = datetime.strptime(item.location.deviceTime, "%Y-%m-%d %H:%M:%S")
            except:
                device_time = datetime.now()

            # 建立 GPS808 記錄
            gps_record = GPS808(
                device_id=item.deviceId,
                mobile_no=item.mobileNo,
                plate_no=item.plateNo,
                protocol_version=item.protocolVersion,
                warn_bit=item.location.warnBit,
                status_bit=item.location.statusBit,
                latitude=item.location.latitude,
                longitude=item.location.longitude,
                lat=item.location.lat,
                lng=item.location.lng,
                altitude=item.location.altitude,
                speed=item.location.speed,
                speed_kph=item.location.speedKph,
                direction=item.location.direction,
                device_time=device_time,
                created_at=datetime.now()
            )
            db.add(gps_record)
            created_count += 1

        db.commit()

        return {
            "result": "success",
            "message": f"成功新增 {created_count} 筆 GPS808 資料"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/{device_id}", response_model=GPS808Response)
async def get_latest_gps808(device_id: str, db: Session = Depends(get_db)):
    """取得指定設備的最新 GPS808 資料"""
    try:
        gps_record = db.query(GPS808).filter(
            GPS808.device_id == device_id
        ).order_by(GPS808.created_at.desc()).first()

        if not gps_record:
            raise HTTPException(status_code=404, detail="找不到該設備的 GPS 資料")

        return gps_record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/{device_id}", response_model=List[GPS808Response])
async def get_gps808_by_device(
    device_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """取得指定設備的 GPS808 歷史資料"""
    try:
        gps_list = db.query(GPS808).filter(
            GPS808.device_id == device_id
        ).order_by(GPS808.created_at.desc()).limit(limit).all()

        return gps_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
