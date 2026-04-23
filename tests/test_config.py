import pytest
import tempfile
import os
from pathlib import Path

from dbwarden.config import (
    get_config,
    get_toml_path,
    get_database,
    get_multi_db_config,
    list_databases,
    DatabaseConfig,
    MultiDbConfig,
    set_dev_mode,
)
from dbwarden.logging import get_logger, DBWardenLogger


@pytest.fixture(autouse=True)
def reset_dev_mode():
    set_dev_mode(False)
    yield
    set_dev_mode(False)


class TestConfig:
    """Tests for configuration loading."""

    def test_get_config_from_toml_file(self):
        """Test loading configuration from warden.toml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                    f.write('database_type = "sqlite"\n')

                config = get_config()

                assert config.sqlalchemy_url == "sqlite:///./test.db"
                assert config.database_type == "sqlite"
                assert config.migrations_dir == "migrations/primary"
            finally:
                os.chdir(old_cwd)

    def test_get_config_with_model_paths(self):
        """Test model paths are parsed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
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
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
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
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "postgresql://localhost/test"\n')
                    f.write('postgres_schema = "custom_schema"\n')

                config = get_config()

                assert config.postgres_schema == "custom_schema"
            finally:
                os.chdir(old_cwd)

    def test_get_config_custom_migrations_dir(self):
        """Test custom migrations directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')
                    f.write('migrations_dir = "db_migrations"\n')

                config = get_config()

                assert config.migrations_dir == "db_migrations"
            finally:
                os.chdir(old_cwd)

    def test_missing_database_section_raises_error(self):
        """Test that missing [database] section raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write("# Empty config\n")

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(
                    ConfigurationError, match="No \\[database\\] section found"
                ):
                    get_config()
            finally:
                os.chdir(old_cwd)

    def test_missing_sqlalchemy_url_raises_error(self):
        """Test that missing SQLAlchemy URL raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(
                    ConfigurationError, match="sqlalchemy_url is required"
                ):
                    get_config()
            finally:
                os.chdir(old_cwd)

    def test_get_config_parent_directory(self):
        """Test config is found in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()

            parent_dir = os.path.join(tmpdir, "parent")
            os.makedirs(parent_dir)
            with open(os.path.join(parent_dir, "warden.toml"), "w") as f:
                f.write('default = "primary"\n')
                f.write("[database.primary]\n")
                f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

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
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
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

    def test_default_database_not_found_raises_error(self):
        """Test that non-existent default database raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "nonexistent"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(
                    ConfigurationError, match="Default database 'nonexistent' not found"
                ):
                    get_multi_db_config()
            finally:
                os.chdir(old_cwd)

    def test_get_database_by_name(self):
        """Test getting a specific database by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./primary.db"\n')
                    f.write("[database.analytics]\n")
                    f.write('sqlalchemy_url = "sqlite:///./analytics.db"\n')

                db = get_database("analytics")
                assert db.sqlalchemy_url == "sqlite:///./analytics.db"
            finally:
                os.chdir(old_cwd)

    def test_get_database_nonexistent_raises_error(self):
        """Test that getting non-existent database raises ConfigurationError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./test.db"\n')

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(
                    ConfigurationError, match="not found in warden.toml"
                ):
                    get_database("nonexistent")
            finally:
                os.chdir(old_cwd)

    def test_list_databases(self):
        """Test listing all databases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./primary.db"\n')
                    f.write("[database.analytics]\n")
                    f.write('sqlalchemy_url = "sqlite:///./analytics.db"\n')
                    f.write("[database.legacy]\n")
                    f.write('sqlalchemy_url = "sqlite:///./legacy.db"\n')

                dbs = list_databases()
                assert len(dbs) == 3
                assert "primary" in dbs
                assert "analytics" in dbs
                assert "legacy" in dbs
            finally:
                os.chdir(old_cwd)

    def test_get_multi_db_config(self):
        """Test getting full multi-database config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./primary.db"\n')
                    f.write("[database.analytics]\n")
                    f.write('sqlalchemy_url = "sqlite:///./analytics.db"\n')

                config = get_multi_db_config()
                assert isinstance(config, MultiDbConfig)
                assert config.default == "primary"
                assert len(config.databases) == 2
                assert "primary" in config.databases
                assert "analytics" in config.databases
            finally:
                os.chdir(old_cwd)

    def test_get_database_uses_dev_database_in_dev_mode(self):
        """Test get_database switches to dev URL/type when dev mode is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('database_type = "postgresql"\n')
                    f.write(
                        'sqlalchemy_url = "postgresql://user:password@localhost:5432/main"\n'
                    )
                    f.write('dev_database_url = "sqlite:///./development.db"\n')

                set_dev_mode(True)
                config = get_database("primary")

                assert config.sqlalchemy_url == "sqlite:///./development.db"
                assert config.database_type == "sqlite"
            finally:
                os.chdir(old_cwd)

    def test_get_database_dev_mode_requires_dev_database_url(self):
        """Test --dev mode fails when target database lacks dev_database_url."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./primary.db"\n')

                from dbwarden.exceptions import ConfigurationError

                set_dev_mode(True)
                with pytest.raises(
                    ConfigurationError,
                    match="has no dev_database_url configured",
                ):
                    get_database("primary")
            finally:
                os.chdir(old_cwd)

    def test_dev_database_type_requires_dev_database_url(self):
        """Test setting dev_database_type without dev_database_url raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./primary.db"\n')
                    f.write('dev_database_type = "sqlite"\n')

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(
                    ConfigurationError,
                    match="dev_database_url is required",
                ):
                    get_multi_db_config()
            finally:
                os.chdir(old_cwd)

    def test_duplicate_sqlalchemy_urls_raise_error(self):
        """Test duplicate sqlalchemy_url values are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./same.db"\n')
                    f.write("[database.analytics]\n")
                    f.write('sqlalchemy_url = "sqlite:///./same.db"\n')

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(ConfigurationError, match="Duplicate database URL"):
                    get_multi_db_config()
            finally:
                os.chdir(old_cwd)

    def test_duplicate_database_targets_raise_error(self):
        """Test different URLs pointing to same DB target are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write(
                        'sqlalchemy_url = "postgresql://user1:pass1@localhost:5432/main"\n'
                    )
                    f.write("[database.analytics]\n")
                    f.write(
                        'sqlalchemy_url = "postgresql://user2:pass2@localhost:5432/main"\n'
                    )

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(
                    ConfigurationError,
                    match="Duplicate database target",
                ):
                    get_multi_db_config()
            finally:
                os.chdir(old_cwd)

    def test_dev_url_duplicate_against_primary_url_raises_error(self):
        """Test dev_database_url cannot duplicate another database URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                with open("warden.toml", "w") as f:
                    f.write('default = "primary"\n')
                    f.write("[database.primary]\n")
                    f.write('sqlalchemy_url = "sqlite:///./main.db"\n')
                    f.write('dev_database_url = "sqlite:///./dev.db"\n')
                    f.write("[database.analytics]\n")
                    f.write('sqlalchemy_url = "sqlite:///./analytics.db"\n')
                    f.write('dev_database_url = "sqlite:///./main.db"\n')

                from dbwarden.exceptions import ConfigurationError

                with pytest.raises(ConfigurationError, match="Duplicate database URL"):
                    get_multi_db_config()
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
