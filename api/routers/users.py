"""
使用者管理 API 路由
從舊專案 face-motion/server/routes/users.js 轉移過來
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel, Field
from typing import Optional, List
import base64
import jwt
import os
from datetime import datetime

from api.database import get_db
from api.models import User, Role, Organization, Permission, RolePermission

router = APIRouter(prefix="/api/users", tags=["Users"])
security = HTTPBearer()

# JWT 設定
SECRET_KEY = os.getenv("SESSION_SECRET", "your-secret-key-change-this")
ALGORITHM = "HS256"


# ============ Pydantic Models ============

class UserProfileResponse(BaseModel):
    """使用者 profile 回應"""
    id: int
    username: str
    name: Optional[str]
    org_id: Optional[int]
    role_id: Optional[int]
    permissions: List[dict]
    org_type: Optional[str]
    upward: bool


class UserListItem(BaseModel):
    """使用者列表項目"""
    id: int
    username: str
    user_name: Optional[str]
    org_id: Optional[int]
    role_id: Optional[int]
    status: int
    position_id: Optional[int]
    created_at: Optional[datetime]


class UserListResponse(BaseModel):
    """使用者列表回應"""
    msg: str
    totalPages: int
    currentPage: int
    pageSize: int
    total: int
    list: List[UserListItem]


class AddUserRequest(BaseModel):
    """新增使用者請求"""
    username: str
    user_name: str
    password: str
    oId: int  # org_id
    pId: Optional[int] = None  # position_id
    rId: int  # role_id


class UpdateUserRequest(BaseModel):
    """更新使用者請求"""
    id: int
    user_name: str
    oId: int  # org_id
    rId: int  # role_id
    pId: Optional[int] = None  # position_id


class UpdatePasswordRequest(BaseModel):
    """更新密碼請求"""
    username: str
    oldPassword: str
    newPassword: str
    confirmPassword: str


class ResetPasswordRequest(BaseModel):
    """重設密碼請求"""
    id: int


class UpdateStatusRequest(BaseModel):
    """更新狀態請求"""
    id: int
    status: int = Field(..., ge=0, le=2, description="0:啟用 1:凍結 2:刪除")


class UserSelectOption(BaseModel):
    """使用者選項"""
    value: int
    label: str


# ============ Helper Functions ============

def encode_password(username: str, password: str) -> str:
    """密碼編碼 - 與 Node.js 版本相容"""
    combined = username + password
    encoded = base64.b64encode(combined.encode()).decode()
    return encoded


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """驗證 JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


# ============ API Endpoints ============

@router.get("/profile")
async def get_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    取得使用者 profile
    對應: GET /profile
    """
    try:
        # 驗證 token
        payload = verify_token(credentials)
        user_id = payload.get("data")

        # 查詢使用者
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 查詢角色和權限
        permissions = []
        org_type = None
        upward = False

        if user.role_id:
            role = db.query(Role).filter(Role.id == user.role_id).first()
            if role:
                # 查詢角色權限
                role_permissions = db.query(RolePermission).filter(
                    RolePermission.role_id == user.role_id
                ).all()

                for rp in role_permissions:
                    perm = db.query(Permission).filter(Permission.id == rp.permission_id).first()
                    if perm:
                        permissions.append({
                            "id": perm.id,
                            "permission_name": perm.permission_name,
                            "can_access": rp.can_access,
                            "can_edit": rp.can_edit
                        })

        # 查詢組織資訊
        if user.org_id:
            org = db.query(Organization).filter(Organization.id == user.org_id).first()
            if org:
                org_type = org.org_type
                # upward 判斷邏輯 (可根據需求調整)
                upward = org.org_type == "0" or user.role_id == 1

        return {
            "result": "success",
            "data": {
                "id": user.id,
                "username": user.username,
                "name": user.user_name,
                "org_id": user.org_id,
                "role_id": user.role_id,
                "permissions": permissions,
                "org_type": org_type,
                "upward": upward
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first"
        )


@router.get("/list")
async def get_user_list(
    page: int = 1,
    pageSize: int = 10,
    username: Optional[str] = None,
    user_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    根據條件查詢使用者列表
    對應: GET /list
    """
    try:
        # 驗證參數
        page = max(1, min(page, 9999))
        pageSize = max(1, min(pageSize, 100))

        # 建立查詢
        query = db.query(User)

        # 搜尋條件
        if username:
            query = query.filter(User.username.like(f"%{username}%"))
        if user_name:
            query = query.filter(User.user_name.like(f"%{user_name}%"))

        # 總數
        total = query.count()

        # 分頁
        offset = (page - 1) * pageSize
        users = query.offset(offset).limit(pageSize).all()

        # 組裝資料
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "user_name": user.user_name,
                "org_id": user.org_id,
                "role_id": user.role_id,
                "status": user.status,
                "position_id": user.position_id,
                "created_at": user.created_at
            })

        return {
            "data": {
                "msg": "success",
                "totalPages": (total + pageSize - 1) // pageSize,
                "currentPage": page,
                "pageSize": pageSize,
                "total": total,
                "list": user_list
            }
        }

    except Exception as e:
        return {"msg": "fail", "error": str(e)}


