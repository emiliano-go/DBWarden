import os
import tempfile
from pathlib import Path

import pytest

from dbwarden.config import (
    DatabaseConfig,
    MultiDbConfig,
    get_config,
    get_database,
    get_multi_db_config,
    get_toml_path,
    list_databases,
    set_dev_mode,
)
from dbwarden.exceptions import ConfigurationError
from dbwarden.logging import DBWardenLogger, get_logger


def _write_settings(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def reset_dev_mode():
    set_dev_mode(False)
    yield
    set_dev_mode(False)


class TestConfig:
    def test_get_config_from_python_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./test.db')",
                    ],
                )
                config = get_config()
                assert config.sqlalchemy_url == "sqlite:///./test.db"
                assert config.database_type == "sqlite"
                assert config.migrations_dir == "migrations/primary"
                assert config.migration_table == "_dbwarden_migrations"
            finally:
                os.chdir(old)

    def test_get_config_uses_custom_migration_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./test.db', migration_table='custom_migrations')",
                    ],
                )
                config = get_config()
                assert config.migration_table == "custom_migrations"
            finally:
                os.chdir(old)

    def test_get_config_uses_custom_seed_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./test.db', seed_table='custom_seeds')",
                    ],
                )
                config = get_config()
                assert config.seed_table == "custom_seeds"
            finally:
                os.chdir(old)

    def test_get_config_default_seed_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./test.db')",
                    ],
                )
                config = get_config()
                assert config.seed_table == "_dbwarden_seeds"
            finally:
                os.chdir(old)

    def test_get_config_with_model_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./test.db', model_paths=['./models/user.py'])",
                    ],
                )
                config = get_config()
                assert config.model_paths == ["./models/user.py"]
            finally:
                os.chdir(old)

    def test_missing_urls_raises_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite')",
                    ],
                )
                with pytest.raises(ConfigurationError, match="database_url_sync or database_url_async"):
                    get_config()
            finally:
                os.chdir(old)

    def test_get_toml_path_returns_none_when_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                assert get_toml_path() is None
            finally:
                os.chdir(old)

    def test_default_database_not_found_raises_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=False, database_type='sqlite', database_url_sync='sqlite:///./test.db')",
                    ],
                )
                with pytest.raises(ConfigurationError, match="Exactly one default"):
                    get_multi_db_config()
            finally:
                os.chdir(old)

    def test_get_database_by_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./primary.db', model_paths=['models/primary'])",
                        "database_config(database_name='analytics', database_type='sqlite', database_url_sync='sqlite:///./analytics.db', model_paths=['models/analytics'])",
                    ],
                )
                db = get_database("analytics")
                assert db.sqlalchemy_url == "sqlite:///./analytics.db"
            finally:
                os.chdir(old)

    def test_get_database_nonexistent_raises_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./test.db')",
                    ],
                )
                with pytest.raises(ConfigurationError, match="not found in settings config"):
                    get_database("nonexistent")
            finally:
                os.chdir(old)

    def test_list_databases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./primary.db', model_paths=['models/primary'])",
                        "database_config(database_name='analytics', database_type='sqlite', database_url_sync='sqlite:///./analytics.db', model_paths=['models/analytics'])",
                        "database_config(database_name='legacy', database_type='sqlite', database_url_sync='sqlite:///./legacy.db', model_paths=['models/legacy'])",
                    ],
                )
                dbs = list_databases()
                assert set(dbs) == {"primary", "analytics", "legacy"}
            finally:
                os.chdir(old)

    def test_get_multi_db_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./primary.db', model_paths=['models/primary'])",
                        "database_config(database_name='analytics', database_type='sqlite', database_url_sync='sqlite:///./analytics.db', model_paths=['models/analytics'])",
                    ],
                )
                config = get_multi_db_config()
                assert isinstance(config, MultiDbConfig)
                assert config.default == "primary"
                assert len(config.databases) == 2
            finally:
                os.chdir(old)

    def test_get_database_uses_dev_database_in_dev_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='postgresql', database_url_sync='postgresql://user:password@localhost:5432/main', dev_database_url='sqlite:///./development.db')",
                    ],
                )
                set_dev_mode(True)
                config = get_database("primary")
                assert config.sqlalchemy_url == "sqlite:///./development.db"
                assert config.database_type == "sqlite"
            finally:
                os.chdir(old)

    def test_get_database_dev_mode_requires_dev_database_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./primary.db')",
                    ],
                )
                set_dev_mode(True)
                with pytest.raises(ConfigurationError, match="has no dev_database_url configured"):
                    get_database("primary")
            finally:
                os.chdir(old)

    def test_dev_database_type_requires_dev_database_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./primary.db', dev_database_type='sqlite')",
                    ],
                )
                with pytest.raises(ConfigurationError, match="dev_database_url is required"):
                    get_multi_db_config()
            finally:
                os.chdir(old)

    def test_duplicate_database_urls_raise_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                _write_settings(
                    Path("dbwarden.py"),
                    [
                        "from dbwarden import database_config",
                        "",
                        "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./same.db', model_paths=['models/primary'])",
                        "database_config(database_name='analytics', database_type='sqlite', database_url_sync='sqlite:///./same.db', model_paths=['models/analytics'])",
                    ],
                )
                with pytest.raises(ConfigurationError, match="Duplicate database_url_sync"):
                    get_multi_db_config()
            finally:
                os.chdir(old)


class TestLogger:
    def test_logger_default_level(self):
        logger = DBWardenLogger(verbose=False)
        assert logger.verbose is False
        assert logger.logger.level == 20

    def test_logger_verbose_level(self):
        logger = DBWardenLogger(verbose=True)
        assert logger.verbose is True
        assert logger.logger.level == 10

    def test_logger_set_verbose(self):
        logger = DBWardenLogger(verbose=False)
        logger.set_verbose(True)
        assert logger.verbose is True
        assert logger.logger.level == 10

    def test_logger_info(self):
        logger = DBWardenLogger(verbose=False)
        logger.info("Test message")

    def test_logger_debug(self):
        logger = DBWardenLogger(verbose=True)
        logger.debug("Debug message")
        logger.log_sql_statement("SELECT * FROM users")

    def test_logger_log_connection_init(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_connection_init("postgresql")

    def test_logger_log_pending_migrations(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_pending_migrations(["V1__init.sql", "V2__add_users.sql"])

    def test_logger_log_migration_start(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_migration_start("0001", "V1__init.sql")

    def test_logger_log_migration_end(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_migration_end("0001", "V1__init.sql", 0.05)

    def test_logger_log_rollback_end(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_rollback_end("0001", "V1__init.sql", 0.03)

    def test_logger_log_backup_created(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_backup_created("/path/to/backup.db")

    def test_logger_log_baseline_set(self):
        logger = DBWardenLogger(verbose=False)
        logger.log_baseline_set("0001")

    def test_get_logger_returns_same_instance(self):
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_reset_logger(self):
        from dbwarden.logging import reset_logger

        logger1 = get_logger()
        reset_logger()
        logger2 = get_logger()
        assert logger1 is not logger2
