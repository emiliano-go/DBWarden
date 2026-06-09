from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestWriteToml:
    def test_write_toml_with_tomli_w(self):
        import builtins

        from dbwarden.commands.database import _write_toml

        mock_tomli_w = MagicMock()
        mock_tomli_w.dump.return_value = None
        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "tomli_w":
                return mock_tomli_w
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=_mock_import),
            patch("builtins.open") as mock_open,
        ):
            _write_toml(Path("/tmp/test.toml"), {"key": "value"})
            mock_tomli_w.dump.assert_called_once()
            mock_open.assert_called_once_with(Path("/tmp/test.toml"), "wb")

    def test_write_toml_json_fallback(self):
        import builtins

        from dbwarden.commands.database import _write_toml

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "tomli_w":
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=_mock_import),
            patch("builtins.open") as mock_open,
            patch("json.dump") as mock_json_dump,
        ):
            _write_toml(Path("/tmp/test.toml"), {"key": "value"})
            mock_json_dump.assert_called_once()
            mock_open.assert_called_once_with(Path("/tmp/test.toml"), "w")


class TestDatabaseList:
    @patch("dbwarden.commands.database.get_multi_db_config")
    @patch("dbwarden.commands.database.console.print")
    def test_handle_database_list(self, mock_print, mock_get_config):
        mock_config = MagicMock()
        mock_config.default = "default"

        db_default = MagicMock()
        db_default.sqlalchemy_url = "sqlite:///default.db"
        db_default.database_type = "sqlite"
        db_default.migrations_dir = "migrations/default"

        mock_config.databases = {"default": db_default}
        mock_get_config.return_value = mock_config

        from dbwarden.commands.database import handle_database_list

        handle_database_list()
        mock_print.assert_called()

    @patch("dbwarden.commands.database.get_multi_db_config")
    @patch("dbwarden.commands.database.console.print")
    def test_handle_database_list_masks_password(self, mock_print, mock_get_config):
        mock_config = MagicMock()
        mock_config.default = "prod"

        db_prod = MagicMock()
        db_prod.sqlalchemy_url = "postgresql://user:secret@localhost:5432/db"
        db_prod.database_type = "postgresql"
        db_prod.migrations_dir = "migrations/prod"

        mock_config.databases = {"prod": db_prod}
        mock_get_config.return_value = mock_config

        from dbwarden.commands.database import handle_database_list

        handle_database_list()
        calls = [str(c) for c in mock_print.call_args_list]
        assert any("***" in c for c in calls)
        assert all("secret" not in c for c in calls)


class TestDatabaseAdd:
    @patch("dbwarden.commands.database.Path.cwd")
    @patch("dbwarden.commands.database.tomllib.load")
    @patch("dbwarden.commands.database.get_multi_db_config")
    @patch("dbwarden.commands.database._write_toml")
    def test_handle_database_add_basic(
        self, mock_write, mock_get_config, mock_toml_load, mock_cwd
    ):
        mock_cwd.return_value = Path("/tmp")
        me = MagicMock()
        me.databases = {}
        mock_get_config.return_value = me
        mock_toml_load.return_value = {"warden": {"database": {}}}

        from dbwarden.commands.database import handle_database_add
        from dbwarden.database.connection import reset_connection_logging

        with patch("builtins.open"), patch.object(Path, "mkdir"):
            handle_database_add(
                name="testdb",
                url="sqlite:///test.db",
                database_type="sqlite",
            )
            mock_write.assert_called_once()

    @patch("dbwarden.commands.database.Path.cwd")
    def test_handle_database_add_no_toml(self, mock_cwd):
        mock_cwd.return_value = Path("/tmp")

        from dbwarden.commands.database import handle_database_add

        with (
            patch("dbwarden.commands.database.tomllib.load", side_effect=FileNotFoundError),
            pytest.raises(FileNotFoundError, match="warden.toml not found"),
        ):
            handle_database_add(name="x", url="sqlite:///x.db")

    @patch("dbwarden.commands.database.Path.cwd")
    @patch("dbwarden.commands.database.tomllib.load")
    @patch("dbwarden.commands.database.get_multi_db_config")
    def test_handle_database_add_duplicate_name(
        self, mock_get_config, mock_toml_load, mock_cwd
    ):
        mock_cwd.return_value = Path("/tmp")
        mock_toml_load.return_value = {"warden": {"database": {"existing": {}}}}
        me = MagicMock()
        me.databases = {}
        mock_get_config.return_value = me

        from dbwarden.commands.database import handle_database_add

        with (
            patch("builtins.open"),
            pytest.raises(ValueError, match="already exists"),
        ):
            handle_database_add(
                name="existing", url="sqlite:///e.db"
            )

    @patch("dbwarden.commands.database.Path.cwd")
    @patch("dbwarden.commands.database.tomllib.load")
    @patch("dbwarden.commands.database.get_multi_db_config")
    def test_handle_database_add_invalid_type(
        self, mock_get_config, mock_toml_load, mock_cwd
    ):
        mock_cwd.return_value = Path("/tmp")
        mock_toml_load.return_value = {"warden": {"database": {}}}
        me = MagicMock()
        me.databases = {}
        mock_get_config.return_value = me

        from dbwarden.commands.database import handle_database_add

        with (
            patch("builtins.open"),
            pytest.raises(ValueError, match="Invalid database_type"),
        ):
            handle_database_add(
                name="x", url="sqlite:///x.db", database_type="oracle"
            )


class TestDatabaseRemove:
    @patch("dbwarden.commands.database.Path.cwd")
    @patch("dbwarden.commands.database.Path.exists")
    @patch("dbwarden.commands.database.get_multi_db_config")
    @patch("dbwarden.commands.database.tomllib.load")
    @patch("dbwarden.commands.database._write_toml")
    def test_handle_database_remove(
        self, mock_write, mock_toml_load, mock_get_config, mock_exists, mock_cwd
    ):
        mock_cwd.return_value = Path("/tmp")
        mock_exists.return_value = True
        mock_toml_load.return_value = {"warden": {"database": {"db1": {}, "db2": {}}, "default": "db1"}}

        me = MagicMock()
        me.databases = {"db1": MagicMock(), "db2": MagicMock()}
        me.default = "db1"
        mock_get_config.return_value = me

        from dbwarden.commands.database import handle_database_remove

        with patch("builtins.open"):
            handle_database_remove("db2")
            mock_write.assert_called_once()

    @patch("dbwarden.commands.database.Path.cwd")
    def test_handle_database_remove_no_toml(self, mock_cwd):
        mock_cwd.return_value = Path("/tmp")

        from dbwarden.commands.database import handle_database_remove

        with pytest.raises(FileNotFoundError, match="warden.toml not found"):
            handle_database_remove("x")

    @patch("dbwarden.commands.database.Path.cwd")
    @patch("dbwarden.commands.database.Path.exists")
    @patch("dbwarden.commands.database.get_multi_db_config")
    def test_handle_database_remove_not_found(self, mock_get_config, mock_exists, mock_cwd):
        mock_cwd.return_value = Path("/tmp")
        mock_exists.return_value = True
        me = MagicMock()
        me.databases = {}
        mock_get_config.return_value = me

        from dbwarden.commands.database import handle_database_remove

        with patch("builtins.open"):
            with pytest.raises(ValueError, match="Database 'x' not found"):
                handle_database_remove("x")
