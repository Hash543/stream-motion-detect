"""
Role API Router
角色管理 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from api.database import get_db
from api.models import Role, RolePermission, Permission

router = APIRouter()


# Pydantic Models
class PermissionMapItem(BaseModel):
    permission_id: int
    can_access: bool = False
    can_edit: bool = False


class RoleCreate(BaseModel):
    role_name: str
    alias_name: Optional[str] = None
    org_id: Optional[int] = None
    created_id: Optional[int] = None
    permission_map: Optional[List[PermissionMapItem]] = None


class RoleUpdate(BaseModel):
    roleID: int
    role_name: str
    alias_name: Optional[str] = None
    updated_id: Optional[int] = None
    permission_map: Optional[List[PermissionMapItem]] = None


class RoleResponse(BaseModel):
    id: int
    role_name: str
    alias_name: Optional[str]
    org_id: Optional[int]
    created_id: Optional[int]
    created_at: datetime
    updated_id: Optional[int]
    updated_at: datetime
    permissions: Optional[List[dict]] = None

    class Config:
        from_attributes = True


@router.get("/list", response_model=dict)
async def get_role_list(db: Session = Depends(get_db)):
    """取得所有角色列表"""
    try:
        roles = db.query(Role).all()

        result_list = []
        for role in roles:
            # 查詢該角色的權限
            role_permissions = db.query(RolePermission).filter(
                RolePermission.role_id == role.id
            ).all()

            permissions = []
            for rp in role_permissions:
                permission = db.query(Permission).filter(
                    Permission.id == rp.permission_id
                ).first()
                if permission:
                    permissions.append({
                        "id": permission.id,
                        "permission_name": permission.permission_name,
                        "can_access": rp.can_access,
                        "can_edit": rp.can_edit
                    })

            result_list.append({
                "id": role.id,
                "role_name": role.role_name,
                "alias_name": role.alias_name,
                "org_id": role.org_id,
                "created_id": role.created_id,
                "created_at": role.created_at.isoformat() if role.created_at else None,
                "updated_id": role.updated_id,
                "updated_at": role.updated_at.isoformat() if role.updated_at else None,
                "permissions": permissions
            })

        return {"result": "success", "data": result_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=dict)
async def add_role(role_data: RoleCreate, db: Session = Depends(get_db)):
    """新增角色"""
    try:
        # 創建角色
        new_role = Role(
            role_name=role_data.role_name,
            alias_name=role_data.alias_name,
            org_id=role_data.org_id,
            created_id=role_data.created_id,
            created_at=datetime.now(),
            updated_id=role_data.created_id,
            updated_at=datetime.now()
        )
        db.add(new_role)
        db.flush()  # 獲取 new_role.id

        # 添加權限映射
        if role_data.permission_map:
            for perm in role_data.permission_map:
                new_role_perm = RolePermission(
                    role_id=new_role.id,
                    permission_id=perm.permission_id,
                    can_access=perm.can_access,
                    can_edit=perm.can_edit,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(new_role_perm)

        db.commit()
        db.refresh(new_role)

        # 查詢完整角色資訊
        role_permissions = db.query(RolePermission).filter(
            RolePermission.role_id == new_role.id
        ).all()

        permissions = []
        for rp in role_permissions:
            permission = db.query(Permission).filter(
                Permission.id == rp.permission_id
            ).first()
            if permission:
                permissions.append({
                    "id": permission.id,
                    "permission_name": permission.permission_name,
                    "can_access": rp.can_access,
                    "can_edit": rp.can_edit
                })

        result = {
            "id": new_role.id,
            "role_name": new_role.role_name,
            "alias_name": new_role.alias_name,
            "org_id": new_role.org_id,
            "created_id": new_role.created_id,
            "created_at": new_role.created_at.isoformat() if new_role.created_at else None,
            "updated_id": new_role.updated_id,
            "updated_at": new_role.updated_at.isoformat() if new_role.updated_at else None,
            "permissions": permissions
        }

        return {"result": "success", "data": result}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{roleID}", response_model=dict)
async def get_role(roleID: int, db: Session = Depends(get_db)):
    """取得單一角色資訊"""
    try:
        role = db.query(Role).filter(Role.id == roleID).first()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 查詢該角色的權限
        role_permissions = db.query(RolePermission).filter(
            RolePermission.role_id == role.id
        ).all()

        permissions = []
        for rp in role_permissions:
            permission = db.query(Permission).filter(
                Permission.id == rp.permission_id
            ).first()
            if permission:
                permissions.append({
                    "id": permission.id,
                    "permission_name": permission.permission_name,
                    "can_access": rp.can_access,
                    "can_edit": rp.can_edit
                })

        result = {
            "id": role.id,
            "role_name": role.role_name,
            "alias_name": role.alias_name,
            "org_id": role.org_id,
            "created_id": role.created_id,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_id": role.updated_id,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None,
            "permissions": permissions
        }

        return {"result": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update", response_model=dict)
async def update_role(role_data: RoleUpdate, db: Session = Depends(get_db)):
    """更新角色"""
    try:
        role = db.query(Role).filter(Role.id == role_data.roleID).first()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 更新角色基本資訊
        role.role_name = role_data.role_name
        role.alias_name = role_data.alias_name
        role.updated_id = role_data.updated_id
        role.updated_at = datetime.now()

        # 更新權限映射
        if role_data.permission_map is not None:
            # 刪除舊的權限映射
            db.query(RolePermission).filter(
                RolePermission.role_id == role_data.roleID
            ).delete()

            # 添加新的權限映射
            for perm in role_data.permission_map:
                new_role_perm = RolePermission(
                    role_id=role_data.roleID,
                    permission_id=perm.permission_id,
                    can_access=perm.can_access,
                    can_edit=perm.can_edit,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(new_role_perm)

        db.commit()
        db.refresh(role)

        # 查詢完整角色資訊
        role_permissions = db.query(RolePermission).filter(
            RolePermission.role_id == role.id
        ).all()

        permissions = []
        for rp in role_permissions:
            permission = db.query(Permission).filter(
                Permission.id == rp.permission_id
            ).first()
            if permission:
                permissions.append({
                    "id": permission.id,
                    "permission_name": permission.permission_name,
                    "can_access": rp.can_access,
                    "can_edit": rp.can_edit
                })

        result = {
            "id": role.id,
            "role_name": role.role_name,
            "alias_name": role.alias_name,
            "org_id": role.org_id,
            "created_id": role.created_id,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_id": role.updated_id,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None,
            "permissions": permissions
        }

        return {"result": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
