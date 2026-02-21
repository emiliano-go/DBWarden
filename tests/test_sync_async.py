import pytest
import tempfile
import os
import asyncio
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from dbwarden.config import get_config
from dbwarden.database.connection import (
    is_async_enabled,
    get_mode,
    get_db_connection,
)
from dbwarden.repositories import (
    create_migrations_table_if_not_exists,
    migrations_table_exists,
)


def clear_config_cache():
    """Clear the lru_cache for config to allow testing different configs."""
    from dbwarden.database import connection

    connection._get_engine.cache_clear()


class TestSyncAsyncConfig:
    """Tests for sync/async configuration switching."""

    @pytest.fixture
    def sync_env(self):
        """Set up environment for sync mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ.pop("DBWARDEN_ASYNC", None)
            os.chdir(tmpdir)

            with open("warden.toml", "w") as f:
                f.write('sqlalchemy_url = "sqlite:///./test_sync.db"\n')
                f.write("async = false\n")

            clear_config_cache()
            yield {"mode": "sync"}

            os.chdir(old_cwd)

    @pytest.fixture
    def async_env(self):
        """Set up environment for async mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ["DBWARDEN_ASYNC"] = "true"
            os.chdir(tmpdir)

            with open("warden.toml", "w") as f:
                f.write('sqlalchemy_url = "sqlite+aiosqlite:///./test_async.db"\n')
                f.write("async = true\n")

            clear_config_cache()
            yield {"mode": "async"}

            os.environ.pop("DBWARDEN_ASYNC", None)
            os.chdir(old_cwd)

    def test_sync_mode_detected_correctly(self, sync_env):
        """Test that sync mode is detected when async=false."""
        assert is_async_enabled() == False
        assert get_mode() == "sync"

    def test_async_mode_detected_correctly(self, async_env):
        """Test that async mode is detected when async=true."""
        assert is_async_enabled() == True
        assert get_mode() == "async"

    def test_config_reloads_on_env_change(self):
        """Test that config responds to environment changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                    f.write("async = false\n")

                clear_config_cache()
                assert is_async_enabled() == False

                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite+aiosqlite:///./test.db"\n')
                    f.write("async = true\n")

                clear_config_cache()
                assert is_async_enabled() == True

            finally:
                os.chdir(old_cwd)


class TestSyncConnection:
    """Tests for synchronous database connection."""

    @pytest.fixture
    def setup_sync_db(self):
        """Set up a synchronous database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            with open("warden.toml", "w") as f:
                f.write(f'sqlalchemy_url = "sqlite:///{db_path}"\n')
                f.write("async = false\n")

            clear_config_cache()
            yield {"db_path": db_path}

            os.chdir(old_cwd)
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_get_db_connection_sync(self, setup_sync_db):
        """Test getting a synchronous database connection."""
        create_migrations_table_if_not_exists()
        assert migrations_table_exists() == True

    def test_execute_sql_sync(self, setup_sync_db):
        """Test executing SQL in sync mode."""
        with get_db_connection() as conn:
            result = conn.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1

    def test_create_table_sync(self, setup_sync_db):
        """Test creating a table in sync mode."""
        with get_db_connection() as conn:
            conn.execute(
                text(
                    "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name VARCHAR(100))"
                )
            )
            conn.commit()

        import sqlite3

        conn = sqlite3.connect(setup_sync_db["db_path"])
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestAsyncConnection:
    """Tests for asynchronous database connection."""

    @pytest.fixture
    def setup_async_db(self):
        """Set up an asynchronous database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ["DBWARDEN_ASYNC"] = "true"
            os.chdir(tmpdir)

            with open("warden.toml", "w") as f:
                f.write(f'sqlalchemy_url = "sqlite+aiosqlite:///{db_path}"\n')
                f.write("async = true\n")

            clear_config_cache()
            yield {"db_path": db_path}

            os.environ.pop("DBWARDEN_ASYNC", None)
            os.chdir(old_cwd)
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_async_db_connection(self, setup_async_db):
        """Test getting an asynchronous database connection."""
        from dbwarden.database.connection import get_async_db_connection

        async with get_async_db_connection() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1

    @pytest.mark.asyncio
    async def test_create_table_async(self, setup_async_db):
        """Test creating a table in async mode."""
        from dbwarden.database.connection import get_async_db_connection

        async with get_async_db_connection() as conn:
            await conn.execute(
                text("CREATE TABLE async_table (id INTEGER PRIMARY KEY, data TEXT)")
            )
            await conn.commit()

        import sqlite3

        conn = sqlite3.connect(setup_async_db["db_path"])
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='async_table'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestConfigReload:
    """Tests for configuration reloading."""

    def test_url_parsing_sync(self):
        """Test URL parsing for sync mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write(
                        'sqlalchemy_url = "postgresql://user:pass@localhost/mydb"\n'
                    )
                    f.write("async = false\n")

                clear_config_cache()
                config = get_config()
                assert config.sqlalchemy_url == "postgresql://user:pass@localhost/mydb"
                assert config.async_mode == False

            finally:
                os.chdir(old_cwd)

    def test_url_parsing_async(self):
        """Test URL parsing for async mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ["DBWARDEN_ASYNC"] = "true"
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write(
                        'sqlalchemy_url = "postgresql+asyncpg://user:pass@localhost/mydb"\n'
                    )
                    f.write("async = true\n")

                clear_config_cache()
                config = get_config()
                assert config.async_mode == True

            finally:
                os.environ.pop("DBWARDEN_ASYNC", None)
                os.chdir(old_cwd)
