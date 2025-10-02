"""
Pydantic Schemas for API Request/Response
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============= Enums =============

class StreamType(str, Enum):
    """串流類型"""
    RTSP = "RTSP"
    WEBCAM = "WEBCAM"
    HTTP_MJPEG = "HTTP_MJPEG"
    HLS = "HLS"
    DASH = "DASH"
    WEBRTC = "WEBRTC"
    ONVIF = "ONVIF"


class DetectionType(str, Enum):
    """檢測類型"""
    HELMET = "helmet"
    DROWSINESS = "drowsiness"
    FACE = "face"
    CUSTOM = "custom"


class PersonStatus(str, Enum):
    """人員狀態"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class ViolationStatus(str, Enum):
    """違規狀態"""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


# ============= Person Schemas =============

class PersonBase(BaseModel):
    """人員基礎資料"""
    person_id: str = Field(..., description="人員ID")
    name: str = Field(..., description="姓名")
    department: Optional[str] = Field(None, description="部門")
    position: Optional[str] = Field(None, description="職位")
    status: PersonStatus = Field(PersonStatus.ACTIVE, description="狀態")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="其他元數據")


class PersonCreate(PersonBase):
    """建立人員"""
    pass


class PersonUpdate(BaseModel):
    """更新人員"""
    name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    status: Optional[PersonStatus] = None
    extra_data: Optional[Dict[str, Any]] = None


class PersonResponse(PersonBase):
    """人員回應"""
    id: int
    face_encoding: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Stream Source Schemas =============

class StreamSourceBase(BaseModel):
    """影像來源基礎資料"""
    stream_id: str = Field(..., description="串流ID")
    name: str = Field(..., description="串流名稱")
    stream_type: StreamType = Field(..., description="串流類型")
    url: Optional[str] = Field(None, description="串流URL")
    location: Optional[str] = Field(None, description="位置")
    enabled: bool = Field(True, description="是否啟用")
    config: Optional[Dict[str, Any]] = Field(None, description="串流配置")


class StreamSourceCreate(StreamSourceBase):
    """建立影像來源"""
    pass


class StreamSourceUpdate(BaseModel):
    """更新影像來源"""
    name: Optional[str] = None
    stream_type: Optional[StreamType] = None
    url: Optional[str] = None
    location: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class StreamSourceResponse(StreamSourceBase):
    """影像來源回應"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Detection Rule Schemas =============

class DetectionRuleBase(BaseModel):
    """檢測規則基礎資料"""
    rule_id: str = Field(..., description="規則ID")
    name: str = Field(..., description="規則名稱")
    description: Optional[str] = Field(None, description="規則描述")
    enabled: bool = Field(True, description="是否啟用")

    # 規則條件
    stream_source_type: Optional[StreamType] = Field(None, description="影像來源類型篩選")
    stream_source_ids: Optional[List[str]] = Field(None, description="特定影像來源ID列表")
    person_ids: Optional[List[str]] = Field(None, description="特定人員ID列表(空=所有人員)")
    detection_types: List[DetectionType] = Field(..., description="檢測類型列表")

    # 規則設定
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="信心度閾值")
    time_threshold: Optional[float] = Field(None, ge=0.0, description="時間閾值(秒)")

    # 通知設定
    notification_enabled: bool = Field(True, description="是否啟用通知")
    notification_config: Optional[Dict[str, Any]] = Field(None, description="通知配置")

    # 排程設定
    schedule_enabled: bool = Field(False, description="是否啟用排程")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="排程配置")

    priority: int = Field(0, description="優先級")


class DetectionRuleCreate(DetectionRuleBase):
    """建立檢測規則"""
    pass


class DetectionRuleUpdate(BaseModel):
    """更新檢測規則"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    stream_source_type: Optional[StreamType] = None
    stream_source_ids: Optional[List[str]] = None
    person_ids: Optional[List[str]] = None
    detection_types: Optional[List[DetectionType]] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    time_threshold: Optional[float] = Field(None, ge=0.0)
    notification_enabled: Optional[bool] = None
    notification_config: Optional[Dict[str, Any]] = None
    schedule_enabled: Optional[bool] = None
    schedule_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None


class DetectionRuleResponse(DetectionRuleBase):
    """檢測規則回應"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Violation Schemas =============

class ViolationQuery(BaseModel):
    """違規查詢"""
    camera_id: Optional[str] = None
    stream_source_id: Optional[int] = None
    violation_type: Optional[str] = None
    person_id: Optional[str] = None
    rule_id: Optional[str] = None
    status: Optional[ViolationStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class ViolationResponse(BaseModel):
    """違規回應"""
    id: int
    violation_id: str
    timestamp: datetime
    camera_id: str
    stream_source_id: Optional[int]
    violation_type: str
    person_id: Optional[str]
    person_name: Optional[str]
    confidence: float
    rule_id: Optional[str]
    bbox_x: Optional[int]
    bbox_y: Optional[int]
    bbox_width: Optional[int]
    bbox_height: Optional[int]
    image_path: Optional[str]
    image_url: Optional[str]
    status: str
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    notes: Optional[str]
    extra_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ViolationUpdate(BaseModel):
    """更新違規"""
    status: Optional[ViolationStatus] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    notes: Optional[str] = None


# ============= Statistics Schemas =============

class ViolationStatistics(BaseModel):
    """違規統計"""
    total_violations: int
    violations_by_type: Dict[str, int]
    violations_by_camera: Dict[str, int]
    violations_by_person: Dict[str, int]
    violations_by_status: Dict[str, int]
    period_days: int


# ============= Common Response Schemas =============

class MessageResponse(BaseModel):
    """訊息回應"""
    message: str
    detail: Optional[str] = None


class ListResponse(BaseModel):
    """列表回應"""
    data: List[Any]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """錯誤回應"""
    error: str
    message: str
    detail: Optional[str] = None
