import os
import tempfile
from pathlib import Path

from dbwarden.commands.settings import (
    handle_settings_database_add,
    handle_settings_database_clear_dev,
    handle_settings_database_remove,
    handle_settings_database_rename,
    handle_settings_database_set_dev,
    handle_settings_default_set,
)
from dbwarden.config import get_multi_db_config


def _write_settings(path: Path) -> None:
    path.write_text(
        "from dbwarden import database_config\n\n"
        "database_config(\n"
        "    database_name='primary',\n"
        "    default=True,\n"
        "    database_type='sqlite',\n"
        "    database_url_sync='sqlite:///./app.db',\n"
        "    model_paths=['models/primary'],\n"
        ")\n",
        encoding="utf-8",
    )


class TestSettingsCommands:
    def test_add_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(Path("dbwarden.py"))
                handle_settings_database_add(
                    name="analytics",
                    database_type="sqlite",
                    url="sqlite:///./analytics.db",
                    model_paths=["models/analytics"],
                )
                cfg = get_multi_db_config()
                assert "analytics" in cfg.databases
            finally:
                os.chdir(old)

    def test_rename_and_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(Path("dbwarden.py"))
                handle_settings_database_rename("primary", "main")
                handle_settings_default_set("main")
                cfg = get_multi_db_config()
                assert cfg.default == "main"
                assert "main" in cfg.databases
            finally:
                os.chdir(old)

    def test_set_and_clear_dev(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(Path("dbwarden.py"))
                handle_settings_database_set_dev(
                    "primary",
                    "sqlite",
                    "sqlite:///./dev.db",
                )
                cfg = get_multi_db_config()
                assert cfg.databases["primary"].dev_database_url == "sqlite:///./dev.db"

                handle_settings_database_clear_dev("primary")
                cfg = get_multi_db_config()
                assert cfg.databases["primary"].dev_database_url is None
            finally:
                os.chdir(old)

    def test_remove_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(Path("dbwarden.py"))
                handle_settings_database_add(
                    name="analytics",
                    database_type="sqlite",
                    url="sqlite:///./analytics.db",
                    model_paths=["models/analytics"],
                )
                handle_settings_database_remove("analytics")
                cfg = get_multi_db_config()
                assert "analytics" not in cfg.databases
            finally:
                os.chdir(old)
