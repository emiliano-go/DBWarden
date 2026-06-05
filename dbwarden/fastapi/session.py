from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
import threading

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dbwarden.config import get_database
from dbwarden.fastapi.runtime import runtime_flags

_SESSION_FACTORIES: dict[str, async_sessionmaker[AsyncSession]] = {}
_SESSION_LOCK = threading.Lock()


def _to_async_url(url: str, database_type: str) -> tuple[str, str]:
    """Convert URL to async driver.
    
    Returns:
        tuple of (safe_cache_key, async_url)
        - safe_cache_key: URL with hidden password for use as dict key
        - async_url: Full URL with async driver for engine creation
    """
    parsed = make_url(url)
    drivername = parsed.drivername

    # Create safe cache key with hidden password
    safe_key = parsed.render_as_string(hide_password=True)

    if "+" in drivername:
        return safe_key, parsed.render_as_string(hide_password=False)

    if database_type == "postgresql" or drivername.startswith("postgres"):
        drivername = "postgresql+asyncpg"
    elif database_type == "sqlite" or drivername.startswith("sqlite"):
        drivername = "sqlite+aiosqlite"
    else:
        raise ValueError(
            f"get_session currently supports async PostgreSQL and SQLite drivers. Unsupported database_type: {database_type}"
        )

    full_async_url = parsed.set(drivername=drivername).render_as_string(hide_password=False)
    return safe_key, full_async_url


def _session_factory(database: str | None = None, dev: bool = False) -> async_sessionmaker[AsyncSession]:
    with runtime_flags(dev=dev, strict_translation=False):
        config = get_database(database)
    
    url = config.sqlalchemy_url_async or config.sqlalchemy_url
    cache_key, async_url = _to_async_url(url, config.database_type)
    
    # Thread-safe check and create
    with _SESSION_LOCK:
        if cache_key in _SESSION_FACTORIES:
            return _SESSION_FACTORIES[cache_key]

        engine = create_async_engine(async_url, future=True)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        _SESSION_FACTORIES[cache_key] = factory
        return factory


def get_session(database: str | None = None, *, dev: bool = False) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Return a FastAPI dependency that yields AsyncSession.

    Example:
        session_dep = get_session()
        async def route(session: Annotated[AsyncSession, Depends(session_dep)]):
            ...
    """

    async def _dependency() -> AsyncGenerator[AsyncSession, None]:
        factory = _session_factory(database=database, dev=dev)
        async with factory() as session:
            yield session

    return _dependency
