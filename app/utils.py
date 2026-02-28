import os
import shutil
from datetime import datetime
from flask import current_app
from sqlalchemy import extract

from app import db 
from app.models import TimeSlot, AuditLog


def calculate_user_quota_stats(user, server):
    """
    Calculates the user's quota usage FOR THE CURRENT MONTH only.
    Strict limits: Max 8 per month.
    """
    MAX_MONTHLY_LIMIT = 8  # Hard limit requested

    now = datetime.now()

    # 1. Calculate Usage (Count reserved slots in CURRENT MONTH only)
    used_quota = TimeSlot.query.filter(
        TimeSlot.server_id == server.id, # type: ignore
        TimeSlot.reserved_by_user_id == user.id,
        extract("year", TimeSlot.start_time) == now.year, # type: ignore
        extract("month", TimeSlot.start_time) == now.month, # type: ignore
    ).count()

    # 2. Calculate Percentage
    usage_percent = 0
    if MAX_MONTHLY_LIMIT > 0:
        usage_percent = (used_quota / MAX_MONTHLY_LIMIT) * 100

    return {
        "max": MAX_MONTHLY_LIMIT,
        "used": used_quota,
        "remaining": MAX_MONTHLY_LIMIT - used_quota,
        "percent": round(usage_percent, 1),
        "status": "danger" if used_quota >= MAX_MONTHLY_LIMIT else "success",
    }


def backup_database():
    """
    Creates a timestamped copy of the SQLite database in a 'backups' folder.
    Returns the filename of the backup or None if failed.
    """
    # 1. Get the database path from Flask config
    # URI format is usually 'sqlite:///site.db', we need just 'site.db'
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri.startswith("sqlite:///"):
        return None, "Not using SQLite, cannot backup file directly."

    db_path = db_uri.replace("sqlite:///", "")

    # Handle absolute vs relative paths
    base_dir = os.path.abspath(os.path.dirname(__file__))  # app/
    root_dir = os.path.dirname(base_dir)  # project root/

    # Determine source file location
    source_path = os.path.join(root_dir, db_path)

    # 2. Verify source exists
    if not os.path.exists(source_path):
        # Try looking in 'instance' folder (common Flask pattern)
        source_path = os.path.join(root_dir, "instance", db_path)
        if not os.path.exists(source_path):
            return None, f"Database file not found at {source_path}"

    # 3. Create 'backups' directory if it doesn't exist
    backup_dir = os.path.join(root_dir, "backups")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # 4. Create destination filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    destination_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(source_path, destination_path)
        return backup_filename, None
    except Exception as e:
        return None, str(e)


def log_action(user_id, action, details):
    """
    Records an event to the Audit Log.
    """
    try:
        log = AuditLog(user_id=user_id, action=action, details=details)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Logging Failed: {e}")
        # We don't want logging errors to crash the main app, so we just print it
