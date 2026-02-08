import pytest
import tempfile
import os
from pathlib import Path

from dbwarden.config import get_config, get_env_path, validate_env_file
from dbwarden.database.connection import is_async_enabled, get_mode
from dbwarden.logging import get_logger, DBWardenLogger


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test."""
    env_vars = [
        "STRATA_SQLALCHEMY_URL",
        "STRATA_ASYNC",
        "STRATA_MODEL_PATHS",
        "STRATA_POSTGRES_SCHEMA",
    ]
    old_vals = {}
    for var in env_vars:
        old_vals[var] = os.environ.pop(var, None)
    yield
    for var in env_vars:
        os.environ.pop(var, None)
        if old_vals[var] is not None:
            os.environ[var] = old_vals[var]


class TestConfig:
    """Tests for configuration loading."""

    def test_get_config_from_env_file(self):
        """Test loading configuration from .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite:///./test.db\n")
                    f.write("STRATA_ASYNC=false\n")

                config = get_config()

                assert config.sqlalchemy_url == "sqlite:///./test.db"
                assert config.async_mode == False
            finally:
                os.chdir(old_cwd)

    def test_get_config_with_async_true(self):
        """Test async mode is detected correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write(
                        "STRATA_SQLALCHEMY_URL=postgresql+asyncpg://user:pass@localhost/db\n"
                    )
                    f.write("STRATA_ASYNC=true\n")

                config = get_config()

                assert config.async_mode == True
            finally:
                os.chdir(old_cwd)

    def test_get_config_with_model_paths(self):
        """Test model paths are parsed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite:///./test.db\n")
                    f.write("STRATA_MODEL_PATHS=./models/user.py,./models/post.py\n")

                config = get_config()

                assert config.model_paths is not None
                assert len(config.model_paths) == 2
                assert "./models/user.py" in config.model_paths
                assert "./models/post.py" in config.model_paths
            finally:
                os.chdir(old_cwd)

    def test_missing_sqlalchemy_url_raises_error(self):
        """Test that missing SQLAlchemy URL raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_ASYNC=false\n")

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(ConfigurationError):
                    get_config()
            finally:
                os.chdir(old_cwd)


class TestAsyncSyncDetection:
    """Tests for async/sync mode detection."""

    def test_is_async_enabled_default(self):
        """Test async detection when env is not set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite:///./test.db\n")

                result = is_async_enabled()
                assert result == False
            finally:
                os.chdir(old_cwd)

    def test_is_async_enabled_true(self):
        """Test async detection with STRATA_ASYNC=true."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ["STRATA_ASYNC"] = "true"
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite:///./test.db\n")

                result = is_async_enabled()
                assert result == True
            finally:
                os.environ.pop("STRATA_ASYNC", None)
                os.chdir(old_cwd)

    def test_is_async_enabled_false(self):
        """Test async detection with STRATA_ASYNC=false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ["STRATA_ASYNC"] = "false"
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite:///./test.db\n")

                result = is_async_enabled()
                assert result == False
            finally:
                os.environ.pop("STRATA_ASYNC", None)
                os.chdir(old_cwd)

    def test_get_mode_sync(self):
        """Test get_mode returns 'sync' for sync mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite:///./test.db\n")

                mode = get_mode()
                assert mode == "sync"
            finally:
                os.chdir(old_cwd)

    def test_get_mode_async(self):
        """Test get_mode returns 'async' for async mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.environ["STRATA_ASYNC"] = "true"
            os.chdir(tmpdir)

            try:
                with open(".env", "w") as f:
                    f.write("STRATA_SQLALCHEMY_URL=sqlite+aiosqlite:///./test.db\n")

                mode = get_mode()
                assert mode == "async"
            finally:
                os.environ.pop("STRATA_ASYNC", None)
                os.chdir(old_cwd)


class TestLogger:
    """Tests for structured logging."""

    def test_logger_default_level(self):
        """Test logger defaults to INFO level."""
        logger = DBWardenLogger(verbose=False)
        assert logger.verbose == False
        assert logger.logger.level == 20  # INFO

    def test_logger_verbose_level(self):
        """Test verbose logger uses DEBUG level."""
        logger = DBWardenLogger(verbose=True)
        assert logger.verbose == True
        assert logger.logger.level == 10  # DEBUG

    def test_logger_set_verbose(self):
        """Test updating verbosity."""
        logger = DBWardenLogger(verbose=False)
        logger.set_verbose(True)
        assert logger.verbose == True
        assert logger.logger.level == 10

    def test_logger_info(self):
        """Test info logging."""
        logger = DBWardenLogger(verbose=False)
        logger.info("Test message")

    def test_logger_debug(self):
        """Test debug logging."""
        logger = DBWardenLogger(verbose=True)
        logger.debug("Debug message")
        logger.log_sql_statement("SELECT * FROM users")

    def test_logger_log_execution_mode(self):
        """Test logging execution mode."""
        logger = DBWardenLogger(verbose=False)
        logger.log_execution_mode("sync")
        logger.log_execution_mode("async")

    def test_logger_log_connection_init(self):
        """Test logging connection initialization."""
        logger = DBWardenLogger(verbose=False)
        logger.log_connection_init("postgresql")

    def test_logger_log_pending_migrations(self):
        """Test logging pending migrations."""
        logger = DBWardenLogger(verbose=False)
        logger.log_pending_migrations(["V1__init.sql", "V2__add_users.sql"])
