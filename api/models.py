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
