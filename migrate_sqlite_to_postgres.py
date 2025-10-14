"""
Migrate data from SQLite to PostgreSQL
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection settings
PG_DATABASE = "motion-detector"
PG_USER = "face-motion"
PG_PASSWORD = "kkk12345"
PG_HOST = "localhost"
PG_PORT = "5432"

# SQLite database path
SQLITE_DB = "data/monitoring.db"

def get_postgres_connection():
    """Create PostgreSQL engine and session"""
    database_url = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return engine, Session()

def get_sqlite_connection():
    """Create SQLite connection"""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_table(table_name, sqlite_conn, pg_session, column_mapping=None, transform_fn=None):
    """
    Migrate a table from SQLite to PostgreSQL

    Args:
        table_name: Name of the table
        sqlite_conn: SQLite connection
        pg_session: PostgreSQL session
        column_mapping: Dict mapping SQLite columns to PostgreSQL columns
        transform_fn: Function to transform row data before insertion
    """
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            print(f"  [INFO] No data in {table_name}")
            return 0, 0

        print(f"  [INFO] Found {len(rows)} rows in {table_name}")

        migrated = 0
        errors = 0

        for row in rows:
            try:
                # Convert row to dict
                row_dict = dict(row)

                # Apply column mapping if provided
                if column_mapping:
                    row_dict = {column_mapping.get(k, k): v for k, v in row_dict.items()}

                # Apply transformation function if provided
                if transform_fn:
                    row_dict = transform_fn(row_dict)

                # Build INSERT query
                columns = list(row_dict.keys())
                placeholders = [f":{col}" for col in columns]

                query = f"""
                    INSERT INTO {table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """

                pg_session.execute(text(query), row_dict)
                pg_session.commit()  # Commit each row to avoid transaction failures
                migrated += 1

            except Exception as e:
                pg_session.rollback()  # Rollback failed transaction
                errors += 1
                print(f"    [ERROR] Failed to migrate row: {e}")
                if errors <= 3:  # Only show first 3 errors
                    print(f"      Row data: {dict(row)}")

        print(f"  [OK] Migrated {migrated} rows, {errors} errors")
        return migrated, errors

    except Exception as e:
        print(f"  [ERROR] Failed to migrate {table_name}: {e}")
        pg_session.rollback()
        return 0, 0

def fix_binary_data(value):
    """Convert binary data to integer if needed"""
    if isinstance(value, bytes):
        # Convert bytes to integer (little-endian)
        return int.from_bytes(value, byteorder='little', signed=False)
    return value

def convert_boolean(value):
    """Convert SQLite integer boolean to Python boolean"""
    if isinstance(value, int):
        return bool(value)
    return value

def convert_json_string(value):
    """Convert 'null' string to None for JSON fields"""
    if value == 'null':
        return None
    return value

def convert_datetime(value):
    """Convert datetime string to datetime object"""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except:
            pass
    return value

def transform_stream_sources_row(row_dict):
    """Transform stream_sources table row data"""
    # Convert boolean fields
    row_dict['enabled'] = convert_boolean(row_dict.get('enabled'))

    # Convert JSON fields
    row_dict['config'] = convert_json_string(row_dict.get('config'))

    # Convert datetime fields
    if 'created_at' in row_dict:
        row_dict['created_at'] = convert_datetime(row_dict['created_at'])
    if 'updated_at' in row_dict:
        row_dict['updated_at'] = convert_datetime(row_dict['updated_at'])

    return row_dict

def transform_detection_rules_row(row_dict):
    """Transform detection_rules table row data"""
    # Convert boolean fields
    row_dict['enabled'] = convert_boolean(row_dict.get('enabled'))
    row_dict['notification_enabled'] = convert_boolean(row_dict.get('notification_enabled'))
    row_dict['schedule_enabled'] = convert_boolean(row_dict.get('schedule_enabled'))

    # Convert JSON fields
    for field in ['stream_source_ids', 'person_ids', 'detection_types',
                   'notification_config', 'schedule_config']:
        if field in row_dict:
            value = row_dict[field]
            # Parse JSON string if it's a valid JSON
            if isinstance(value, str):
                if value == 'null':
                    row_dict[field] = None
                else:
                    # Keep as string for PostgreSQL JSON type
                    import json
                    try:
                        # Validate it's valid JSON
                        json.loads(value)
                    except:
                        row_dict[field] = None

    # Convert datetime fields
    if 'created_at' in row_dict:
        row_dict['created_at'] = convert_datetime(row_dict['created_at'])
    if 'updated_at' in row_dict:
        row_dict['updated_at'] = convert_datetime(row_dict['updated_at'])

    return row_dict

def transform_violations_row(row_dict):
    """Transform violations table row data"""
    # Fix binary encoded integers
    row_dict['bbox_x'] = fix_binary_data(row_dict.get('bbox_x'))
    row_dict['bbox_y'] = fix_binary_data(row_dict.get('bbox_y'))
    row_dict['bbox_width'] = fix_binary_data(row_dict.get('bbox_width'))
    row_dict['bbox_height'] = fix_binary_data(row_dict.get('bbox_height'))

    # Ensure timestamp is in proper format
    if 'timestamp' in row_dict and isinstance(row_dict['timestamp'], str):
        try:
            row_dict['timestamp'] = datetime.fromisoformat(row_dict['timestamp'])
        except:
            pass

    # Remove or rename columns that don't exist in PostgreSQL schema
    if 'created_at' in row_dict:
        del row_dict['created_at']  # This will be auto-generated

    # Map to PostgreSQL schema
    # Note: The violations table in models.py has different columns than SQLite
    # We need to map accordingly
    new_dict = {
        'violation_id': row_dict.get('id'),
        'timestamp': row_dict.get('timestamp'),
        'camera_id': row_dict.get('camera_id'),
        'violation_type': row_dict.get('violation_type'),
        'person_id': row_dict.get('person_id'),
        'confidence': row_dict.get('confidence'),
        'bbox_x': row_dict.get('bbox_x'),
        'bbox_y': row_dict.get('bbox_y'),
        'bbox_width': row_dict.get('bbox_width'),
        'bbox_height': row_dict.get('bbox_height'),
        'image_path': row_dict.get('image_path'),
        'extra_data': row_dict.get('additional_data'),  # Map additional_data to extra_data
        'status': 'new',  # Default status
    }

    return new_dict

def transform_cameras_row(row_dict):
    """Transform cameras table row data - map to stream_sources"""
    # Map cameras to stream_sources table
    new_dict = {
        'stream_id': row_dict.get('camera_id'),
        'name': row_dict.get('camera_id', 'Unknown'),
        'stream_type': 'RTSP',  # Default type
        'url': row_dict.get('rtsp_url'),
        'location': row_dict.get('location'),
        'enabled': bool(row_dict.get('is_active', True)),
        'status': 'active' if row_dict.get('is_active', True) else 'inactive',
    }

    # Handle created_at and updated_at
    if 'created_at' in row_dict:
        try:
            new_dict['created_at'] = datetime.fromisoformat(row_dict['created_at'])
        except:
            pass
    if 'updated_at' in row_dict:
        try:
            new_dict['updated_at'] = datetime.fromisoformat(row_dict['updated_at'])
        except:
            pass

    return new_dict

def main():
    """Main migration function"""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"Source: {SQLITE_DB}")
    print(f"Target: postgresql://{PG_HOST}:{PG_PORT}/{PG_DATABASE}")
    print()

    try:
        # Connect to databases
        print("Connecting to databases...")
        sqlite_conn = get_sqlite_connection()
        pg_engine, pg_session = get_postgres_connection()
        print("[OK] Connected to both databases")
        print()

        total_migrated = 0
        total_errors = 0

        # Migrate tables with data
        tables_to_migrate = [
            # (table_name, transform_function)
            ('stream_sources', transform_stream_sources_row),
            ('detection_rules', transform_detection_rules_row),
            ('violations', transform_violations_row),
        ]

        # Also migrate cameras table to stream_sources (if not already done)
        print("[INFO] Migrating cameras data to stream_sources...")
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM cameras")
        camera_rows = cursor.fetchall()

        if camera_rows:
            print(f"  [INFO] Found {len(camera_rows)} camera records")
            for row in camera_rows:
                try:
                    row_dict = dict(row)
                    transformed = transform_cameras_row(row_dict)

                    # Check if stream_id already exists
                    result = pg_session.execute(
                        text("SELECT id FROM stream_sources WHERE stream_id = :stream_id"),
                        {'stream_id': transformed['stream_id']}
                    ).fetchone()

                    if not result:
                        columns = list(transformed.keys())
                        placeholders = [f":{col}" for col in columns]
                        query = f"""
                            INSERT INTO stream_sources ({', '.join(columns)})
                            VALUES ({', '.join(placeholders)})
                        """
                        pg_session.execute(text(query), transformed)
                        total_migrated += 1
                    else:
                        print(f"    [SKIP] stream_id {transformed['stream_id']} already exists")

                except Exception as e:
                    total_errors += 1
                    print(f"    [ERROR] Failed to migrate camera: {e}")

            pg_session.commit()
            print(f"  [OK] Camera migration completed")
        print()

        # Migrate other tables
        for table_name, transform_fn in tables_to_migrate:
            print(f"[INFO] Migrating {table_name}...")
            migrated, errors = migrate_table(
                table_name,
                sqlite_conn,
                pg_session,
                transform_fn=transform_fn
            )
            total_migrated += migrated
            total_errors += errors
            print()

        # Close connections
        sqlite_conn.close()
        pg_session.close()

        print("=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"Total rows migrated: {total_migrated}")
        print(f"Total errors: {total_errors}")
        print()

        if total_errors == 0:
            print("[OK] Migration completed successfully!")
            return True
        else:
            print("[WARNING] Migration completed with some errors")
            return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
