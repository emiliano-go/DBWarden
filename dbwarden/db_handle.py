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
        """FastAPI dependency annotation for async database access.

        Resolves to ``Annotated[AsyncSession, Depends(...)]`` for SQL databases
        or ``Annotated[AsyncClient, Depends(...)]`` for ClickHouse.
        """
        if self._db_type in ("postgresql", "sqlite", "mysql", "mariadb"):
            from fastapi import Depends
            from sqlalchemy.ext.asyncio import AsyncSession

            from dbwarden.fastapi.engines import _make_session_dep

            return Annotated[
                AsyncSession, Depends(_make_session_dep(self._name))
            ]

        if self._db_type == "clickhouse":
            from fastapi import Depends
            from clickhouse_connect.driver.asyncclient import AsyncClient

            from dbwarden.fastapi.engines import _make_clickhouse_dep

            return Annotated[
                AsyncClient, Depends(_make_clickhouse_dep(self._name))
            ]

        raise ValueError(
            f"Unsupported database_type: {self._db_type!r}. "
            f"Expected one of: sqlite, postgresql, mysql, mariadb, clickhouse."
        )

    @functools.cached_property
    def sync_session(self) -> Annotated[Session | SyncClickHouseClient, Depends]:
        """FastAPI dependency annotation for synchronous database access.

        Resolves to ``Annotated[Session, Depends(...)]`` for SQL databases
        or ``Annotated[Client, Depends(...)]`` for ClickHouse.
        """

        if self._db_type in ("postgresql", "sqlite", "mysql", "mariadb"):
            from fastapi import Depends
            from sqlalchemy.orm import Session

            from dbwarden.fastapi.engines import _make_sync_session_dep

            return Annotated[
                Session, Depends(_make_sync_session_dep(self._name))
            ]

        if self._db_type == "clickhouse":
            from fastapi import Depends
            from clickhouse_connect.driver.client import Client as SyncClickHouseClient

            from dbwarden.fastapi.engines import _make_sync_clickhouse_dep

            return Annotated[
                SyncClickHouseClient, Depends(_make_sync_clickhouse_dep(self._name))
            ]

        raise ValueError(
            f"Unsupported database_type: {self._db_type!r}. "
            f"Expected one of: sqlite, postgresql, mysql, mariadb, clickhouse."
        )

    @property
    def session(self) -> Annotated[AsyncSession | AsyncClient, Depends]:
        """Deprecated: use ``async_session`` or ``sync_session``."""
        import warnings

        warnings.warn(
            "DatabaseHandle.session is deprecated; use .async_session or .sync_session",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.async_session
