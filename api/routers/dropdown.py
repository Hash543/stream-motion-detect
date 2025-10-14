"""
Dropdown API Router
下拉選單 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from api.database import get_db
from api.models import SysParams, InspectProperty, Organization

router = APIRouter()


class DropdownOption(BaseModel):
    text: str
    value: int


@router.get("/{type}", response_model=List[DropdownOption])
async def get_dropdown_options(type: str, db: Session = Depends(get_db)):
    """取得下拉選單選項"""
    try:
        if type == "inspect_property_type":
            return get_inspect_property_type(db)
        elif type == "inspect_property_car":
            return get_inspect_property_car(db)
        elif type == "inspect_property_gps":
            return get_inspect_property_gps(db)
        elif type == "inspect_property_camera":
            return get_inspect_property_camera(db)
        elif type == "organization":
            return get_organization(db)
        else:
            raise HTTPException(status_code=400, detail="未知的下拉選單類型")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_inspect_property_type(db: Session) -> List[dict]:
    """取得設備類型下拉清單選項"""
    items = db.query(SysParams).filter(
        SysParams.param_type == "inspect_property_type"
    ).all()

    result = []
    for item in items:
        # 使用 pname 作為顯示文字，ivalue 作為值
        result.append({
            "text": item.pname if item.pname else item.pvalue,
            "value": item.ivalue
        })

    return result


def get_inspect_property_car(db: Session) -> List[dict]:
    """取得車輛下拉清單選項"""
    items = db.query(InspectProperty).filter(
        InspectProperty.prop_type == 1
    ).all()

    result = []
    for item in items:
        result.append({
            "text": item.plate if item.plate else item.code,
            "value": item.id
        })

    return result


def get_inspect_property_gps(db: Session) -> List[dict]:
    """取得 GPS 下拉清單選項"""
    items = db.query(InspectProperty).filter(
        InspectProperty.prop_type == 2
    ).all()

    result = []
    for item in items:
        result.append({
            "text": item.code,
            "value": item.id
        })

    return result


def get_inspect_property_camera(db: Session) -> List[dict]:
    """取得攝像頭下拉清單選項"""
    items = db.query(InspectProperty).filter(
        InspectProperty.prop_type == 3
    ).all()

    result = []
    for item in items:
        result.append({
            "text": item.code,
            "value": item.id
        })

    return result


def get_organization(db: Session) -> List[dict]:
    """取得組織下拉清單選項"""
    items = db.query(Organization).all()

    result = []
    for item in items:
        result.append({
            "text": item.name,
            "value": item.id
        })

    return result
