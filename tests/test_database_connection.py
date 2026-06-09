from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetDbConnection:
    @patch("dbwarden.database.connection.get_database")
    @patch("dbwarden.database.connection._get_engine")
    @patch("dbwarden.database.connection.get_logger")
    def test_get_db_connection_success(self, mock_get_logger, mock_get_engine, mock_get_db):
        mock_config = MagicMock()
        mock_config.sqlalchemy_url = "sqlite:///test.db"
        mock_config.database_type = "sqlite"
        mock_config.postgres_schema = None
        mock_get_db.return_value = mock_config

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_connection
        mock_get_engine.return_value = mock_engine

        from dbwarden.database.connection import get_db_connection

        with get_db_connection("test") as conn:
            assert conn is mock_connection

        mock_engine.begin.assert_called_once()

    @patch("dbwarden.database.connection.get_database")
    @patch("dbwarden.database.connection._get_engine")
    def test_get_db_connection_rolls_back_on_exception(self, mock_get_engine, mock_get_db):
        mock_config = MagicMock()
        mock_config.sqlalchemy_url = "sqlite:///test.db"
        mock_config.database_type = "sqlite"
        mock_config.postgres_schema = None
        mock_get_db.return_value = mock_config

        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = MagicMock()
        mock_get_engine.return_value = mock_engine

        from dbwarden.database.connection import get_db_connection

        with pytest.raises(ValueError, match="test error"):
            with get_db_connection("test") as conn:
                raise ValueError("test error")

    @patch("dbwarden.database.connection.get_database")
    @patch("dbwarden.database.connection._get_engine")
    def test_get_db_connection_passes_sandbox_url(self, mock_get_engine, mock_get_db):
        mock_config = MagicMock()
        mock_config.sqlalchemy_url = "sqlite:///original.db"
        mock_config.database_type = "sqlite"
        mock_config.postgres_schema = None
        mock_get_db.return_value = mock_config

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_connection
        mock_get_engine.return_value = mock_engine

        from dbwarden.database.connection import get_db_connection, set_sandbox_override, clear_sandbox_override

        set_sandbox_override("sqlite:///sandbox.db", "sqlite")
        try:
            with get_db_connection("test") as conn:
                assert conn is mock_connection
        finally:
            clear_sandbox_override()


class TestGetEngine:
    @patch("dbwarden.database.connection.get_database")
    @patch("dbwarden.database.connection._get_engine")
    def test_get_engine(self, mock_get_engine, mock_get_db):
        mock_config = MagicMock()
        mock_config.sqlalchemy_url = "sqlite:///test.db"
        mock_config.database_type = "sqlite"
        mock_get_db.return_value = mock_config

        from dbwarden.database.connection import get_engine

        result = get_engine("test")
        mock_get_engine.assert_called_once_with("sqlite:///test.db", "sqlite")
        assert result == mock_get_engine.return_value


class TestSandboxOverride:
    def test_sandbox_override_context_manager(self):
        import dbwarden.database.connection as conn_mod

        with conn_mod.sandbox_override("sqlite:///sandbox.db", "sqlite"):
            assert conn_mod._SANDBOX_URL == "sqlite:///sandbox.db"
            assert conn_mod._SANDBOX_DB_TYPE == "sqlite"

        assert conn_mod._SANDBOX_URL is None
        assert conn_mod._SANDBOX_DB_TYPE is None


class TestConvertUrl:
    def test_convert_clickhouse_http_url(self):
        from dbwarden.database.connection import _convert_url_to_clickhouse_dialect

        result = _convert_url_to_clickhouse_dialect("https://user:pass@host:8443/db")
        assert result.startswith("clickhousedb://user:pass@host:8443/db")

    def test_convert_clickhouse_no_password(self):
        from dbwarden.database.connection import _convert_url_to_clickhouse_dialect

        result = _convert_url_to_clickhouse_dialect("http://user@host:8123/db")
        assert "password" not in result
        assert "clickhousedb://user@" in result

    def test_convert_clickhouse_plain_url(self):
        from dbwarden.database.connection import _convert_url_to_clickhouse_dialect

        result = _convert_url_to_clickhouse_dialect("clickhousedb://user:pass@host:8443/db")
        assert result.startswith("clickhousedb://")


class TestResetConnectionLogging:
    def test_reset_connection_logging(self):
        import dbwarden.database.connection as conn_mod

        conn_mod._connection_init_logged = True
        conn_mod.reset_connection_logging()
        assert conn_mod._connection_init_logged is False
