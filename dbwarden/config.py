from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import tomllib

from dbwarden.constants import TOML_FILE
from dbwarden.exceptions import ConfigurationError

DatabaseType = Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"]


@dataclass
class DatabaseConfig:
    """
    Configuration settings for a single database.

    Attributes:
        sqlalchemy_url (str): The SQLAlchemy database connection URL.
        database_type (DatabaseType): The database type (sqlite, postgresql, mysql, mariadb, clickhouse).
        model_paths (list[str] | None): Optional list of paths to SQLAlchemy
            model files for automatic migration generation. Defaults to None.
        migrations_dir (str): Directory for migration files. Defaults to "migrations".
        postgres_schema (str | None): Optional PostgreSQL schema to use.
            Defaults to None.
    """

    sqlalchemy_url: str
    database_type: DatabaseType
    model_paths: list[str] | None = None
    migrations_dir: str = "migrations"
    postgres_schema: str | None = None


@dataclass
class MultiDbConfig:
    """
    Multi-database configuration for DBWarden.

    Attributes:
        databases (dict[str, DatabaseConfig]): Dictionary mapping database names to configs.
        default (str): Name of the default database. Defaults to "default".
    """

    databases: dict[str, DatabaseConfig] = field(default_factory=dict)
    default: str = "default"


def get_toml_path() -> Path | None:
    """
    Find the warden.toml file by searching up the directory tree.

    Returns:
        Path | None: The path to warden.toml if found, None otherwise.
    """
    current = Path.cwd().resolve()

    while True:
        toml_path = current / TOML_FILE
        if toml_path.exists():
            return toml_path

        if current.parent == current:
            break
        current = current.parent

    return None


def _infer_database_type(sqlalchemy_url: str) -> DatabaseType:
    """
    Infer database type from SQLAlchemy URL.

    Args:
        sqlalchemy_url: The database connection URL.

    Returns:
        DatabaseType: The inferred database type.
    """
    url_lower = sqlalchemy_url.lower()
    if url_lower.startswith("sqlite"):
        return "sqlite"
    elif url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
        return "postgresql"
    elif url_lower.startswith("mysql"):
        return "mysql"
    elif url_lower.startswith("mariadb"):
        return "mariadb"
    elif url_lower.startswith("clickhouse"):
        return "clickhouse"
    return "sqlite"


def get_multi_db_config() -> MultiDbConfig:
    """
    Load multi-database configuration from warden.toml file.

    Returns:
        MultiDbConfig: Multi-database configuration dataclass.

    Raises:
        ConfigurationError: If warden.toml is not found or is missing required values.
    """
    toml_path = get_toml_path()

    if not toml_path:
        raise ConfigurationError(
            f"warden.toml not found. Please create a warden.toml file in {Path.cwd()} or a parent directory.\n"
            f"Required format:\n"
            f'  default = "primary"\n'
            f"  [database.primary]\n"
            f'  sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"\n'
            f'  migrations_dir = "migrations/primary"\n'
            f'  model_paths = ["./models/"]'
        )

    with open(toml_path, "rb") as f:
        config_data = tomllib.load(f)

    toml_config = config_data.get("warden", config_data)

    default = toml_config.get("default", "default")
    databases: dict[str, DatabaseConfig] = {}

    database_section = toml_config.get("database", {})
    if not database_section:
        raise ConfigurationError(
            "No [database] section found in warden.toml. "
            "Multi-database format is required.\n"
            f'  default = "primary"\n'
            f"  [database.primary]\n"
            f'  sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"'
        )

    for name, db_config in database_section.items():
        if not isinstance(db_config, dict):
            raise ConfigurationError(
                f"Invalid database configuration for '{name}'. Expected a table with settings."
            )

        sqlalchemy_url = db_config.get("sqlalchemy_url")
        if not sqlalchemy_url:
            raise ConfigurationError(
                f"sqlalchemy_url is required for database '{name}' in warden.toml. "
                f'Example: sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"'
            )

        database_type = _infer_database_type(sqlalchemy_url)
        if "database_type" in db_config:
            explicit_type = db_config["database_type"].lower()
            if explicit_type not in (
                "sqlite",
                "postgresql",
                "mysql",
                "mariadb",
                "clickhouse",
            ):
                raise ConfigurationError(
                    f"Invalid database_type '{explicit_type}' for database '{name}'. "
                    f"Must be one of: sqlite, postgresql, mysql, mariadb, clickhouse"
                )
            database_type = explicit_type

        model_paths = None
        if "model_paths" in db_config:
            model_paths = db_config["model_paths"]
            if isinstance(model_paths, str):
                model_paths = [p.strip() for p in model_paths.split(",") if p.strip()]

        migrations_dir = db_config.get("migrations_dir", f"migrations/{name}")
        postgres_schema = db_config.get("postgres_schema", None)

        databases[name] = DatabaseConfig(
            sqlalchemy_url=sqlalchemy_url,
            database_type=database_type,
            model_paths=model_paths,
            migrations_dir=migrations_dir,
            postgres_schema=postgres_schema,
        )

    if default not in databases:
        available = list(databases.keys())
        raise ConfigurationError(
            f"Default database '{default}' not found in [database] section. "
            f"Available databases: {available}"
        )

    return MultiDbConfig(databases=databases, default=default)


def get_database(name: str | None = None) -> DatabaseConfig:
    """
    Get database config by name or default.

    Args:
        name: Database name. If None, returns the default database.

    Returns:
        DatabaseConfig: Configuration for the specified database.

    Raises:
        ConfigurationError: If database name is not found.
    """
    config = get_multi_db_config()

    if name is None:
        name = config.default

    if name not in config.databases:
        available = list(config.databases.keys())
        raise ConfigurationError(
            f"Database '{name}' not found in warden.toml. "
            f"Available databases: {available}"
        )

    return config.databases[name]


def list_databases() -> list[str]:
    """
    List all configured database names.

    Returns:
        list[str]: List of database names.
    """
    config = get_multi_db_config()
    return list(config.databases.keys())


def get_config() -> DatabaseConfig:
    """
    Get the default database config (for backward compatibility).

    Returns:
        DatabaseConfig: Configuration for the default database.
    """
    return get_database(None)
