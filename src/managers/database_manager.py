import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path
import threading
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)

@dataclass
class ViolationRecord:
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    camera_id: str = ""
    violation_type: str = ""
    person_id: Optional[str] = None
    confidence: float = 0.0
    bbox_x: int = 0
    bbox_y: int = 0
    bbox_width: int = 0
    bbox_height: int = 0
    image_path: Optional[str] = None
    additional_data: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class PersonRecord:
    person_id: str
    name: str
    department: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    additional_info: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class CameraRecord:
    camera_id: str
    location: str
    rtsp_url: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class DatabaseManager:
    def __init__(self, db_path: str = "data/monitoring.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for database operations
        self._lock = threading.Lock()

        # Initialize database
        self._init_database()

        logger.info(f"Database manager initialized: {self.db_path}")

    def _init_database(self) -> None:
        """Initialize database tables"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create violations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS violations (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        camera_id TEXT NOT NULL,
                        violation_type TEXT NOT NULL,
                        person_id TEXT,
                        confidence REAL NOT NULL,
                        bbox_x INTEGER NOT NULL,
                        bbox_y INTEGER NOT NULL,
                        bbox_width INTEGER NOT NULL,
                        bbox_height INTEGER NOT NULL,
                        image_path TEXT,
                        additional_data TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create persons table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS persons (
                        person_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        department TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        additional_info TEXT
                    )
                ''')

                # Create cameras table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cameras (
                        camera_id TEXT PRIMARY KEY,
                        location TEXT NOT NULL,
                        rtsp_url TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')

                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_camera_id ON violations(camera_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_person_id ON violations(person_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_type ON violations(violation_type)')

                conn.commit()
                logger.info("Database tables initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def add_violation(self, violation: ViolationRecord) -> bool:
        """Add a violation record to the database"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO violations (
                            id, timestamp, camera_id, violation_type, person_id, confidence,
                            bbox_x, bbox_y, bbox_width, bbox_height, image_path, additional_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        violation.id,
                        violation.timestamp.isoformat(),
                        violation.camera_id,
                        violation.violation_type,
                        violation.person_id,
                        violation.confidence,
                        violation.bbox_x,
                        violation.bbox_y,
                        violation.bbox_width,
                        violation.bbox_height,
                        violation.image_path,
                        violation.additional_data
                    ))

                    conn.commit()
                    logger.debug(f"Added violation record: {violation.id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to add violation record: {e}")
            return False

    def get_violations(self, camera_id: Optional[str] = None,
                      violation_type: Optional[str] = None,
                      person_id: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Get violation records with optional filters"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM violations WHERE 1=1"
                params = []

                if camera_id:
                    query += " AND camera_id = ?"
                    params.append(camera_id)

                if violation_type:
                    query += " AND violation_type = ?"
                    params.append(violation_type)

                if person_id:
                    query += " AND person_id = ?"
                    params.append(person_id)

                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())

                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                violations = []
                for row in rows:
                    violation_dict = dict(row)
                    # Convert timestamp string back to datetime
                    violation_dict['timestamp'] = datetime.fromisoformat(violation_dict['timestamp'])
                    violations.append(violation_dict)

                return violations

        except Exception as e:
            logger.error(f"Failed to get violations: {e}")
            return []

    def add_person(self, person: PersonRecord) -> bool:
        """Add a person record to the database"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT OR REPLACE INTO persons (
                            person_id, name, department, created_at, updated_at, additional_info
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        person.person_id,
                        person.name,
                        person.department,
                        person.created_at.isoformat(),
                        person.updated_at.isoformat(),
                        person.additional_info
                    ))

                    conn.commit()
                    logger.debug(f"Added person record: {person.person_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to add person record: {e}")
            return False

    def get_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Get a person record by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM persons WHERE person_id = ?", (person_id,))
                row = cursor.fetchone()

                if row:
                    person_dict = dict(row)
                    person_dict['created_at'] = datetime.fromisoformat(person_dict['created_at'])
                    person_dict['updated_at'] = datetime.fromisoformat(person_dict['updated_at'])
                    return person_dict

                return None

        except Exception as e:
            logger.error(f"Failed to get person {person_id}: {e}")
            return None

    def get_all_persons(self) -> List[Dict[str, Any]]:
        """Get all person records"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM persons ORDER BY name")
                rows = cursor.fetchall()

                persons = []
                for row in rows:
                    person_dict = dict(row)
                    person_dict['created_at'] = datetime.fromisoformat(person_dict['created_at'])
                    person_dict['updated_at'] = datetime.fromisoformat(person_dict['updated_at'])
                    persons.append(person_dict)

                return persons

        except Exception as e:
            logger.error(f"Failed to get all persons: {e}")
            return []

    def add_camera(self, camera: CameraRecord) -> bool:
        """Add a camera record to the database"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT OR REPLACE INTO cameras (
                            camera_id, location, rtsp_url, is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        camera.camera_id,
                        camera.location,
                        camera.rtsp_url,
                        camera.is_active,
                        camera.created_at.isoformat(),
                        camera.updated_at.isoformat()
                    ))

                    conn.commit()
                    logger.debug(f"Added camera record: {camera.camera_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to add camera record: {e}")
            return False

    def get_all_cameras(self) -> List[Dict[str, Any]]:
        """Get all camera records"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cameras ORDER BY camera_id")
                rows = cursor.fetchall()

                cameras = []
                for row in rows:
                    camera_dict = dict(row)
                    camera_dict['created_at'] = datetime.fromisoformat(camera_dict['created_at'])
                    camera_dict['updated_at'] = datetime.fromisoformat(camera_dict['updated_at'])
                    cameras.append(camera_dict)

                return cameras

        except Exception as e:
            logger.error(f"Failed to get all cameras: {e}")
            return []

    def get_violation_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get violation statistics for the last N days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Total violations
                cursor.execute(
                    "SELECT COUNT(*) FROM violations WHERE timestamp >= ? AND timestamp <= ?",
                    (start_date.isoformat(), end_date.isoformat())
                )
                total_violations = cursor.fetchone()[0]

                # Violations by type
                cursor.execute('''
                    SELECT violation_type, COUNT(*) as count
                    FROM violations
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY violation_type
                    ORDER BY count DESC
                ''', (start_date.isoformat(), end_date.isoformat()))

                violations_by_type = {row[0]: row[1] for row in cursor.fetchall()}

                # Violations by camera
                cursor.execute('''
                    SELECT camera_id, COUNT(*) as count
                    FROM violations
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY camera_id
                    ORDER BY count DESC
                ''', (start_date.isoformat(), end_date.isoformat()))

                violations_by_camera = {row[0]: row[1] for row in cursor.fetchall()}

                # Daily violation counts
                cursor.execute('''
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM violations
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                ''', (start_date.isoformat(), end_date.isoformat()))

                daily_counts = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "period_days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_violations": total_violations,
                    "violations_by_type": violations_by_type,
                    "violations_by_camera": violations_by_camera,
                    "daily_counts": daily_counts
                }

        except Exception as e:
            logger.error(f"Failed to get violation statistics: {e}")
            return {}

    def cleanup_old_records(self, days: int = 30) -> Dict[str, int]:
        """Clean up violation records older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Count records to be deleted
                    cursor.execute(
                        "SELECT COUNT(*) FROM violations WHERE timestamp < ?",
                        (cutoff_date.isoformat(),)
                    )
                    records_to_delete = cursor.fetchone()[0]

                    # Delete old records
                    cursor.execute(
                        "DELETE FROM violations WHERE timestamp < ?",
                        (cutoff_date.isoformat(),)
                    )

                    deleted_count = cursor.rowcount
                    conn.commit()

                    logger.info(f"Cleaned up {deleted_count} old violation records")

                    return {
                        "deleted_count": deleted_count,
                        "cutoff_date": cutoff_date.isoformat()
                    }

        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return {"deleted_count": 0}

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get table counts
                cursor.execute("SELECT COUNT(*) FROM violations")
                violation_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM persons")
                person_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM cameras")
                camera_count = cursor.fetchone()[0]

                # Get database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                return {
                    "database_path": str(self.db_path),
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2),
                    "violation_count": violation_count,
                    "person_count": person_count,
                    "camera_count": camera_count
                }

        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}

    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            with self._lock:
                with self._get_connection() as source:
                    with sqlite3.connect(str(backup_path)) as backup:
                        source.backup(backup)

            logger.info(f"Database backed up to: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False

    def execute_custom_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a custom SQL query (for advanced users)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if query.strip().upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    conn.commit()
                    return [{"affected_rows": cursor.rowcount}]

        except Exception as e:
            logger.error(f"Failed to execute custom query: {e}")
            return [{"error": str(e)}]