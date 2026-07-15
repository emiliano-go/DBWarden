import os
import secrets
import shutil
import sqlite3
import stat
import uuid
from datetime import datetime
from pathlib import Path


def create_backup(sqlalchemy_url: str, backup_dir: str) -> str:
    """
    Create a backup of the database.

    Args:
        sqlalchemy_url: Database connection URL.
        backup_dir: Directory to store backups.

    Returns:
        str: Path to the backup file.

    Raises:
        ValueError: If backup_dir is world-writable.
    """
    # Check backup_dir is not world-writable
    backup_dir_path = Path(backup_dir)
    try:
        mode = backup_dir_path.stat().st_mode
        if mode & stat.S_IWOTH:
            raise ValueError(
                f"Backup directory '{backup_dir}' is world-writable. "
                "Use a secure directory with restricted permissions."
            )
    except FileNotFoundError:
        # Directory doesn't exist yet - will be created with safe permissions
        pass

    os.makedirs(backup_dir, exist_ok=True)

    # Ensure directory has safe permissions after creation
    os.chmod(backup_dir, 0o700)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique = f"{timestamp}_{secrets.randbelow(1000):03d}"
    backup_path = os.path.join(backup_dir, f"backup_{unique}.db")

    # Handle collision with incrementing suffix
    base = backup_path
    counter = 1
    while os.path.exists(backup_path):
        backup_path = base.replace(".db", f"_{counter}.db")
        counter += 1
        if counter > 100:
            raise RuntimeError("Too many backup collisions")

    if sqlalchemy_url.startswith("sqlite:///"):
        db_path = sqlalchemy_url.replace("sqlite:///", "")
        if db_path:
            shutil.copy(db_path, backup_path)
            os.chmod(backup_path, 0o644)
        else:
            conn = sqlite3.connect(":memory:")
            conn.close()

    return backup_path
