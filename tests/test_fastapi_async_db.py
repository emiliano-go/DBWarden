"""Tests for async database engine dependencies and DatabaseHandle."""

from typing import Annotated, get_origin

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import Depends
from fastapi.params import Depends as DependsCls
from sqlalchemy.ext.asyncio import AsyncSession


def _is_depends_instance(obj) -> bool:
    """Check if *obj* is a FastAPI Depends() instance."""
    return type(obj).__name__ == "Depends" or hasattr(obj, "dependency")


class TestDatabaseHandle:
    """Tests for the DatabaseHandle returned by database_config()."""

    def test_async_session_property_returns_annotated_sql(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("primary", "postgresql")
        ann = handle.async_session

        assert get_origin(ann) is Annotated
        assert AsyncSession in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)

    def test_async_session_property_returns_annotated_sqlite(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("analytics", "sqlite")
        ann = handle.async_session

        assert get_origin(ann) is Annotated
        assert AsyncSession in ann.__args__

    def test_async_session_property_returns_annotated_clickhouse(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("analytics", "clickhouse")
        ann = handle.async_session

        from clickhouse_connect.driver.asyncclient import AsyncClient

        assert get_origin(ann) is Annotated
        assert AsyncClient in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)

    def test_async_session_property_raises_for_unknown_type(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("bad", "mongodb")
        with pytest.raises(ValueError, match="Unsupported database_type"):
            _ = handle.async_session

    def test_async_session_property_cached(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("primary", "postgresql")
        assert handle.async_session is handle.async_session

    def test_sync_session_property_returns_annotated(self):
        from dbwarden.db_handle import DatabaseHandle
        from sqlalchemy.orm import Session

        handle = DatabaseHandle("primary", "postgresql")
        ann = handle.sync_session

        assert get_origin(ann) is Annotated
        assert Session in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)

    def test_sync_session_property_raises_for_unknown_type(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("bad", "mongodb")
        with pytest.raises(ValueError, match="Unsupported database_type"):
            _ = handle.sync_session

    def test_sync_session_property_cached(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("primary", "postgresql")
        assert handle.sync_session is handle.sync_session

    def test_database_config_returns_handle(self):
        import dbwarden.config_registry as cr

        handle = cr.database_config(
            database_name="test_handle",
            database_type="sqlite",
            database_url_sync="sqlite:///./test.db",
        )
        from dbwarden.db_handle import DatabaseHandle

        assert isinstance(handle, DatabaseHandle)
        assert hasattr(handle, "async_session")
        assert hasattr(handle, "sync_session")


class TestMakeSessionDep:
    """Tests for _make_session_dep factory."""

    def test_returns_callable(self):
        from dbwarden.fastapi.engines import _make_session_dep

        dep = _make_session_dep("primary")
        assert callable(dep)

    def test_dependency_is_async_generator_function(self, monkeypatch):
        mock_db = type("MockDB", (), {
            "database_type": "sqlite",
            "sqlalchemy_url_sync": "sqlite:///:memory:",
            "sqlalchemy_url_async": None,
            "sqlalchemy_url": "sqlite:///:memory:",
        })()

        def mock_get_database(name=None):
            return mock_db

        monkeypatch.setattr("dbwarden.fastapi.engines.get_database", mock_get_database)
        monkeypatch.setattr("dbwarden.fastapi.engines.runtime_flags", lambda dev, strict_translation: type("ctx", (), {
            "__enter__": lambda s: None,
            "__exit__": lambda s, *a: None,
        })())

        from dbwarden.fastapi.engines import _make_session_dep

        dep = _make_session_dep("primary")
        import inspect

        assert inspect.isasyncgenfunction(dep)

    def test_session_dep_works_with_annotation(self):
        from dbwarden.fastapi.engines import _make_session_dep

        dep = _make_session_dep("primary")

        ann = Annotated[AsyncSession, Depends(dep)]

        assert get_origin(ann) is Annotated
        assert AsyncSession in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)


class TestMakeClickHouseDep:
    """Tests for _make_clickhouse_dep factory."""

    def test_returns_callable(self):
        from dbwarden.fastapi.engines import _make_clickhouse_dep

        dep = _make_clickhouse_dep("analytics")
        assert callable(dep)

    def test_dependency_is_async_generator_function(self):
        from dbwarden.fastapi.engines import _make_clickhouse_dep

        dep = _make_clickhouse_dep("analytics")
        import inspect

        assert inspect.isasyncgenfunction(dep)

    def test_clickhouse_dep_works_with_annotation(self):
        from dbwarden.fastapi.engines import _make_clickhouse_dep

        dep = _make_clickhouse_dep("analytics")
        from clickhouse_connect.driver.asyncclient import AsyncClient

        ann = Annotated[AsyncClient, Depends(dep)]

        assert get_origin(ann) is Annotated
        assert AsyncClient in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)


class TestDisposeEngines:
    """Tests for dispose_engines cleanup."""

    def test_dispose_engines_clears_caches(self):
        from dbwarden.fastapi import engines

        engines._ASYNC_SESSION_FACTORIES["test"] = "fake"
        engines._CLICKHOUSE_ASYNC_CLIENTS["test"] = "fake"

        engines.dispose_engines()

        assert "test" not in engines._ASYNC_SESSION_FACTORIES
        assert "test" not in engines._CLICKHOUSE_ASYNC_CLIENTS
