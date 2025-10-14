"""
Database Models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from api.database import Base


class Person(Base):
    """人員資料表"""
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(100))
    position = Column(String(100))
    status = Column(String(20), default="active")  # active, inactive
    face_encoding = Column(Text)  # JSON格式的人臉特徵
    extra_data = Column(JSON)  # 其他元數據 (renamed from metadata)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class StreamSource(Base):
    """影像來源資料表"""
    __tablename__ = "stream_sources"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    stream_type = Column(String(20), nullable=False)  # RTSP, WEBCAM, HTTP_MJPEG, HLS, etc.
    url = Column(String(500))
    location = Column(String(200))
    enabled = Column(Boolean, default=True)
    config = Column(JSON)  # 串流特定配置
    status = Column(String(20), default="inactive")  # active, inactive, error
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DetectionRule(Base):
    """檢測規則資料表"""
    __tablename__ = "detection_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)

    # 規則條件
    stream_source_type = Column(String(20))  # 影像來源類型篩選
    stream_source_ids = Column(JSON)  # 特定影像來源ID列表
    person_ids = Column(JSON)  # 特定人員ID列表 (空=所有人員)
    detection_types = Column(JSON, nullable=False)  # 檢測類型列表: ["helmet", "drowsiness", "face"]

    # 規則設定
    confidence_threshold = Column(Float, default=0.7)
    time_threshold = Column(Float)  # 時間閾值(秒)，用於瞌睡等需要持續時間的檢測

    # 通知設定
    notification_enabled = Column(Boolean, default=True)
    notification_config = Column(JSON)  # 通知配置

    # 排程設定
    schedule_enabled = Column(Boolean, default=False)
    schedule_config = Column(JSON)  # 排程配置 (時間範圍等)

    priority = Column(Integer, default=0)  # 優先級
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Violation(Base):
    """違規記錄資料表"""
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    violation_id = Column(String(50), unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)

    # 來源資訊
    camera_id = Column(String(50), index=True)
    stream_source_id = Column(Integer, ForeignKey("stream_sources.id"))

    # 違規資訊
    violation_type = Column(String(50), index=True)  # no_helmet, drowsiness, unknown_person
    person_id = Column(String(50))
    person_name = Column(String(100))
    confidence = Column(Float)

    # 觸發規則
    rule_id = Column(String(50))

    # 位置資訊
    bbox_x = Column(Integer)
    bbox_y = Column(Integer)
    bbox_width = Column(Integer)
    bbox_height = Column(Integer)

    # 截圖資訊
    image_path = Column(String(500))
    image_url = Column(String(500))

    # 處理狀態
    status = Column(String(20), default="new")  # new, acknowledged, resolved
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(100))
    resolved_at = Column(DateTime)
    resolved_by = Column(String(100))
    notes = Column(Text)

    extra_data = Column(JSON)  # renamed from metadata
    created_at = Column(DateTime, default=datetime.now)


class SystemLog(Base):
    """系統日誌表"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    level = Column(String(20), index=True)  # INFO, WARNING, ERROR, CRITICAL
    source = Column(String(100))  # 日誌來源
    message = Column(Text)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)


# ==================== Face Motion 整合模型 ====================

