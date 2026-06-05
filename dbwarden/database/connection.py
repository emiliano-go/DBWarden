import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dbwarden.config import get_database
from dbwarden.logging import get_logger


def _convert_url_to_clickhouse_dialect(url: str) -> str:
    """Convert HTTP URL to clickhouse-connect dialect format."""
    if url.startswith("http://"):
        url = url.replace("http://", "", 1)
    elif url.startswith("https://"):
        url = url.replace("https://", "", 1)

    if "@" in url:
        parts = url.split("@", 1)
        before_at = parts[0]
        after_at = parts[1]

        if ":" in before_at:
            user, password = before_at.split(":", 1)
        else:
            user = ""
            password = ""

        if "/" in after_at:
            host_port, db = after_at.split("/", 1)
            db_path = f"/{db}"
        else:
            host_port = after_at
            db_path = ""

        if user:
            if password:
                return f"clickhousedb://{user}:{password}@{host_port}{db_path}"
            else:
                return f"clickhousedb://{user}@{host_port}{db_path}"
        else:
            return f"clickhousedb://{host_port}{db_path}"

    return f"clickhousedb://{url}"


@lru_cache(maxsize=4)
def _get_engine(url: str, db_type: str = "postgresql") -> Engine:
    """Create SQLAlchemy engine with dialect-specific URL handling."""
    if db_type == "clickhouse":
        url = _convert_url_to_clickhouse_dialect(url)
    return create_engine(url=url)


def _get_engine_key(url: str, db_type: str) -> tuple[str, str]:
    """Cache key for engine - includes db_type for ClickHouse URL conversion."""
    return (url, db_type)


_engine_cache: dict[tuple[str, str], Engine] = {}


def _get_engine(url: str, db_type: str = "postgresql") -> Engine:
    """Create SQLAlchemy engine with dialect-specific URL handling."""
    key = (url, db_type)
    if key in _engine_cache:
        return _engine_cache[key]

    final_url = url
    if db_type == "clickhouse":
        final_url = _convert_url_to_clickhouse_dialect(url)

    engine = create_engine(url=final_url)
    _engine_cache[key] = engine
    return engine


_connection_init_logged = False


def reset_connection_logging() -> None:
    """Reset the connection init logging flag for new CLI invocations."""
    global _connection_init_logged
    _connection_init_logged = False


_SANDBOX_URL: str | None = None
_SANDBOX_DB_TYPE: str | None = None


def set_sandbox_override(url: str, db_type: str) -> None:
    """Set the sandbox database URL override for the current process."""
    global _SANDBOX_URL, _SANDBOX_DB_TYPE
    _SANDBOX_URL = url
    _SANDBOX_DB_TYPE = db_type


def clear_sandbox_override() -> None:
    """Clear the sandbox database URL override."""
    global _SANDBOX_URL, _SANDBOX_DB_TYPE
    _SANDBOX_URL = None
    _SANDBOX_DB_TYPE = None


@contextmanager
def sandbox_override(url: str, db_type: str):
    """Context manager that temporarily sets the sandbox override."""
    set_sandbox_override(url, db_type)
    try:
        yield
    finally:
        clear_sandbox_override()


@contextmanager
def get_db_connection(db_name: str | None = None) -> Generator[Any, None, None]:
    """
    Context manager that yields a database connection.

    Args:
        db_name: Database name from config. If None, uses default database.
    """
    global _connection_init_logged
    config = get_database(db_name)

    url = _SANDBOX_URL if _SANDBOX_URL is not None else config.sqlalchemy_url
    db_type = _SANDBOX_DB_TYPE if _SANDBOX_DB_TYPE is not None else config.database_type

    from sqlalchemy.engine import make_url
    parsed = make_url(url)
    actual_db_name = db_name or (parsed.database or "default")
    logger = get_logger(
        db_name=actual_db_name,
        db_type=db_type,
    )

    engine = _get_engine(url, db_type)

    if not _connection_init_logged:
        logger.log_connection_init(db_type)
        _connection_init_logged = True

    with engine.begin() as connection:
        postgres_schema = config.postgres_schema
        if postgres_schema:
            connection.execute(
                text("SET search_path TO :postgres_schema"),
                parameters={"postgres_schema": postgres_schema},
            )
        yield connection


def get_engine(db_name: str | None = None) -> Engine:
    """
    Get SQLAlchemy engine for the specified database.

    Args:
        db_name: Database name from config. If None, uses default database.

    Returns:
        SQLAlchemy Engine instance.
    """
    config = get_database(db_name)
    return _get_engine(config.sqlalchemy_url, config.database_type)
