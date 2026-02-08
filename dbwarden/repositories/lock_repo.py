from typing import Optional

from sqlalchemy import text

from dbwarden.database.connection import get_db_connection
from dbwarden.database.queries import SQL_QUERIES, QueryMethod


def get_query(method: QueryMethod, **kwargs) -> str:
    """Get a SQL query by method."""
    return SQL_QUERIES.get(method, "")


def create_lock_table_if_not_exists() -> None:
    """Create the lock table if it doesn't exist."""
    with get_db_connection() as connection:
        connection.execute(text(get_query(QueryMethod.CREATE_LOCK_TABLE)))


def acquire_lock() -> bool:
    """Attempt to acquire the migration lock."""
    try:
        with get_db_connection() as connection:
            connection.execute(text(get_query(QueryMethod.ACQUIRE_LOCK)))
        return True
    except Exception:
        return False


def release_lock() -> bool:
    """Release the migration lock."""
    try:
        with get_db_connection() as connection:
            connection.execute(text(get_query(QueryMethod.RELEASE_LOCK)))
        return True
    except Exception:
        return False


def check_lock() -> bool:
    """Check if migration lock is currently held."""
    try:
        with get_db_connection() as connection:
            result = connection.execute(text(get_query(QueryMethod.CHECK_LOCK)))
            locked = result.scalar_one_or_none()
            return locked is True
    except Exception:
        return False
