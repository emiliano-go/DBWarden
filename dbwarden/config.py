from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

import tomllib
from sqlalchemy.engine import make_url

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
    dev_database_url: str | None = None
    dev_database_type: DatabaseType | None = None


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


_USE_DEV_DATABASE = False


def set_dev_mode(enabled: bool) -> None:
    """Enable or disable development database mode for this process."""
    global _USE_DEV_DATABASE
    _USE_DEV_DATABASE = enabled


def is_dev_mode() -> bool:
    """Return whether development database mode is enabled."""
    return _USE_DEV_DATABASE


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


def _validate_database_type(
    database_type: str, name: str, field_name: str
) -> DatabaseType:
    if not isinstance(database_type, str):
        raise ConfigurationError(
            f"Invalid {field_name} for database '{name}'. Must be a string."
        )

    explicit_type = database_type.lower()
    if explicit_type not in (
        "sqlite",
        "postgresql",
        "mysql",
        "mariadb",
        "clickhouse",
    ):
        raise ConfigurationError(
            f"Invalid {field_name} '{explicit_type}' for database '{name}'. "
            f"Must be one of: sqlite, postgresql, mysql, mariadb, clickhouse"
        )
    return explicit_type  # type: ignore[return-value]


def _normalized_url(url: str) -> str:
    try:
        parsed = make_url(url)
        return parsed.render_as_string(hide_password=False)
    except Exception:
        return url.strip()


def _build_database_target_key(url: str, db_type: str, base_dir: Path) -> str:
    """Return a canonical key for identifying the physical target database."""
    parsed = make_url(url)

    if db_type == "sqlite":
        db_path = parsed.database or ""
        if db_path == ":memory:" or not db_path:
            return f"sqlite::{db_path or ':memory:'}"

        normalized_path = Path(db_path)
        if not normalized_path.is_absolute():
            normalized_path = (base_dir / normalized_path).resolve()
        else:
            normalized_path = normalized_path.resolve()

        return f"sqlite::{normalized_path.as_posix()}"

    host = parsed.host or ""
    port = str(parsed.port or "")
    database = parsed.database or ""
    return f"{db_type}::{host}:{port}/{database}"


def _validate_unique_database_targets(
    databases: dict[str, DatabaseConfig],
    base_dir: Path,
) -> None:
    normalized_urls: dict[str, str] = {}
    target_keys: dict[str, str] = {}

    for name, config in databases.items():
        entries = [("sqlalchemy_url", config.sqlalchemy_url, config.database_type)]
        if config.dev_database_url and config.dev_database_type:
            entries.append(
                (
                    "dev_database_url",
                    config.dev_database_url,
                    config.dev_database_type,
                )
            )

        for field_name, url, db_type in entries:
            url_key = _normalized_url(url)
            owner = f"{name}.{field_name}"

            if url_key in normalized_urls:
                previous_owner = normalized_urls[url_key]
                raise ConfigurationError(
                    "Duplicate database URL detected in warden.toml: "
                    f"'{owner}' and '{previous_owner}' point to the same URL."
                )
            normalized_urls[url_key] = owner

            target_key = _build_database_target_key(url, db_type, base_dir)
            if target_key in target_keys:
                previous_owner = target_keys[target_key]
                raise ConfigurationError(
                    "Duplicate database target detected in warden.toml: "
                    f"'{owner}' and '{previous_owner}' point to the same database target."
                )
            target_keys[target_key] = owner


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

    config_dir = toml_path.parent

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
            database_type = _validate_database_type(
                db_config["database_type"],
                name,
                "database_type",
            )

        model_paths = None
        if "model_paths" in db_config:
            model_paths = db_config["model_paths"]
            if isinstance(model_paths, str):
                model_paths = [p.strip() for p in model_paths.split(",") if p.strip()]

        migrations_dir = db_config.get("migrations_dir", f"migrations/{name}")
        postgres_schema = db_config.get("postgres_schema", None)

        dev_database_url = db_config.get("dev_database_url")
        dev_database_type = None
        if "dev_database_type" in db_config and not dev_database_url:
            raise ConfigurationError(
                f"dev_database_url is required when dev_database_type is set for database '{name}'."
            )

        if dev_database_url:
            dev_database_type = _infer_database_type(dev_database_url)
            if "dev_database_type" in db_config:
                dev_database_type = _validate_database_type(
                    db_config["dev_database_type"],
                    name,
                    "dev_database_type",
                )

        databases[name] = DatabaseConfig(
            sqlalchemy_url=sqlalchemy_url,
            database_type=database_type,
            model_paths=model_paths,
            migrations_dir=migrations_dir,
            postgres_schema=postgres_schema,
            dev_database_url=dev_database_url,
            dev_database_type=dev_database_type,
        )

    if default not in databases:
        available = list(databases.keys())
        raise ConfigurationError(
            f"Default database '{default}' not found in [database] section. "
            f"Available databases: {available}"
        )

    _validate_unique_database_targets(databases, config_dir)

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

    selected = config.databases[name]

    if not is_dev_mode():
        return selected

    if not selected.dev_database_url:
        raise ConfigurationError(
            f"--dev mode is enabled, but database '{name}' has no dev_database_url configured."
        )

    dev_database_type = selected.dev_database_type or _infer_database_type(
        selected.dev_database_url
    )

    return replace(
        selected,
        sqlalchemy_url=selected.dev_database_url,
        database_type=dev_database_type,
    )


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
