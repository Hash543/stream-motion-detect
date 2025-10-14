"""
Organization API Router
組織管理 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from api.database import get_db
from api.models import Organization

router = APIRouter()


# Pydantic Models
class OrganizationCreate(BaseModel):
    name: str
    full_name: Optional[str] = None
    pid: Optional[int] = None
    org_type: Optional[str] = None
    tel: Optional[str] = None
    address: Optional[str] = None
    gui_no: Optional[str] = None
    bank_code: Optional[str] = None
    bank_num: Optional[str] = None
    remarks: Optional[str] = None
    contact_person: Optional[str] = None
    contact_ext: Optional[str] = None
    contact_tel: Optional[str] = None
    contact_email: Optional[str] = None
    created_id: Optional[int] = None


class OrganizationUpdate(BaseModel):
    id: int
    name: str
    full_name: Optional[str] = None
    pid: Optional[int] = None
    org_type: Optional[str] = None
    tel: Optional[str] = None
    address: Optional[str] = None
    gui_no: Optional[str] = None
    bank_code: Optional[str] = None
    bank_num: Optional[str] = None
    remarks: Optional[str] = None
    contact_person: Optional[str] = None
    contact_ext: Optional[str] = None
    contact_tel: Optional[str] = None
    contact_email: Optional[str] = None
    updated_id: Optional[int] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    full_name: Optional[str]
    pid: Optional[int]
    org_type: Optional[str]
    tel: Optional[str]
    address: Optional[str]
    gui_no: Optional[str]
    bank_code: Optional[str]
    bank_num: Optional[str]
    remarks: Optional[str]
    contact_person: Optional[str]
    contact_ext: Optional[str]
    contact_tel: Optional[str]
    contact_email: Optional[str]
    created_id: Optional[int]
    created_at: datetime
    updated_id: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/list", response_model=dict)
async def get_organization_list(db: Session = Depends(get_db)):
    """取得所有組織列表"""
    try:
        organizations = db.query(Organization).all()

        data = []
        for org in organizations:
            data.append({
                "id": org.id,
                "name": org.name,
                "full_name": org.full_name,
                "pid": org.pid,
                "org_type": org.org_type,
                "tel": org.tel,
                "address": org.address,
                "gui_no": org.gui_no,
                "bank_code": org.bank_code,
                "bank_num": org.bank_num,
                "remarks": org.remarks,
                "contact_person": org.contact_person,
                "contact_ext": org.contact_ext,
                "contact_tel": org.contact_tel,
                "contact_email": org.contact_email,
                "created_id": org.created_id,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "updated_id": org.updated_id,
                "updated_at": org.updated_at.isoformat() if org.updated_at else None
            })

        return {"result": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/getOrgSelectOptions", response_model=dict)
async def get_org_select_options(db: Session = Depends(get_db)):
    """取得組織下拉選單選項"""
    try:
        organizations = db.query(Organization).all()

        data = []
        for org in organizations:
            data.append({
                "id": org.id,
                "name": org.name,
                "full_name": org.full_name
            })

        return {"result": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=dict)
async def add_organization(org_data: OrganizationCreate, db: Session = Depends(get_db)):
    """新增組織"""
    try:
        new_org = Organization(
            name=org_data.name,
            full_name=org_data.full_name,
            pid=org_data.pid,
            org_type=org_data.org_type,
            tel=org_data.tel,
            address=org_data.address,
            gui_no=org_data.gui_no,
            bank_code=org_data.bank_code,
            bank_num=org_data.bank_num,
            remarks=org_data.remarks,
            contact_person=org_data.contact_person,
            contact_ext=org_data.contact_ext,
            contact_tel=org_data.contact_tel,
            contact_email=org_data.contact_email,
            created_id=org_data.created_id,
            created_at=datetime.now(),
            updated_id=org_data.created_id,
            updated_at=datetime.now()
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)

        result = {
            "id": new_org.id,
            "name": new_org.name,
            "full_name": new_org.full_name,
            "pid": new_org.pid,
            "org_type": new_org.org_type,
            "tel": new_org.tel,
            "address": new_org.address,
            "gui_no": new_org.gui_no,
            "bank_code": new_org.bank_code,
            "bank_num": new_org.bank_num,
            "remarks": new_org.remarks,
            "contact_person": new_org.contact_person,
            "contact_ext": new_org.contact_ext,
            "contact_tel": new_org.contact_tel,
            "contact_email": new_org.contact_email,
            "created_id": new_org.created_id,
            "created_at": new_org.created_at.isoformat() if new_org.created_at else None,
            "updated_id": new_org.updated_id,
            "updated_at": new_org.updated_at.isoformat() if new_org.updated_at else None
        }

        return {"result": "success", "data": result}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{orgID}", response_model=dict)
async def get_organization(orgID: int, db: Session = Depends(get_db)):
    """取得單一組織資訊"""
    try:
        org = db.query(Organization).filter(Organization.id == orgID).first()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        result = {
            "id": org.id,
            "name": org.name,
            "full_name": org.full_name,
            "pid": org.pid,
            "org_type": org.org_type,
            "tel": org.tel,
            "address": org.address,
            "gui_no": org.gui_no,
            "bank_code": org.bank_code,
            "bank_num": org.bank_num,
            "remarks": org.remarks,
            "contact_person": org.contact_person,
            "contact_ext": org.contact_ext,
            "contact_tel": org.contact_tel,
            "contact_email": org.contact_email,
            "created_id": org.created_id,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "updated_id": org.updated_id,
            "updated_at": org.updated_at.isoformat() if org.updated_at else None
        }

        return {"result": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update", response_model=dict)
async def update_organization(org_data: OrganizationUpdate, db: Session = Depends(get_db)):
    """更新組織"""
    try:
        org = db.query(Organization).filter(Organization.id == org_data.id).first()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # 更新組織資訊
        org.name = org_data.name
        org.full_name = org_data.full_name
        org.pid = org_data.pid
        org.org_type = org_data.org_type
        org.tel = org_data.tel
        org.address = org_data.address
        org.gui_no = org_data.gui_no
        org.bank_code = org_data.bank_code
        org.bank_num = org_data.bank_num
        org.remarks = org_data.remarks
        org.contact_person = org_data.contact_person
        org.contact_ext = org_data.contact_ext
        org.contact_tel = org_data.contact_tel
        org.contact_email = org_data.contact_email
        org.updated_id = org_data.updated_id
        org.updated_at = datetime.now()

        db.commit()
        db.refresh(org)

        result = {
            "id": org.id,
            "name": org.name,
            "full_name": org.full_name,
            "pid": org.pid,
            "org_type": org.org_type,
            "tel": org.tel,
            "address": org.address,
            "gui_no": org.gui_no,
            "bank_code": org.bank_code,
            "bank_num": org.bank_num,
            "remarks": org.remarks,
            "contact_person": org.contact_person,
            "contact_ext": org.contact_ext,
            "contact_tel": org.contact_tel,
            "contact_email": org.contact_email,
            "created_id": org.created_id,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "updated_id": org.updated_id,
            "updated_at": org.updated_at.isoformat() if org.updated_at else None
        }

        return {"result": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{orgID}", response_model=dict)
async def delete_organization(orgID: int, db: Session = Depends(get_db)):
    """刪除組織"""
    try:
        org = db.query(Organization).filter(Organization.id == orgID).first()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        db.delete(org)
        db.commit()

        return {"result": "success", "data": {"id": orgID}}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
