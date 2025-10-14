"""
Positions API Router
職位管理 API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from math import ceil

from api.database import get_db
from api.models import Positions

router = APIRouter()


# Pydantic Models
class PositionCreate(BaseModel):
    posi_name: str
    posi_level: Optional[int] = None
    posi_code: Optional[str] = None
    org_id: Optional[int] = None
    created_id: Optional[int] = None


class PositionUpdate(BaseModel):
    id: int
    posi_name: str
    posi_level: Optional[int] = None
    posi_code: Optional[str] = None
    org_id: Optional[int] = None
    updated_id: Optional[int] = None


class PositionResponse(BaseModel):
    id: int
    posi_name: str
    posi_level: Optional[int]
    posi_code: Optional[str]
    org_id: Optional[int]
    created_id: Optional[int]
    created_at: datetime
    updated_id: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/list", response_model=dict)
async def get_positions_list(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """取得職位列表（分頁）"""
    try:
        # 計算偏移量
        offset = (page - 1) * size

        # 查詢總數
        total_count = db.query(Positions).count()

        # 查詢分頁資料
        positions = db.query(Positions).offset(offset).limit(size).all()

        # 計算總頁數
        total_pages = ceil(total_count / size)

        # 格式化結果
        data = []
        for pos in positions:
            data.append({
                "id": pos.id,
                "posi_name": pos.posi_name,
                "posi_level": pos.posi_level,
                "posi_code": pos.posi_code,
                "org_id": pos.org_id,
                "created_id": pos.created_id,
                "created_at": pos.created_at.isoformat() if pos.created_at else None,
                "updated_id": pos.updated_id,
                "updated_at": pos.updated_at.isoformat() if pos.updated_at else None
            })

        return {
            "result": "success",
            "data": data,
            "totalPages": total_pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/level", response_model=dict)
async def get_positions_level(db: Session = Depends(get_db)):
    """取得所有職位（依 level 排序）"""
    try:
        positions = db.query(Positions).order_by(Positions.posi_level).all()

        data = []
        for pos in positions:
            data.append({
                "id": pos.id,
                "posi_name": pos.posi_name,
                "posi_level": pos.posi_level,
                "posi_code": pos.posi_code,
                "org_id": pos.org_id,
                "created_id": pos.created_id,
                "created_at": pos.created_at.isoformat() if pos.created_at else None,
                "updated_id": pos.updated_id,
                "updated_at": pos.updated_at.isoformat() if pos.updated_at else None
            })

        return {"result": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=dict)
async def add_position(position_data: PositionCreate, db: Session = Depends(get_db)):
    """新增職位"""
    try:
        new_position = Positions(
            posi_name=position_data.posi_name,
            posi_level=position_data.posi_level,
            posi_code=position_data.posi_code,
            org_id=position_data.org_id,
            created_id=position_data.created_id,
            created_at=datetime.now(),
            updated_id=position_data.created_id,
            updated_at=datetime.now()
        )
        db.add(new_position)
        db.commit()
        db.refresh(new_position)

        result = {
            "id": new_position.id,
            "posi_name": new_position.posi_name,
            "posi_level": new_position.posi_level,
            "posi_code": new_position.posi_code,
            "org_id": new_position.org_id,
            "created_id": new_position.created_id,
            "created_at": new_position.created_at.isoformat() if new_position.created_at else None,
            "updated_id": new_position.updated_id,
            "updated_at": new_position.updated_at.isoformat() if new_position.updated_at else None
        }

        return {"result": "success", "data": result}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update", response_model=dict)
async def update_position(position_data: PositionUpdate, db: Session = Depends(get_db)):
    """更新職位"""
    try:
        position = db.query(Positions).filter(Positions.id == position_data.id).first()

        if not position:
            return {"result": "error", "message": "找不到資料"}

        # 更新職位資訊
        position.posi_name = position_data.posi_name
        position.posi_level = position_data.posi_level
        position.posi_code = position_data.posi_code
        position.org_id = position_data.org_id
        position.updated_id = position_data.updated_id
        position.updated_at = datetime.now()

        db.commit()
        db.refresh(position)

        result = {
            "id": position.id,
            "posi_name": position.posi_name,
            "posi_level": position.posi_level,
            "posi_code": position.posi_code,
            "org_id": position.org_id,
            "created_id": position.created_id,
            "created_at": position.created_at.isoformat() if position.created_at else None,
            "updated_id": position.updated_id,
            "updated_at": position.updated_at.isoformat() if position.updated_at else None
        }

        return {"result": "success", "data": result}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{id}", response_model=dict)
async def delete_position(id: int, db: Session = Depends(get_db)):
    """刪除職位"""
    try:
        position = db.query(Positions).filter(Positions.id == id).first()

        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        db.delete(position)
        db.commit()

        return {"result": "success", "data": {"id": id}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
