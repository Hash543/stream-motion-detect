"""
Database Stream Loader
从数据库加载 stream_sources 配置
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DatabaseStreamLoader:
    """从数据库加载 stream sources 配置"""

    @staticmethod
    def load_streams_from_database(db: Session) -> List[Dict[str, Any]]:
        """
        从数据库加载所有启用的 stream sources

        Args:
            db: SQLAlchemy Session

        Returns:
            List of stream configurations compatible with UniversalStreamManager
        """
        try:
            from api.models import StreamSource

            # 查询所有启用的 streams
            streams = db.query(StreamSource).filter(
                StreamSource.enabled == True
            ).all()

            stream_configs = []
            for stream in streams:
                config = DatabaseStreamLoader._convert_to_stream_config(stream)
                if config:
                    stream_configs.append(config)

            logger.info(f"Loaded {len(stream_configs)} enabled streams from database")
            return stream_configs

        except Exception as e:
            logger.error(f"Error loading streams from database: {e}")
            return []

    @staticmethod
    def _convert_to_stream_config(stream_source) -> Optional[Dict[str, Any]]:
        """
        将数据库 StreamSource 转换为 UniversalStreamManager 配置格式

        Args:
            stream_source: StreamSource model instance

        Returns:
            Stream configuration dict compatible with StreamFactory
        """
        try:
            # 确保必要字段存在
            if not stream_source.url:
                logger.warning(f"Stream {stream_source.stream_id} has no URL, skipping")
                return None

            # StreamFactory 期望的格式：
            # {
            #   'id': str,
            #   'name': str,
            #   'type': str,
            #   'location': str,  # 必需
            #   'config': {       # 必需，包含具体配置
            #       'url': str (for RTSP/HTTP),
            #       'device_index': int (for WEBCAM)
            #   }
            # }

            # 构建 config 字典
            stream_config_dict = {}

            # 根据 stream_type 设置对应的配置
            stream_type = stream_source.stream_type.upper()

            if stream_type == 'RTSP':
                stream_config_dict['url'] = stream_source.url
            elif stream_type == 'HTTP_MJPEG' or stream_type == 'HTTP':
                stream_config_dict['url'] = stream_source.url
            elif stream_type == 'WEBCAM':
                # 如果是 WEBCAM，从 url 或 config 中获取 device_index
                if stream_source.config and 'device_index' in stream_source.config:
                    stream_config_dict['device_index'] = stream_source.config['device_index']
                else:
                    # 尝试从 URL 解析
                    try:
                        stream_config_dict['device_index'] = int(stream_source.url)
                    except:
                        stream_config_dict['device_index'] = 0

            # 合并数据库中的额外配置
            if stream_source.config and isinstance(stream_source.config, dict):
                stream_config_dict.update(stream_source.config)

            # 构建最终配置
            config = {
                'id': stream_source.stream_id,
                'name': stream_source.name,
                'type': stream_type,
                'location': stream_source.location or 'Unknown Location',  # 提供默认值
                'config': stream_config_dict,
                'enabled': stream_source.enabled if stream_source.enabled is not None else True,
            }

            return config

        except Exception as e:
            logger.error(f"Error converting stream source to config: {e}")
            return None

    @staticmethod
    def get_stream_by_id(db: Session, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        从数据库获取特定的 stream

        Args:
            db: SQLAlchemy Session
            stream_id: Stream ID

        Returns:
            Stream configuration dict or None
        """
        try:
            from api.models import StreamSource

            stream = db.query(StreamSource).filter(
                StreamSource.stream_id == stream_id
            ).first()

            if stream:
                return DatabaseStreamLoader._convert_to_stream_config(stream)

            return None

        except Exception as e:
            logger.error(f"Error getting stream {stream_id} from database: {e}")
            return None
