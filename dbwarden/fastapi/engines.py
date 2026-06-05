from __future__ import annotations

import threading
from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from dbwarden.config import get_database
from dbwarden.fastapi.runtime import runtime_flags

_ASYNC_SESSION_FACTORIES: dict[str, async_sessionmaker[AsyncSession]] = {}
_SYNC_SESSION_FACTORIES: dict[str, sessionmaker[Session]] = {}
_CLICKHOUSE_ASYNC_CLIENTS: dict[str, Any] = {}
_CLICKHOUSE_SYNC_CLIENTS: dict[str, Any] = {}
_LOCK = threading.Lock()


def _to_async_url(url: str, database_type: str) -> tuple[str, str]:
    """Convert URL to async driver format.

    Returns:
        Tuple of (safe_cache_key, async_url).
    """
    parsed = make_url(url)
    safe_key = parsed.render_as_string(hide_password=True)

    if "+" in parsed.drivername:
        return safe_key, parsed.render_as_string(hide_password=False)

    if database_type in ("postgresql",) or parsed.drivername.startswith("postgres"):
        drivername = "postgresql+asyncpg"
    elif database_type in ("sqlite",) or parsed.drivername.startswith("sqlite"):
        drivername = "sqlite+aiosqlite"
    else:
        raise ValueError(
            f"get_session currently supports async PostgreSQL and SQLite drivers. "
            f"Unsupported database_type: {database_type}"
        )

    full_url = parsed.set(drivername=drivername).render_as_string(hide_password=False)
    return safe_key, full_url


def _async_session_factory(name: str, dev: bool = False) -> async_sessionmaker[AsyncSession]:
    with runtime_flags(dev=dev, strict_translation=False):
        config = get_database(name)

    url = config.sqlalchemy_url_async or config.sqlalchemy_url
    cache_key, async_url = _to_async_url(url, config.database_type)

    with _LOCK:
        if cache_key in _ASYNC_SESSION_FACTORIES:
            return _ASYNC_SESSION_FACTORIES[cache_key]

        engine = create_async_engine(async_url, future=True)
        factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        _ASYNC_SESSION_FACTORIES[cache_key] = factory
        return factory


def _make_session_dep(name: str, dev: bool = False):
    """Return a FastAPI dependency that yields a new AsyncSession per request."""

    async def _dependency() -> AsyncGenerator[AsyncSession, None]:
        factory = _async_session_factory(name, dev=dev)
        async with factory() as session:
            yield session

    return _dependency


def _sync_session_factory(name: str, dev: bool = False) -> sessionmaker[Session]:
    with runtime_flags(dev=dev, strict_translation=False):
        config = get_database(name)

    url = config.sqlalchemy_url_sync or config.sqlalchemy_url

    with _LOCK:
        if url in _SYNC_SESSION_FACTORIES:
            return _SYNC_SESSION_FACTORIES[url]

        engine = create_engine(url)
        factory = sessionmaker(bind=engine)
        _SYNC_SESSION_FACTORIES[url] = factory
        return factory


def _make_sync_session_dep(name: str, dev: bool = False):
    """Return a FastAPI dependency that yields a new sync Session per request."""

    def _dependency() -> Generator[Session, None, None]:
        factory = _sync_session_factory(name, dev=dev)
        with factory() as session:
            yield session

    return _dependency


def _parse_clickhouse_url(url: str) -> dict[str, Any]:
    """Parse a ClickHouse URL into connection kwargs."""
    parsed = make_url(url)
    kwargs: dict[str, Any] = {
        "host": parsed.host or "localhost",
        "port": parsed.port or 8123,
        "database": parsed.database or "default",
    }
    if parsed.username:
        kwargs["username"] = parsed.username
    if parsed.password:
        kwargs["password"] = parsed.password
    return kwargs


def _make_clickhouse_dep(name: str, dev: bool = False):
    """Return a FastAPI dependency that yields a shared AsyncClient."""

    async def _dependency() -> AsyncGenerator[Any, None]:
        if name not in _CLICKHOUSE_ASYNC_CLIENTS:
            import clickhouse_connect

            with runtime_flags(dev=dev, strict_translation=False):
                config = get_database(name)

            conn_kwargs = _parse_clickhouse_url(config.sqlalchemy_url)
            client = await clickhouse_connect.get_async_client(**conn_kwargs)
            _CLICKHOUSE_ASYNC_CLIENTS[name] = client

        yield _CLICKHOUSE_ASYNC_CLIENTS[name]

    return _dependency


def _make_sync_clickhouse_dep(name: str, dev: bool = False):
    """Return a FastAPI dependency that yields a shared sync ClickHouse client."""

    def _dependency() -> Generator[Any, None, None]:
        if name not in _CLICKHOUSE_SYNC_CLIENTS:
            import clickhouse_connect

            with runtime_flags(dev=dev, strict_translation=False):
                config = get_database(name)

            conn_kwargs = _parse_clickhouse_url(config.sqlalchemy_url)
            client = clickhouse_connect.get_client(**conn_kwargs)
            _CLICKHOUSE_SYNC_CLIENTS[name] = client

        yield _CLICKHOUSE_SYNC_CLIENTS[name]

    return _dependency


def dispose_engines() -> None:
    """Close all cached engines and clients.

    Call during FastAPI shutdown:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            dispose_engines()
    """
    _CLICKHOUSE_ASYNC_CLIENTS.clear()
    _CLICKHOUSE_SYNC_CLIENTS.clear()
    _ASYNC_SESSION_FACTORIES.clear()
    _SYNC_SESSION_FACTORIES.clear()
