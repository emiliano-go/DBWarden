from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from clickhouse_connect.driver.asyncclient import AsyncClient
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseHandle:
    """Handle returned by ``database_config()``.

    The ``.session`` property returns a type annotation FastAPI can
    consume directly as a route parameter type hint — no ``Annotated``,
    ``Depends``, or typing imports needed in the route module::

        # dbwarden.py
        from dbwarden import database_config
        primary = database_config(database_name="primary", ...)

        # routes.py
        from ..dbwarden import primary

        @router.get("/users")
        async def users(session: primary.session):
            ...
    """

    def __init__(self, name: str, db_type: str) -> None:
        self._name = name
        self._db_type = db_type

    @functools.cached_property
    def session(self):
        """Return ``Annotated[T, Depends(...)]`` for the database type.

        * PostgreSQL / SQLite / MySQL / MariaDB  → ``AsyncSession``
        * ClickHouse                              → ``AsyncClient``
        """
        if self._db_type in ("postgresql", "sqlite", "mysql", "mariadb"):
            from fastapi import Depends
            from sqlalchemy.ext.asyncio import AsyncSession

            from dbwarden.fastapi.async_db import _make_session_dep

            return Annotated[
                AsyncSession, Depends(_make_session_dep(self._name))
            ]

        if self._db_type == "clickhouse":
            from fastapi import Depends
            from clickhouse_connect.driver.asyncclient import AsyncClient

            from dbwarden.fastapi.async_db import _make_clickhouse_dep

            return Annotated[
                AsyncClient, Depends(_make_clickhouse_dep(self._name))
            ]

        raise ValueError(
            f"Unsupported database_type: {self._db_type!r}. "
            f"Expected one of: sqlite, postgresql, mysql, mariadb, clickhouse."
        )