class User(Base):
    """使用者資料表"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    user_name = Column(String(255))
    password = Column(String(255), nullable=False)
    org_id = Column(Integer, ForeignKey("organization.id"))
    role_id = Column(Integer, ForeignKey("role.id"))
    status = Column(Integer, default=1)  # 1:active, 0:inactive, 2:deleted
    position_id = Column(Integer, ForeignKey("positions.id"))
    created_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_id = Column(Integer)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Role(Base):
    """角色資料表"""
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_name = Column(String(255), nullable=False)
    alias_name = Column(String(255))
    org_id = Column(Integer, ForeignKey("organization.id"))
    created_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_id = Column(Integer)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Organization(Base):
    """組織資料表"""
    __tablename__ = "organization"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(255))
    pid = Column(Integer, ForeignKey("organization.id"))
    org_type = Column(String(100))
    tel = Column(String(50))
    address = Column(String(500))
    gui_no = Column(String(50))
    bank_code = Column(String(50))
    bank_num = Column(String(100))
    remarks = Column(Text)
    contact_person = Column(String(100))
    contact_ext = Column(String(50))
    contact_tel = Column(String(50))
    contact_email = Column(String(255))
    created_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_id = Column(Integer)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Positions(Base):
    """職位資料表"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    posi_name = Column(String(255), nullable=False)
    posi_level = Column(Integer)
    posi_code = Column(String(50))
    org_id = Column(Integer, ForeignKey("organization.id"))
    created_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_id = Column(Integer)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AlertEvent(Base):
    """警報事件資料表"""
    __tablename__ = "alert_event"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Text)
    code = Column(String(255))
    type = Column(String(255))
    length = Column(String(255))
    area = Column(Text)
    time = Column(DateTime)
    severity = Column(Text)
    image = Column(Text)
    resized_image = Column(Text)
    lat = Column(Float)
    lng = Column(Float)
    address = Column(Text)
    note = Column(Text)
    handle_note = Column(Text)
    report_status = Column(Integer, default=1)  # 1:未處理, 2:處理中, 3:已處理
    image1 = Column(Text)
    image2 = Column(Text)
    image3 = Column(Text)
    image4 = Column(Text)
    image5 = Column(Text)
    order_no = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AlertEventAssignUser(Base):
    """警報事件分配使用者關聯表"""
    __tablename__ = "alert_event_assign_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ae_id = Column(Integer, ForeignKey("alert_event.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.now)
    status = Column(Integer, default=1)  # 1:待處理, 2:處理中, 3:已完成
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class GPS808(Base):
    """GPS808 位置追蹤資料表"""
    __tablename__ = "gps808"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), index=True, comment="設備ID")
    mobile_no = Column(String(20), comment="SIM卡號")
    plate_no = Column(String(20), comment="車牌號碼")
    protocol_version = Column(Integer, comment="協議版本")

    warn_bit = Column(Integer, comment="告警標誌")
    status_bit = Column(Integer, comment="狀態標誌")
    latitude = Column(Integer, comment="原始緯度")
    longitude = Column(Integer, comment="原始經度")
    lat = Column(Float, comment="轉換後緯度")
    lng = Column(Float, comment="轉換後經度")
    altitude = Column(Integer, comment="海拔 (m)")
    speed = Column(Float, comment="速度 (m/s)")
    speed_kph = Column(Float, comment="速度 (km/h)")
    direction = Column(Integer, comment="方向 (度)")

    device_time = Column(DateTime, comment="設備時間")
    created_at = Column(DateTime, default=datetime.now, comment="數據接收時間")


class Permission(Base):
    """權限資料表"""
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    permission_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RolePermission(Base):
    """角色權限關聯表"""
    __tablename__ = "role_permission"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permission.id"), nullable=False)
    can_access = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class InspectProperty(Base):
    """設備資產資料表"""
    __tablename__ = "inspect_property"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(255), comment="設備編號")
    prop_type = Column(Integer, comment="設備類型，1:車輛, 2:GPS, 3:攝像頭")
    plate = Column(String(255), comment="車牌")
    prop_location = Column(String(255), comment="位置")
    brand = Column(String(255), comment="品牌型號")
    mfd = Column(DateTime, comment="製造日期")
    warranty = Column(DateTime, comment="保固日期")
    period = Column(DateTime, comment="下個保養日期")
    vendor = Column(String(255), comment="維護廠商")
    warn_date = Column(DateTime, comment="汰換警告日期")
    interval = Column(Integer, comment="通知區間")
    status = Column(Integer, default=2, comment="設備狀態，1:連線, 2:離線")
    last_online_time = Column(DateTime, comment="最後上線時間")
    created_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_id = Column(Integer)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RelInspectProperty(Base):
    """設備資產關聯表（車輛與設備的關聯）"""
    __tablename__ = "rel_inspect_property"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspect_property_car_id = Column(Integer, ForeignKey("inspect_property.id"), comment="車輛ID")
    inspect_property_device_id = Column(Integer, ForeignKey("inspect_property.id"), comment="設備ID")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RelInspectPropertyOrganization(Base):
    """設備資產與組織關聯表"""
    __tablename__ = "rel_inspect_property_organization"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspect_property_id = Column(Integer, ForeignKey("inspect_property.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    function = Column(String(10), comment="功能，EDIT:編輯, READ:查看")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SysParams(Base):
    """系統參數表"""
    __tablename__ = "sys_params"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    param_type = Column(String(255), comment="參數類型")
    ivalue = Column(Integer, comment="整數值")
    pvalue = Column(String(255), comment="字串值")
    pname = Column(String(255), comment="參數名稱")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
