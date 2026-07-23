from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from clickhouse_connect.driver.asyncclient import AsyncClient
    from clickhouse_connect.driver.client import Client as SyncClickHouseClient
    from fastapi.params import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session


class DatabaseHandle:
    """Handle returned by ``database_config()``.

    The ``.async_session`` and ``.sync_session`` properties return type
    annotations FastAPI can consume directly as route parameter type hints::

        # dbwarden.py
        from dbwarden import database_config
        primary = database_config(database_name="primary", ...)

        # routes.py
        from ..dbwarden import primary

        @router.get("/users")
        async def users(session: primary.async_session):
            ...

        @router.get("/items")
        def items(session: primary.sync_session):
            ...
    """

    def __init__(self, name: str, db_type: str) -> None:
        self._name = name
        self._db_type = db_type

    @functools.cached_property
    def async_session(self) -> Annotated[AsyncSession | AsyncClient, Depends]:
        from dbwarden.plugin import HookRegistry, HookNotRegisteredError

        if self._db_type in ("postgresql", "sqlite", "mysql", "mariadb"):
            from fastapi import Depends
            from sqlalchemy.ext.asyncio import AsyncSession

            if HookRegistry.is_registered("session_factory"):
                maker = HookRegistry.execute_single("session_factory", self._name)
                return Annotated[
                    AsyncSession, Depends(maker)
                ]
            raise RuntimeError(
                f"FastAPI session factory not available. "
                f"Install dbwarden-fastapi: `dbwarden plugin add dbwarden-fastapi`"
            )

        if self._db_type == "clickhouse":
            from fastapi import Depends
            from clickhouse_connect.driver.asyncclient import AsyncClient

            if HookRegistry.is_registered("clickhouse_session_factory"):
                maker = HookRegistry.execute_single("clickhouse_session_factory", self._name)
                return Annotated[
                    AsyncClient, Depends(maker)
                ]
            raise RuntimeError(
                f"FastAPI ClickHouse session factory not available. "
                f"Install dbwarden-fastapi: `dbwarden plugin add dbwarden-fastapi`"
            )

        raise ValueError(
            f"Unsupported database_type: {self._db_type!r}. "
            f"Expected one of: sqlite, postgresql, mysql, mariadb, clickhouse."
        )

    @functools.cached_property
    def sync_session(self) -> Annotated[Session | SyncClickHouseClient, Depends]:
        from dbwarden.plugin import HookRegistry, HookNotRegisteredError

        if self._db_type in ("postgresql", "sqlite", "mysql", "mariadb"):
            from fastapi import Depends
            from sqlalchemy.orm import Session

            if HookRegistry.is_registered("sync_session_factory"):
                maker = HookRegistry.execute_single("sync_session_factory", self._name)
                return Annotated[
                    Session, Depends(maker)
                ]
            raise RuntimeError(
                f"FastAPI sync session factory not available. "
                f"Install dbwarden-fastapi: `dbwarden plugin add dbwarden-fastapi`"
            )

        if self._db_type == "clickhouse":
            from fastapi import Depends
            from clickhouse_connect.driver.client import Client as SyncClickHouseClient

            if HookRegistry.is_registered("clickhouse_sync_session_factory"):
                maker = HookRegistry.execute_single("clickhouse_sync_session_factory", self._name)
                return Annotated[
                    SyncClickHouseClient, Depends(maker)
                ]
            raise RuntimeError(
                f"FastAPI ClickHouse sync session factory not available. "
                f"Install dbwarden-fastapi: `dbwarden plugin add dbwarden-fastapi`"
            )

        raise ValueError(
            f"Unsupported database_type: {self._db_type!r}. "
            f"Expected one of: sqlite, postgresql, mysql, mariadb, clickhouse."
        )

    @property
    def session(self) -> Annotated[AsyncSession | AsyncClient, Depends]:
        import warnings

        warnings.warn(
            "DatabaseHandle.session is deprecated; use .async_session or .sync_session",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.async_session
