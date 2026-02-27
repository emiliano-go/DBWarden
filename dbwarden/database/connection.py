import logging
import os
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from typing import Any, AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from dbwarden.config import get_config
from dbwarden.logging import get_logger


@lru_cache(maxsize=1)
def _get_engine(url: str) -> Engine:
    return create_engine(url=url)


@lru_cache(maxsize=1)
def _get_async_engine(url: str) -> AsyncEngine:
    return create_async_engine(url=url)


_connection_init_logged = False


def reset_connection_logging() -> None:
    """Reset the connection init logging flag for new CLI invocations."""
    global _connection_init_logged
    _connection_init_logged = False


def is_async_enabled() -> bool:
    """
    Check if async mode is enabled.

    Returns:
        bool: True if async mode is enabled.
    """
    async_env = os.getenv("DBWARDEN_ASYNC", "").lower()
    if async_env in ("true", "1", "yes"):
        return True
    if async_env in ("false", "0", "no"):
        return False

    try:
        config = get_config()
        return config.async_mode
    except Exception:
        return False


def get_mode() -> str:
    """
    Get the current execution mode.

    Returns:
        str: "async" or "sync"
    """
    return "async" if is_async_enabled() else "sync"


def _make_sync_url(url: str) -> str:
    """Convert an async URL to sync by removing async driver suffixes."""
    url = url.replace("+asyncpg", "")
    url = url.replace("+async", "")
    url = url.replace("+aiosqlite", "")
    return url


@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """
    Context manager that yields a database connection.

    Works in sync mode. Converts async URLs to sync URLs.
    """
    global _connection_init_logged
    logger = get_logger()
    config = get_config()
    url = _make_sync_url(config.sqlalchemy_url)

    engine = _get_engine(url)

    mode = get_mode()
    if not _connection_init_logged:
        logger.log_connection_init(mode)
        _connection_init_logged = True

    with engine.begin() as connection:
        postgres_schema = config.postgres_schema
        if postgres_schema:
            connection.execute(
                text("SET search_path TO :postgres_schema"),
                parameters={"postgres_schema": postgres_schema},
            )
        yield connection


@asynccontextmanager
async def get_async_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """
    Context manager that yields an async database connection.

    Only works when ASYNC=true.
    """
    global _connection_init_logged
    if not is_async_enabled():
        raise RuntimeError(
            "ASYNC=false but using async connection. "
            "Set DBWARDEN_ASYNC=true to use async mode."
        )

    logger = get_logger()
    config = get_config()
    async_engine = _get_async_engine(config.sqlalchemy_url)

    if not _connection_init_logged:
        logger.log_connection_init("async")
        _connection_init_logged = True

    async with async_engine.begin() as connection:
        postgres_schema = config.postgres_schema
        if postgres_schema:
            await connection.execute(
                text("SET search_path TO :postgres_schema"),
                parameters={"postgres_schema": postgres_schema},
            )
        yield connection
