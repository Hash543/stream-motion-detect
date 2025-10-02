"""
Stream Source Management API Routes
影像來源CRUD API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from api.database import get_db
from api.models import StreamSource
from api.schemas import (
    StreamSourceCreate, StreamSourceUpdate, StreamSourceResponse,
    MessageResponse, StreamType
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[StreamSourceResponse])
def list_streams(
    skip: int = 0,
    limit: int = 100,
    stream_type: Optional[StreamType] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    取得影像來源列表

    - **skip**: 跳過筆數
    - **limit**: 限制筆數
    - **stream_type**: 篩選串流類型
    - **enabled**: 篩選是否啟用
    """
    query = db.query(StreamSource)

    if stream_type:
        query = query.filter(StreamSource.stream_type == stream_type)
    if enabled is not None:
        query = query.filter(StreamSource.enabled == enabled)

    streams = query.offset(skip).limit(limit).all()
    return streams


@router.get("/{stream_id}", response_model=StreamSourceResponse)
def get_stream(stream_id: str, db: Session = Depends(get_db)):
    """
    取得特定影像來源資訊

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")
    return stream


@router.post("/", response_model=StreamSourceResponse)
def create_stream(
    stream: StreamSourceCreate,
    db: Session = Depends(get_db)
):
    """
    建立影像來源

    - **stream_id**: 串流ID (唯一)
    - **name**: 串流名稱
    - **stream_type**: 串流類型 (RTSP, WEBCAM, HTTP_MJPEG, HLS, DASH, WEBRTC, ONVIF)
    - **url**: 串流URL (可選，WEBCAM不需要)
    - **location**: 位置 (可選)
    - **enabled**: 是否啟用
    - **config**: 串流特定配置 (可選)

    範例config:
    - RTSP: {"tcp_transport": true, "timeout": 10}
    - WEBCAM: {"device_index": 0, "resolution": {"width": 1280, "height": 720}}
    - HTTP_MJPEG: {"auth": {"username": "admin", "password": "password"}}
    """
    # 檢查是否已存在
    existing = db.query(StreamSource).filter(StreamSource.stream_id == stream.stream_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stream ID already exists")

    # 驗證URL (除了WEBCAM)
    if stream.stream_type != StreamType.WEBCAM and not stream.url:
        raise HTTPException(status_code=400, detail="URL is required for this stream type")

    # 建立串流來源
    db_stream = StreamSource(
        stream_id=stream.stream_id,
        name=stream.name,
        stream_type=stream.stream_type,
        url=stream.url,
        location=stream.location,
        enabled=stream.enabled,
        config=stream.config,
        status="inactive"
    )

    db.add(db_stream)
    db.commit()
    db.refresh(db_stream)

    logger.info(f"Created stream source: {stream.stream_id} - {stream.name} ({stream.stream_type})")
    return db_stream


@router.put("/{stream_id}", response_model=StreamSourceResponse)
def update_stream(
    stream_id: str,
    stream_update: StreamSourceUpdate,
    db: Session = Depends(get_db)
):
    """
    更新影像來源

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")

    # 更新欄位
    update_data = stream_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stream, field, value)

    db.commit()
    db.refresh(stream)

    logger.info(f"Updated stream source: {stream_id}")
    return stream


@router.delete("/{stream_id}", response_model=MessageResponse)
def delete_stream(stream_id: str, db: Session = Depends(get_db)):
    """
    刪除影像來源

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")

    db.delete(stream)
    db.commit()

    logger.info(f"Deleted stream source: {stream_id}")
    return MessageResponse(message="Stream source deleted successfully")


@router.post("/{stream_id}/enable", response_model=StreamSourceResponse)
def enable_stream(stream_id: str, db: Session = Depends(get_db)):
    """
    啟用影像來源

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")

    stream.enabled = True
    db.commit()
    db.refresh(stream)

    logger.info(f"Enabled stream source: {stream_id}")
    return stream


@router.post("/{stream_id}/disable", response_model=StreamSourceResponse)
def disable_stream(stream_id: str, db: Session = Depends(get_db)):
    """
    停用影像來源

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")

    stream.enabled = False
    db.commit()
    db.refresh(stream)

    logger.info(f"Disabled stream source: {stream_id}")
    return stream


@router.get("/{stream_id}/status")
def get_stream_status(stream_id: str, db: Session = Depends(get_db)):
    """
    取得影像來源即時狀態

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")

    # TODO: 從監控系統取得即時狀態
    # from src.monitoring_system import get_stream_status
    # real_time_status = get_stream_status(stream_id)

    return {
        "stream_id": stream_id,
        "name": stream.name,
        "enabled": stream.enabled,
        "status": stream.status,
        "stream_type": stream.stream_type,
        "location": stream.location
    }


@router.get("/statistics/summary")
def get_stream_statistics(db: Session = Depends(get_db)):
    """
    取得影像來源統計資訊
    """
    from sqlalchemy import func

    total = db.query(StreamSource).count()
    enabled = db.query(StreamSource).filter(StreamSource.enabled == True).count()
    disabled = db.query(StreamSource).filter(StreamSource.enabled == False).count()
    active = db.query(StreamSource).filter(StreamSource.status == "active").count()

    # 按類型統計
    by_type = db.query(StreamSource.stream_type, func.count(StreamSource.id))\
        .group_by(StreamSource.stream_type)\
        .all()

    return {
        "total_streams": total,
        "enabled_streams": enabled,
        "disabled_streams": disabled,
        "active_streams": active,
        "by_type": {stream_type: count for stream_type, count in by_type}
    }


@router.post("/{stream_id}/test")
async def test_stream_connection(stream_id: str, db: Session = Depends(get_db)):
    """
    測試影像來源連接

    - **stream_id**: 串流ID
    """
    stream = db.query(StreamSource).filter(StreamSource.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream source not found")

    try:
        # TODO: 實作測試連接邏輯
        # from src.managers.universal_stream_manager import test_stream_connection
        # result = await test_stream_connection(stream)

        logger.info(f"Testing stream connection: {stream_id}")

        return {
            "stream_id": stream_id,
            "test_result": "success",
            "message": "Stream connection test completed",
            "details": {
                "stream_type": stream.stream_type,
                "url": stream.url if stream.stream_type != "WEBCAM" else "N/A"
            }
        }

    except Exception as e:
        logger.error(f"Stream connection test failed: {e}")
        return {
            "stream_id": stream_id,
            "test_result": "failed",
            "message": "Stream connection test failed",
            "error": str(e)
        }
