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


def is_async_enabled() -> bool:
    """
    Check if async mode is enabled.

    Returns:
        bool: True if async mode is enabled.
    """
    async_env = os.getenv("STRATA_ASYNC", "").lower()
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

    Works in sync mode by default.
    """
    logger = get_logger()
    config = get_config()
    url = config.sqlalchemy_url

    if is_async_enabled():
        url = _make_sync_url(url)

    engine = create_engine(url=url)

    logger.log_connection_init("sync")

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
    if not is_async_enabled():
        raise RuntimeError(
            "ASYNC=false but using async connection. "
            "Set STRATA_ASYNC=true to use async mode."
        )

    logger = get_logger()
    config = get_config()
    async_engine = create_async_engine(url=config.sqlalchemy_url)

    logger.log_connection_init("async")

    async with async_engine.begin() as connection:
        postgres_schema = config.postgres_schema
        if postgres_schema:
            await connection.execute(
                text("SET search_path TO :postgres_schema"),
                parameters={"postgres_schema": postgres_schema},
            )
        yield connection
