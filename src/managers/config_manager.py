import json
import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, validator
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class RTSPSource(BaseModel):
    id: str
    url: str
    location: str

class DetectionSettings(BaseModel):
    helmet_confidence_threshold: float = 0.7
    drowsiness_duration_threshold: float = 3.0
    face_recognition_threshold: float = 0.6
    processing_fps: int = 2

    @validator('helmet_confidence_threshold', 'face_recognition_threshold')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence threshold must be between 0 and 1')
        return v

    @validator('drowsiness_duration_threshold')
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError('Duration threshold must be positive')
        return v

class NotificationAPI(BaseModel):
    endpoint: str
    timeout: int = 10
    retry_attempts: int = 3

class Storage(BaseModel):
    screenshot_path: str = "./screenshots/"
    max_storage_days: int = 30
    image_quality: int = 95

    @validator('image_quality')
    def validate_quality(cls, v):
        if not 1 <= v <= 100:
            raise ValueError('Image quality must be between 1 and 100')
        return v

class Database(BaseModel):
    type: str = "sqlite"
    url: str = "sqlite:///./data/monitoring.db"

class Models(BaseModel):
    helmet_model_path: str = "./models/helmet_detection.pt"
    face_model_path: str = "./models/face_recognition.pkl"

class Logging(BaseModel):
    level: str = "INFO"
    log_file: str = "./logs/monitoring.log"
    max_file_size: str = "10MB"
    backup_count: int = 5

class Config(BaseModel):
    rtsp_sources: List[RTSPSource]
    detection_settings: DetectionSettings
    notification_api: NotificationAPI
    storage: Storage
    database: Database = Database()
    models: Models = Models()
    logging: Logging = Logging()

class ConfigManager:
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self._config: Optional[Config] = None

    def load_config(self) -> Config:
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config file not found: {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            self._config = Config(**config_data)
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            return self._config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def save_config(self, config: Config) -> None:
        try:
            os.makedirs(self.config_path.parent, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.dict(), f, indent=2, ensure_ascii=False)

            self._config = config
            logger.info(f"Configuration saved successfully to {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get_config(self) -> Config:
        if self._config is None:
            return self.load_config()
        return self._config

    def update_rtsp_sources(self, sources: List[RTSPSource]) -> None:
        config = self.get_config()
        config.rtsp_sources = sources
        self.save_config(config)

    def add_rtsp_source(self, source: RTSPSource) -> None:
        config = self.get_config()
        existing_ids = [s.id for s in config.rtsp_sources]
        if source.id in existing_ids:
            raise ValueError(f"RTSP source with ID '{source.id}' already exists")

        config.rtsp_sources.append(source)
        self.save_config(config)

    def remove_rtsp_source(self, source_id: str) -> None:
        config = self.get_config()
        config.rtsp_sources = [s for s in config.rtsp_sources if s.id != source_id]
        self.save_config(config)

    def update_detection_settings(self, settings: DetectionSettings) -> None:
        config = self.get_config()
        config.detection_settings = settings
        self.save_config(config)

    def create_directories(self) -> None:
        config = self.get_config()

        directories = [
            config.storage.screenshot_path,
            os.path.dirname(config.logging.log_file),
            os.path.dirname(config.models.helmet_model_path),
            os.path.dirname(config.models.face_model_path)
        ]

        if config.database.type == "sqlite":
            db_path = config.database.url.replace("sqlite:///", "")
            directories.append(os.path.dirname(db_path))

        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")

    def validate_paths(self) -> Dict[str, bool]:
        config = self.get_config()
        validation_results = {}

        model_paths = [
            config.models.helmet_model_path,
            config.models.face_model_path
        ]

        for path in model_paths:
            validation_results[path] = os.path.exists(path)
            if not validation_results[path]:
                logger.warning(f"Model file not found: {path}")

        return validation_results