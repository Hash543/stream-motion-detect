"""
Equipment Assets API Router
設備資產管理 API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from api.database import get_db
from api.models import (
    InspectProperty,
    RelInspectProperty,
    RelInspectPropertyOrganization,
    Organization,
    SysParams
)

router = APIRouter()


# Pydantic Models
class OrganizationItem(BaseModel):
    id: int
    canRead: bool = False
    canEdit: bool = False


class DeviceItem(BaseModel):
    id: int


class EquipmentAssetCreate(BaseModel):
    prop_type: int  # 1:車輛, 2:GPS, 3:攝像頭
    plate: Optional[str] = None
    brand: Optional[str] = None
    devices: Optional[List[DeviceItem]] = None
    organizations: Optional[List[OrganizationItem]] = None


class EquipmentAssetUpdate(BaseModel):
    prop_type: Optional[int] = None
    plate: Optional[str] = None
    brand: Optional[str] = None
    devices: Optional[List[DeviceItem]] = None
    organizations: Optional[List[OrganizationItem]] = None


class EquipmentAssetResponse(BaseModel):
    id: int
    code: str
    prop_type: int
    plate: Optional[str]
    brand: Optional[str]
    status: int
    last_online_time: Optional[datetime]
    created_id: Optional[int]
    created_at: datetime
    updated_id: Optional[int]
    updated_at: datetime
    organizations: Optional[List[dict]] = None
    devices: Optional[List[dict]] = None

    class Config:
        from_attributes = True


def convert_to_api_model(item: InspectProperty, db: Session, include_organizations: bool = True, include_devices: bool = False) -> dict:
    """將資料庫模型轉換為 API 回應格式"""
    result = {
        "id": item.id,
        "code": item.code,
        "prop_type": item.prop_type,
        "plate": item.plate,
        "brand": item.brand,
        "status": item.status,
        "last_online_time": item.last_online_time.isoformat() if item.last_online_time else None,
        "created_id": item.created_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_id": item.updated_id,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None
    }

    # 加入組織資訊
    if include_organizations:
        org_rels = db.query(RelInspectPropertyOrganization).filter(
            RelInspectPropertyOrganization.inspect_property_id == item.id
        ).all()

        organizations = {}
        for rel in org_rels:
            org = db.query(Organization).filter(Organization.id == rel.organization_id).first()
            if org:
                if rel.organization_id not in organizations:
                    organizations[rel.organization_id] = {
                        "id": org.id,
                        "name": org.name,
                        "canRead": False,
                        "canEdit": False
                    }
                if rel.function == "EDIT":
                    organizations[rel.organization_id]["canEdit"] = True
                elif rel.function == "READ":
                    organizations[rel.organization_id]["canRead"] = True

        result["organizations"] = list(organizations.values())

    # 加入設備資訊
    if include_devices:
        devices = []
        # 查詢關聯的設備
        device_rels = db.query(RelInspectProperty).filter(
            RelInspectProperty.inspect_property_car_id == item.id
        ).all()

        for rel in device_rels:
            device = db.query(InspectProperty).filter(InspectProperty.id == rel.inspect_property_device_id).first()
            if device:
                devices.append(convert_to_api_model(device, db, include_organizations=False, include_devices=False))

        result["devices"] = devices

    return result


def generate_equipment_code(db: Session, prop_type: int) -> str:
    """生成設備編號"""
    # 從 sys_params 取得前綴
    param = db.query(SysParams).filter(
        and_(
            SysParams.param_type == "inspect_property_type",
            SysParams.ivalue == prop_type
        )
    ).first()

    prefix = param.pvalue if param else f"TYPE{prop_type}"

    # 計算該類型的數量
    count = db.query(InspectProperty).filter(InspectProperty.prop_type == prop_type).count()

    # 生成編號
    code = f"{prefix}-{str(count + 1).zfill(3)}"
    return code


@router.get("/devices", response_model=dict)
async def list_devices(db: Session = Depends(get_db)):
    """列出所有設備（GPS & 攝像頭）"""
    try:
        # 查詢 GPS (type=2) 和攝像頭 (type=3)
        devices = db.query(InspectProperty).filter(
            InspectProperty.prop_type.in_([2, 3])
        ).all()

        # 按設備類型分組
        gps_devices = []
        camera_devices = []

        for device in devices:
            device_data = convert_to_api_model(device, db, include_organizations=False)
            if device.prop_type == 2:
                gps_devices.append(device_data)
            elif device.prop_type == 3:
                camera_devices.append(device_data)

        return {
            "msg": "success",
            "data": {
                "gps": gps_devices,
                "camera": camera_devices
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=dict)
async def list_equipment_assets(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """取得設備資產列表（分頁）"""
    try:
        offset = (page - 1) * pageSize

        # 查詢總數
        total = db.query(InspectProperty).count()

        # 查詢分頁資料
        items = db.query(InspectProperty).offset(offset).limit(pageSize).all()

        # 轉換為 API 格式
        item_list = [convert_to_api_model(item, db, include_organizations=True) for item in items]

        return {
            "total": total,
            "list": item_list,
            "page": page,
            "pageSize": pageSize
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}", response_model=dict)
async def get_equipment_asset(id: int, db: Session = Depends(get_db)):
    """取得單一設備資產詳情"""
    try:
        item = db.query(InspectProperty).filter(InspectProperty.id == id).first()

        if not item:
            raise HTTPException(status_code=404, detail="設備資產不存在")

        result = convert_to_api_model(item, db, include_organizations=True, include_devices=True)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=dict)
async def create_equipment_asset(asset_data: EquipmentAssetCreate, db: Session = Depends(get_db)):
    """新增設備資產"""
    try:
        # 生成設備編號
        code = generate_equipment_code(db, asset_data.prop_type)

        # 建立設備資產
        new_asset = InspectProperty(
            code=code,
            prop_type=asset_data.prop_type,
            plate=asset_data.plate,
            brand=asset_data.brand,
            status=2,  # 預設離線
            created_id=0,  # TODO: 從 JWT 取得使用者 ID
            created_at=datetime.now(),
            updated_id=0,
            updated_at=datetime.now()
        )
        db.add(new_asset)
        db.flush()  # 獲取 ID

        # 建立設備關聯
        if asset_data.devices:
            for device in asset_data.devices:
                rel = RelInspectProperty(
                    inspect_property_car_id=new_asset.id,
                    inspect_property_device_id=device.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(rel)

        # 建立組織關聯
        if asset_data.organizations:
            for org in asset_data.organizations:
                if org.canEdit:
                    rel = RelInspectPropertyOrganization(
                        inspect_property_id=new_asset.id,
                        organization_id=org.id,
                        function="EDIT",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(rel)
                if org.canRead:
                    rel = RelInspectPropertyOrganization(
                        inspect_property_id=new_asset.id,
                        organization_id=org.id,
                        function="READ",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(rel)

        db.commit()
        db.refresh(new_asset)

        result = convert_to_api_model(new_asset, db, include_organizations=False)
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{id}", response_model=dict)
async def update_equipment_asset(id: int, asset_data: EquipmentAssetUpdate, db: Session = Depends(get_db)):
    """更新設備資產"""
    try:
        # 檢查資產是否存在
        asset = db.query(InspectProperty).filter(InspectProperty.id == id).first()

        if not asset:
            raise HTTPException(status_code=404, detail="設備資產不存在")

        # 更新基本資訊
        if asset_data.prop_type is not None:
            asset.prop_type = asset_data.prop_type
        if asset_data.plate is not None:
            asset.plate = asset_data.plate
        if asset_data.brand is not None:
            asset.brand = asset_data.brand

        asset.updated_id = 0  # TODO: 從 JWT 取得使用者 ID
        asset.updated_at = datetime.now()

        # 更新設備關聯
        if asset_data.devices is not None:
            # 刪除舊關聯
            db.query(RelInspectProperty).filter(
                RelInspectProperty.inspect_property_car_id == id
            ).delete()

            # 建立新關聯
            for device in asset_data.devices:
                rel = RelInspectProperty(
                    inspect_property_car_id=id,
                    inspect_property_device_id=device.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(rel)

        # 更新組織關聯
        if asset_data.organizations is not None:
            # 刪除舊關聯
            db.query(RelInspectPropertyOrganization).filter(
                RelInspectPropertyOrganization.inspect_property_id == id
            ).delete()

            # 建立新關聯
            for org in asset_data.organizations:
                if org.canEdit:
                    rel = RelInspectPropertyOrganization(
                        inspect_property_id=id,
                        organization_id=org.id,
                        function="EDIT",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(rel)
                if org.canRead:
                    rel = RelInspectPropertyOrganization(
                        inspect_property_id=id,
                        organization_id=org.id,
                        function="READ",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(rel)

        db.commit()
        db.refresh(asset)

        result = convert_to_api_model(asset, db, include_organizations=False)
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}", response_model=dict)
async def delete_equipment_asset(id: int, db: Session = Depends(get_db)):
    """刪除設備資產"""
    try:
        # 檢查資產是否存在
        asset = db.query(InspectProperty).filter(InspectProperty.id == id).first()

        if not asset:
            raise HTTPException(status_code=404, detail="設備資產不存在")

        # 刪除設備關聯
        db.query(RelInspectProperty).filter(
            RelInspectProperty.inspect_property_car_id == id
        ).delete()

        # 刪除組織關聯
        db.query(RelInspectPropertyOrganization).filter(
            RelInspectPropertyOrganization.inspect_property_id == id
        ).delete()

        # 刪除資產
        db.delete(asset)
        db.commit()

        return {"message": "設備資產已成功刪除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
