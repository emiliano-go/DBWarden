import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from dbwarden.constants import TOML_FILE
from dbwarden.exceptions import ConfigurationError


@dataclass
class DbwardenConfig:
    """
    Configuration settings for DBWarden migrations.

    Attributes:
        sqlalchemy_url (str): The SQLAlchemy database connection URL.
        async_mode (bool): If True, uses async database connections.
            Defaults to False.
        model_paths (list[str] | None): Optional list of paths to SQLAlchemy
            model files for automatic migration generation. Defaults to None.
        postgres_schema (str | None): Optional PostgreSQL schema to use.
            Defaults to None.
    """

    sqlalchemy_url: str
    async_mode: bool = False
    model_paths: list[str] | None = None
    postgres_schema: str | None = None

    def __post_init__(self):
        if not isinstance(self.async_mode, bool):
            raise TypeError(
                f"async_mode must be bool, got {type(self.async_mode).__name__}"
            )


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


def get_config() -> DbwardenConfig:
    """
    Load configuration from warden.toml file.

    Returns:
        DbwardenConfig: Configuration dataclass with all required values.

    Raises:
        ConfigurationError: If warden.toml is not found or is missing required values.
    """
    toml_path = get_toml_path()

    if not toml_path:
        raise ConfigurationError(
            f"warden.toml not found. Please create a warden.toml file in {Path.cwd()} or a parent directory. "
            f"Required: sqlalchemy_url\n"
            f'Example: sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"'
        )

    return _load_from_toml(toml_path)


def _load_from_toml(path: Path) -> DbwardenConfig:
    """
    Load configuration from warden.toml file.

    Args:
        path: Path to warden.toml file.

    Returns:
        DbwardenConfig: Configuration dataclass.
    """
    with open(path, "rb") as f:
        config_data = tomllib.load(f)

    toml_config = config_data.get("warden", config_data)

    sqlalchemy_url = toml_config.get("sqlalchemy_url")
    if not sqlalchemy_url:
        raise ConfigurationError(
            "sqlalchemy_url is required in warden.toml. "
            'Example: sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"'
        )

    async_mode = toml_config.get("async", False)

    model_paths = None
    if "model_paths" in toml_config:
        model_paths = toml_config["model_paths"]
        if isinstance(model_paths, str):
            model_paths = [p.strip() for p in model_paths.split(",") if p.strip()]

    postgres_schema = toml_config.get("postgres_schema", None)

    return DbwardenConfig(
        sqlalchemy_url=sqlalchemy_url,
        async_mode=async_mode,
        model_paths=model_paths,
        postgres_schema=postgres_schema,
    )


def get_non_secret_env_vars() -> dict[str, str]:
    """
    Get configuration info for display (excluding secrets).

    Returns:
        dict: Non-sensitive configuration info.
    """
    try:
        config = get_config()
        return {
            "sqlalchemy_url": "***",
            "async": str(config.async_mode).lower(),
            "model_paths": ", ".join(config.model_paths) if config.model_paths else "",
            "postgres_schema": config.postgres_schema or "",
        }
    except ConfigurationError:
        return {"error": "warden.toml not found or invalid"}
