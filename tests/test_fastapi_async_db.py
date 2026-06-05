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

    def test_session_property_returns_annotated_sql(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("primary", "postgresql")
        ann = handle.session

        assert get_origin(ann) is Annotated
        assert AsyncSession in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)

    def test_session_property_returns_annotated_sqlite(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("analytics", "sqlite")
        ann = handle.session

        assert get_origin(ann) is Annotated
        assert AsyncSession in ann.__args__

    def test_session_property_returns_annotated_clickhouse(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("analytics", "clickhouse")
        ann = handle.session

        from clickhouse_connect.driver.asyncclient import AsyncClient

        assert get_origin(ann) is Annotated
        assert AsyncClient in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)

    def test_session_property_raises_for_unknown_type(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("bad", "mongodb")
        with pytest.raises(ValueError, match="Unsupported database_type"):
            _ = handle.session

    def test_session_property_cached(self):
        from dbwarden.db_handle import DatabaseHandle

        handle = DatabaseHandle("primary", "postgresql")
        assert handle.session is handle.session

    def test_database_config_returns_handle(self):
        import dbwarden.config_registry as cr

        handle = cr.database_config(
            database_name="test_handle",
            database_type="sqlite",
            database_url="sqlite:///./test.db",
        )
        from dbwarden.db_handle import DatabaseHandle

        assert isinstance(handle, DatabaseHandle)
        assert hasattr(handle, "session")


class TestMakeSessionDep:
    """Tests for _make_session_dep factory."""

    def test_returns_callable(self):
        from dbwarden.fastapi.async_db import _make_session_dep

        dep = _make_session_dep("primary")
        assert callable(dep)

    def test_dependency_is_async_generator_function(self, monkeypatch):
        mock_db = type("MockDB", (), {
            "database_type": "sqlite",
            "sqlalchemy_url": "sqlite:///:memory:",
        })()

        def mock_get_database(name=None):
            return mock_db

        monkeypatch.setattr("dbwarden.fastapi.async_db.get_database", mock_get_database)
        monkeypatch.setattr("dbwarden.fastapi.async_db.runtime_flags", lambda dev, strict_translation: type("ctx", (), {
            "__enter__": lambda s: None,
            "__exit__": lambda s, *a: None,
        })())

        from dbwarden.fastapi.async_db import _make_session_dep

        dep = _make_session_dep("primary")
        import inspect

        assert inspect.isasyncgenfunction(dep)

    def test_session_dep_works_with_annotation(self):
        from dbwarden.fastapi.async_db import _make_session_dep

        dep = _make_session_dep("primary")

        ann = Annotated[AsyncSession, Depends(dep)]

        assert get_origin(ann) is Annotated
        assert AsyncSession in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)


class TestMakeClickHouseDep:
    """Tests for _make_clickhouse_dep factory."""

    def test_returns_callable(self):
        from dbwarden.fastapi.async_db import _make_clickhouse_dep

        dep = _make_clickhouse_dep("analytics")
        assert callable(dep)

    def test_dependency_is_async_generator_function(self):
        from dbwarden.fastapi.async_db import _make_clickhouse_dep

        dep = _make_clickhouse_dep("analytics")
        import inspect

        assert inspect.isasyncgenfunction(dep)

    def test_clickhouse_dep_works_with_annotation(self):
        from dbwarden.fastapi.async_db import _make_clickhouse_dep

        dep = _make_clickhouse_dep("analytics")
        from clickhouse_connect.driver.asyncclient import AsyncClient

        ann = Annotated[AsyncClient, Depends(dep)]

        assert get_origin(ann) is Annotated
        assert AsyncClient in ann.__args__
        assert any(_is_depends_instance(a) for a in ann.__metadata__)


class TestDisposeEngines:
    """Tests for dispose_engines cleanup."""

    def test_dispose_engines_clears_caches(self):
        from dbwarden.fastapi import async_db

        async_db._SESSION_FACTORIES["test"] = "fake"
        async_db._CLICKHOUSE_CLIENTS["test"] = "fake"

        async_db.dispose_engines()

        assert "test" not in async_db._SESSION_FACTORIES
        assert "test" not in async_db._CLICKHOUSE_CLIENTS
