"""
Person Management API Routes
人臉識別建檔API
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging
import base64
import cv2
import numpy as np

from api.database import get_db
from api.models import Person, User
from api.schemas import (
    PersonCreate, PersonUpdate, PersonResponse,
    MessageResponse, ListResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[PersonResponse])
def list_persons(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    department: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    取得人員列表

    - **skip**: 跳過筆數
    - **limit**: 限制筆數
    - **status**: 篩選狀態 (active/inactive)
    - **department**: 篩選部門
    - **user_id**: 篩選關聯的使用者ID
    """
    query = db.query(Person).outerjoin(User, Person.user_id == User.id)

    if status:
        query = query.filter(Person.status == status)
    if department:
        query = query.filter(Person.department == department)
    if user_id:
        query = query.filter(Person.user_id == user_id)

    persons = query.offset(skip).limit(limit).all()

    # 添加 user_name 到回應
    result = []
    for person in persons:
        person_dict = {
            "id": person.id,
            "person_id": person.person_id,
            "name": person.name,
            "department": person.department,
            "position": person.position,
            "user_id": person.user_id,
            "status": person.status,
            "extra_data": person.extra_data,
            "face_encoding": person.face_encoding,
            "user_name": person.user.user_name if person.user else None,
            "created_at": person.created_at,
            "updated_at": person.updated_at
        }
        result.append(person_dict)

    return result


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: str, db: Session = Depends(get_db)):
    """
    取得特定人員資訊

    - **person_id**: 人員ID
    """
    person = db.query(Person).outerjoin(User, Person.user_id == User.id)\
        .filter(Person.person_id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # 添加 user_name 到回應
    return {
        "id": person.id,
        "person_id": person.person_id,
        "name": person.name,
        "department": person.department,
        "position": person.position,
        "user_id": person.user_id,
        "status": person.status,
        "extra_data": person.extra_data,
        "face_encoding": person.face_encoding,
        "user_name": person.user.user_name if person.user else None,
        "created_at": person.created_at,
        "updated_at": person.updated_at
    }


@router.post("/", response_model=PersonResponse)
def create_person(
    person: PersonCreate,
    db: Session = Depends(get_db)
):
    """
    建立人員

    - **person_id**: 人員ID (唯一)
    - **name**: 姓名
    - **department**: 部門 (可選)
    - **position**: 職位 (可選)
    - **user_id**: 關聯的使用者ID (可選)
    - **status**: 狀態 (active/inactive)
    - **extra_data**: 其他元數據 (可選)
    """
    # 檢查是否已存在
    existing = db.query(Person).filter(Person.person_id == person.person_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Person ID already exists")

    # 如果提供了 user_id，檢查使用者是否存在
    if person.user_id:
        user = db.query(User).filter(User.id == person.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    # 建立人員
    db_person = Person(
        person_id=person.person_id,
        name=person.name,
        department=person.department,
        position=person.position,
        user_id=person.user_id,
        status=person.status,
        extra_data=person.extra_data
    )

    db.add(db_person)
    db.commit()
    db.refresh(db_person)

    logger.info(f"Created person: {person.person_id} - {person.name} (user_id: {person.user_id})")

    # 取得使用者名稱
    user_name = None
    if db_person.user_id:
        user = db.query(User).filter(User.id == db_person.user_id).first()
        user_name = user.user_name if user else None

    return {
        "id": db_person.id,
        "person_id": db_person.person_id,
        "name": db_person.name,
        "department": db_person.department,
        "position": db_person.position,
        "user_id": db_person.user_id,
        "status": db_person.status,
        "extra_data": db_person.extra_data,
        "face_encoding": db_person.face_encoding,
        "user_name": user_name,
        "created_at": db_person.created_at,
        "updated_at": db_person.updated_at
    }


@router.put("/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: str,
    person_update: PersonUpdate,
    db: Session = Depends(get_db)
):
    """
    更新人員資訊

    - **person_id**: 人員ID
    - **user_id**: 關聯的使用者ID (可選，設為 null 可清除關聯)
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # 更新欄位
    update_data = person_update.model_dump(exclude_unset=True)

    # 如果要更新 user_id，檢查使用者是否存在
    if 'user_id' in update_data and update_data['user_id'] is not None:
        user = db.query(User).filter(User.id == update_data['user_id']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    for field, value in update_data.items():
        setattr(person, field, value)

    db.commit()
    db.refresh(person)

    logger.info(f"Updated person: {person_id} (user_id: {person.user_id})")

    # 取得使用者名稱
    user_name = None
    if person.user_id:
        user = db.query(User).filter(User.id == person.user_id).first()
        user_name = user.user_name if user else None

    return {
        "id": person.id,
        "person_id": person.person_id,
        "name": person.name,
        "department": person.department,
        "position": person.position,
        "user_id": person.user_id,
        "status": person.status,
        "extra_data": person.extra_data,
        "face_encoding": person.face_encoding,
        "user_name": user_name,
        "created_at": person.created_at,
        "updated_at": person.updated_at
    }


@router.delete("/{person_id}", response_model=MessageResponse)
def delete_person(person_id: str, db: Session = Depends(get_db)):
    """
    刪除人員

    - **person_id**: 人員ID
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    db.delete(person)
    db.commit()

    logger.info(f"Deleted person: {person_id}")
    return MessageResponse(message="Person deleted successfully")


@router.post("/{person_id}/face-encoding")
async def upload_face_encoding(
    person_id: str,
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    上傳人臉照片並提取特徵編碼

    - **person_id**: 人員ID
    - **images**: 人臉照片檔案列表 (建議多張不同角度)
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    try:
        # 載入人臉檢測管理器
        from src.managers.face_detection_manager import FaceDetectionManager

        face_manager = FaceDetectionManager()

        # 讀取並處理影像
        face_encodings = []
        for image_file in images:
            # 讀取檔案
            contents = await image_file.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                logger.warning(f"Failed to decode image: {image_file.filename}")
                continue

            # 提取人臉特徵
            encoding = face_manager.extract_face_encoding(img)
            if encoding is not None:
                face_encodings.append(encoding.tolist())

        if not face_encodings:
            raise HTTPException(
                status_code=400,
                detail="No face detected in uploaded images"
            )

        # 儲存人臉特徵 (JSON格式)
        person.face_encoding = json.dumps(face_encodings)
        db.commit()

        logger.info(f"Updated face encoding for person: {person_id}")

        return {
            "message": "Face encoding updated successfully",
            "person_id": person_id,
            "encodings_count": len(face_encodings)
        }

    except Exception as e:
        logger.error(f"Error processing face encoding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/face-encoding")
def get_face_encoding(person_id: str, db: Session = Depends(get_db)):
    """
    取得人員的人臉特徵編碼

    - **person_id**: 人員ID
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if not person.face_encoding:
        raise HTTPException(status_code=404, detail="Face encoding not found")

    return {
        "person_id": person_id,
        "name": person.name,
        "has_face_encoding": True,
        "encodings_count": len(json.loads(person.face_encoding)) if person.face_encoding else 0
    }


@router.delete("/{person_id}/face-encoding", response_model=MessageResponse)
def delete_face_encoding(person_id: str, db: Session = Depends(get_db)):
    """
    刪除人員的人臉特徵編碼

    - **person_id**: 人員ID
    """
    person = db.query(Person).filter(Person.person_id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    person.face_encoding = None
    db.commit()

    logger.info(f"Deleted face encoding for person: {person_id}")
    return MessageResponse(message="Face encoding deleted successfully")


@router.get("/statistics/summary")
def get_person_statistics(db: Session = Depends(get_db)):
    """
    取得人員統計資訊
    """
    from sqlalchemy import func

    total = db.query(Person).count()
    active = db.query(Person).filter(Person.status == "active").count()
    inactive = db.query(Person).filter(Person.status == "inactive").count()
    with_face = db.query(Person).filter(Person.face_encoding.isnot(None)).count()

    # 按部門統計
    departments = db.query(Person.department, func.count(Person.id))\
        .group_by(Person.department)\
        .all()

    return {
        "total_persons": total,
        "active_persons": active,
        "inactive_persons": inactive,
        "persons_with_face_encoding": with_face,
        "departments": {dept: count for dept, count in departments if dept}
    }


@router.get("/users/options")
def get_users_options(
    status: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    取得使用者選項列表 (用於下拉選單)

    - **status**: 篩選使用者狀態 (0:正常, 1:凍結, 2:刪除)

    返回格式:
    ```json
    {
        "status": "success",
        "data": [
            {
                "value": 1,
                "label": "張三 (zhangsan)",
                "user_id": 1,
                "user_name": "張三",
                "username": "zhangsan",
                "org_id": 1,
                "role_id": 2
            }
        ]
    }
    ```
    """
    query = db.query(User)

    # 預設只顯示啟用的使用者
    if status is None:
        query = query.filter(User.status == 0)
    else:
        query = query.filter(User.status == status)

    users = query.order_by(User.user_name).all()

    options = []
    for user in users:
        label = user.user_name if user.user_name else user.username
        if user.user_name and user.username:
            label = f"{user.user_name} ({user.username})"

        options.append({
            "value": user.id,
            "label": label,
            "user_id": user.id,
            "user_name": user.user_name,
            "username": user.username,
            "org_id": user.org_id,
            "role_id": user.role_id
        })

    return {
        "status": "success",
        "data": options
    }
