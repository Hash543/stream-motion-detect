"""
認證 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import base64
import jwt
from datetime import datetime, timedelta
import os

from api.database import get_db
from api.models import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])
security = HTTPBearer()

# JWT 設定
SECRET_KEY = os.getenv("SESSION_SECRET", "your-secret-key-change-this")
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False


class LoginResponse(BaseModel):
    result: dict


class AddUserRequest(BaseModel):
    username: str
    password: str


class UpdatePasswordRequest(BaseModel):
    username: str
    password: str


def create_access_token(user_id: int, role_id: int, remember: bool = False):
    """創建 JWT token"""
    expire_seconds = 60 * 60 * 24 * 365 if remember else 60 * 60  # 1年 or 1小時
    expire = datetime.utcnow() + timedelta(seconds=expire_seconds)

    payload = {
        "exp": expire,
        "data": user_id,
        "role": role_id,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


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
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    使用者登入
    """
    menus = []
    btns = []

    # 編碼密碼（與 Node.js 版本相容）
    encoded_password = encode_password(request.username, request.password)

    # 查詢使用者
    user = db.query(User).filter(User.username == request.username.lower()).first()

    if user and user.password == encoded_password:
        # 登入成功
        token = create_access_token(user.id, user.role_id or 0, request.remember)

        return LoginResponse(result={
            "access_token": token,
            "token_type": "Bearer",
            "status": 0,
            "msg": "登入成功",
            "menus": menus,
            "btns": btns,
        })

    # 登入失敗
    return LoginResponse(result={
        "status": 1,
        "msg": "帳號或密碼錯誤",
        "menus": menus,
        "btns": btns,
    })


@router.post("/addEjo")
async def add_user(request: AddUserRequest, db: Session = Depends(get_db)):
    """
    新增使用者（臨時用，之後要移除）
    """
    encoded_password = encode_password(request.username, request.password)

    new_user = User(
        username=request.username.lower(),
        password=encoded_password,
        user_name=request.username,
        role_id=1,
        org_id=1,
        status=1
    )

    db.add(new_user)
    db.commit()

    return {
        "result": {
            "status": 1,
            "msg": "完成",
        }
    }


@router.post("/updateEjo")
async def update_password(request: UpdatePasswordRequest, db: Session = Depends(get_db)):
    """
    更新密碼（臨時用，之後要移除）
    """
    encoded_password = encode_password(request.username, request.password)

    user = db.query(User).filter(User.username == request.username.lower()).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = encoded_password
    db.commit()
    db.refresh(user)

    return {
        "result": {
            "status": 1,
            "msg": "完成",
            "user": {
                "id": user.id,
                "username": user.username,
            }
        }
    }


@router.get("/me")
async def get_current_user(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    取得當前登入使用者資訊
    """
    user_id = token_data.get("data")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "user_name": user.user_name,
        "role_id": user.role_id,
        "org_id": user.org_id,
    }
