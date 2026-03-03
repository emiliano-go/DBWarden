import pytest
import tempfile
import os
from pathlib import Path

from dbwarden.config import get_config, get_toml_path
from dbwarden.logging import get_logger, DBWardenLogger


class TestConfig:
    """Tests for configuration loading."""

    def test_get_config_from_toml_file(self):
        """Test loading configuration from warden.toml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

                config = get_config()

                assert config.sqlalchemy_url == "sqlite:///./test.db"
            finally:
                os.chdir(old_cwd)

    def test_get_config_with_model_paths(self):
        """Test model paths are parsed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                    f.write('model_paths = ["./models/user.py", "./models/post.py"]\n')

                config = get_config()

                assert config.model_paths is not None
                assert len(config.model_paths) == 2
                assert "./models/user.py" in config.model_paths
                assert "./models/post.py" in config.model_paths
            finally:
                os.chdir(old_cwd)

    def test_get_config_model_paths_string(self):
        """Test model paths as comma-separated string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                    f.write('model_paths = "./models"\n')

                config = get_config()

                assert config.model_paths is not None
                assert len(config.model_paths) == 1
                assert "./models" in config.model_paths
            finally:
                os.chdir(old_cwd)

    def test_get_config_postgres_schema(self):
        """Test postgres schema configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                    f.write('postgres_schema = "custom_schema"\n')

                config = get_config()

                assert config.postgres_schema == "custom_schema"
            finally:
                os.chdir(old_cwd)

    def test_missing_sqlalchemy_url_raises_error(self):
        """Test that missing SQLAlchemy URL raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write("# Empty config\n")

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(ConfigurationError):
                    get_config()
            finally:
                os.chdir(old_cwd)

    def test_get_config_parent_directory(self):
        """Test config is found in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()

            # Create parent with warden.toml
            parent_dir = os.path.join(tmpdir, "parent")
            os.makedirs(parent_dir)
            with open(os.path.join(parent_dir, "warden.toml"), "w") as f:
                f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

            # Create child directory and run from there
            child_dir = os.path.join(parent_dir, "child")
            os.makedirs(child_dir)
            os.chdir(child_dir)

            try:
                config = get_config()
                assert config.sqlalchemy_url == "sqlite:///./test.db"
            finally:
                os.chdir(old_cwd)

    def test_get_toml_path_finds_file(self):
        """Test get_toml_path finds warden.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

                path = get_toml_path()
                assert path is not None
                assert path.name == "warden.toml"
            finally:
                os.chdir(old_cwd)

    def test_get_toml_path_returns_none_when_not_found(self):
        """Test get_toml_path returns None when file not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                path = get_toml_path()
                assert path is None
            finally:
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

    def test_logger_log_connection_init(self):
        """Test logging connection initialization."""
        logger = DBWardenLogger(verbose=False)
        logger.log_connection_init("postgresql")

    def test_logger_log_pending_migrations(self):
        """Test logging pending migrations."""
        logger = DBWardenLogger(verbose=False)
        logger.log_pending_migrations(["V1__init.sql", "V2__add_users.sql"])

    def test_logger_log_migration_start(self):
        """Test logging migration start."""
        logger = DBWardenLogger(verbose=False)
        logger.log_migration_start("0001", "V1__init.sql")

    def test_logger_log_migration_end(self):
        """Test logging migration end."""
        logger = DBWardenLogger(verbose=False)
        logger.log_migration_end("0001", "V1__init.sql", 0.05)

    def test_logger_log_rollback_end(self):
        """Test logging rollback end."""
        logger = DBWardenLogger(verbose=False)
        logger.log_rollback_end("0001", "V1__init.sql", 0.03)

    def test_logger_log_backup_created(self):
        """Test logging backup creation."""
        logger = DBWardenLogger(verbose=False)
        logger.log_backup_created("/path/to/backup.db")

    def test_logger_log_baseline_set(self):
        """Test logging baseline set."""
        logger = DBWardenLogger(verbose=False)
        logger.log_baseline_set("0001")

    def test_get_logger_returns_same_instance(self):
        """Test get_logger returns same instance."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_reset_logger(self):
        """Test reset_logger creates new instance."""
        from dbwarden.logging import reset_logger

        logger1 = get_logger()
        reset_logger()
        logger2 = get_logger()
        assert logger1 is not logger2