@router.get("/getUserSelectOptions")
async def get_user_select_options(
    opR: Optional[str] = None,
    rIds: Optional[str] = None,
    opO: Optional[str] = None,
    oIds: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    取得使用者選項 (用於下拉選單)
    對應: GET /getUserSelectOptions
    """
    try:
        query = db.query(User)

        # 根據角色過濾
        if opR and rIds:
            role_id_list = [int(x) for x in rIds.split(",") if x.strip()]
            if opR == "in":
                query = query.filter(User.role_id.in_(role_id_list))
            elif opR == "not in":
                query = query.filter(~User.role_id.in_(role_id_list))

        # 根據組織過濾
        if opO and oIds:
            org_id_list = [int(x) for x in oIds.split(",") if x.strip()]
            if opO == "in":
                query = query.filter(User.org_id.in_(org_id_list))
            elif opO == "not in":
                query = query.filter(~User.org_id.in_(org_id_list))

        users = query.all()

        options = [
            {
                "value": user.id,
                "label": user.user_name or user.username
            }
            for user in users
        ]

        return {
            "result": "success",
            "data": options
        }

    except Exception as e:
        return {"result": "error", "msg": str(e)}


@router.post("/add")
async def add_user(
    request: AddUserRequest,
    db: Session = Depends(get_db)
):
    """
    新增使用者
    對應: POST /add
    """
    try:
        # 編碼密碼
        encoded_password = encode_password(request.username, request.password)

        # 檢查使用者是否已存在
        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="使用者名稱已存在")

        # 建立新使用者
        new_user = User(
            username=request.username,
            user_name=request.user_name,
            password=encoded_password,
            org_id=request.oId,
            role_id=request.rId,
            position_id=request.pId,
            status=0,  # 0: 正常
            created_id=1,  # TODO: 從 token 取得當前使用者 ID
            created_at=datetime.now(),
            updated_id=1,
            updated_at=datetime.now()
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "result": "success",
            "data": {
                "id": new_user.id,
                "username": new_user.username,
                "user_name": new_user.user_name,
                "org_id": new_user.org_id,
                "role_id": new_user.role_id,
                "status": new_user.status
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{userID}")
async def get_user_by_id(
    userID: int,
    db: Session = Depends(get_db)
):
    """
    根據 ID 找到使用者
    對應: GET /:userID
    """
    user = db.query(User).filter(User.id == userID).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "result": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "user_name": user.user_name,
            "org_id": user.org_id,
            "role_id": user.role_id,
            "position_id": user.position_id,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    }


@router.post("/update")
async def update_user(
    request: UpdateUserRequest,
    db: Session = Depends(get_db)
):
    """
    修改使用者
    對應: POST /update
    """
    # 驗證必填欄位
    if not request.user_name:
        raise HTTPException(status_code=400, detail="用戶姓名必填")
    if not request.oId:
        raise HTTPException(status_code=400, detail="所屬機構必選")
    if not request.rId:
        raise HTTPException(status_code=400, detail="角色必選")

    # 查詢使用者
    user = db.query(User).filter(User.id == request.id).first()
    if not user:
        raise HTTPException(status_code=400, detail="用戶不存在")

    # 更新使用者
    user.user_name = request.user_name
    user.org_id = request.oId
    user.role_id = request.rId
    if request.pId:
        user.position_id = request.pId
    user.updated_at = datetime.now()
    user.updated_id = 1  # TODO: 從 token 取得當前使用者 ID

    db.commit()

    return {"result": "success"}


@router.post("/updatePassword")
async def update_password(
    request: UpdatePasswordRequest,
    db: Session = Depends(get_db)
):
    """
    修改密碼
    對應: POST /updatePassword
    密碼規則: base64(username + password)
    """
    # 驗證必填欄位
    if not all([request.oldPassword, request.newPassword, request.confirmPassword, request.username]):
        raise HTTPException(status_code=400, detail="請輸入舊密碼、新密碼和確認密碼")

    # 編碼舊密碼
    old_encoded = encode_password(request.username, request.oldPassword)

    # 查詢使用者
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="用戶不存在")

    # 驗證舊密碼
    if user.password != old_encoded:
        raise HTTPException(status_code=400, detail="舊密碼錯誤")

    # 驗證新密碼和確認密碼
    if request.newPassword != request.confirmPassword:
        raise HTTPException(status_code=400, detail="新密碼和確認密碼不一致")

    # 編碼新密碼
    new_encoded = encode_password(request.username, request.newPassword)

    # 檢查新舊密碼是否相同
    if new_encoded == user.password:
        raise HTTPException(status_code=400, detail="新密碼和舊密碼一致")

    # 更新密碼
    user.password = new_encoded
    user.updated_at = datetime.now()
    db.commit()

    return {"result": "success"}


@router.post("/resetPassword")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    重設密碼 (重設為 12345678)
    對應: POST /resetPassword
    """
    # 查詢使用者
    user = db.query(User).filter(User.id == request.id).first()
    if not user:
        raise HTTPException(status_code=400, detail="用戶不存在")

    # 重設密碼為 12345678
    new_password = encode_password(user.username, "12345678")
    user.password = new_password
    user.updated_at = datetime.now()
    db.commit()

    return {"result": "success"}


@router.post("/updateStatus")
async def update_status(
    request: UpdateStatusRequest,
    db: Session = Depends(get_db)
):
    """
    修改使用者狀態
    對應: POST /updateStatus
    Status: 0:啟用 1:凍結 2:刪除
    """
    # 查詢使用者
    user = db.query(User).filter(User.id == request.id).first()
    if not user:
        raise HTTPException(status_code=400, detail="用戶不存在")

    # 驗證 status 值
    if request.status not in [0, 1, 2]:
        raise HTTPException(status_code=400, detail="參數錯誤")

    # 更新狀態
    user.status = request.status
    user.updated_at = datetime.now()
    db.commit()

    return {"result": "success"}
