from sqlalchemy import text

from dbwarden.database.connection import get_db_connection
from dbwarden.database.queries import QueryMethod, get_query


def create_lock_table_if_not_exists(db_name: str | None = None) -> None:
    """Create the lock table if it doesn't exist."""
    with get_db_connection(db_name) as connection:
        connection.execute(text(get_query(QueryMethod.CREATE_LOCK_TABLE, db_name)))


def acquire_lock(db_name: str | None = None) -> bool:
    """Attempt to acquire the migration lock."""
    try:
        with get_db_connection(db_name) as connection:
            connection.execute(text(get_query(QueryMethod.ACQUIRE_LOCK, db_name)))
        return True
    except Exception:
        return False


def release_lock(db_name: str | None = None) -> bool:
    """Release the migration lock."""
    try:
        with get_db_connection(db_name) as connection:
            connection.execute(text(get_query(QueryMethod.RELEASE_LOCK, db_name)))
        return True
    except Exception:
        return False


def check_lock(db_name: str | None = None) -> bool:
    """Check if migration lock is currently held."""
    try:
        with get_db_connection(db_name) as connection:
            result = connection.execute(
                text(get_query(QueryMethod.CHECK_LOCK, db_name))
            )
            locked = result.scalar_one_or_none()
            return locked is True
    except Exception:
        return False
