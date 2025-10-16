"""
Test application connection to PostgreSQL
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("Testing Application PostgreSQL Connection")
print("=" * 60)
print()

try:
    # Import database module
    from api.database import DATABASE_URL, engine, SessionLocal
    from api.models import StreamSource, DetectionRule, Violation
    from sqlalchemy import text

    print(f"[INFO] Database URL: {DATABASE_URL}")
    print()

    # Test connection
    print("[INFO] Testing database connection...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.scalar()
        print(f"[OK] Connected to PostgreSQL!")
        print(f"     Version: {version}")
    print()

    # Test session
    print("[INFO] Testing database session...")
    session = SessionLocal()

    # Query stream sources
    stream_sources = session.query(StreamSource).all()
    print(f"[OK] Found {len(stream_sources)} stream sources:")
    for stream in stream_sources:
        print(f"     - {stream.stream_id}: {stream.name} ({stream.stream_type})")
    print()

    # Query detection rules
    detection_rules = session.query(DetectionRule).all()
    print(f"[OK] Found {len(detection_rules)} detection rules:")
    for rule in detection_rules:
        print(f"     - {rule.rule_id}: {rule.name} (enabled: {rule.enabled})")
    print()

    # Query violations (count only)
    violation_count = session.query(Violation).count()
    print(f"[OK] Found {violation_count:,} violations in database")
    print()

    # Get recent violations
    recent_violations = session.query(Violation).order_by(Violation.timestamp.desc()).limit(3).all()
    print(f"[INFO] Recent violations:")
    for viol in recent_violations:
        print(f"     - {viol.violation_id}: {viol.violation_type} at {viol.camera_id} ({viol.timestamp})")
    print()

    session.close()

    print("=" * 60)
    print("[OK] Application PostgreSQL Connection Test PASSED!")
    print("=" * 60)
    print("\nYour application is now using PostgreSQL database.")
    print("Database: motion-detector")
    print("User: face-motion")

except Exception as e:
    print(f"\n[ERROR] Connection test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
