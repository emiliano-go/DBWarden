import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from dbwarden.constants import ENV_FILE
from dbwarden.exceptions import ConfigurationError, EnvFileNotFoundError


def _reload_dotenv() -> None:
    """Reload .env file from current working directory."""
    env_path = get_env_path()
    load_dotenv(dotenv_path=env_path)


@dataclass
class StrataConfig:
    """
    Configuration settings for Strata migrations.

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


def get_env_path() -> Path:
    """
    Find the .env file by searching up the directory tree.

    Returns:
        Path: The path to the .env file.

    Raises:
        EnvFileNotFoundError: If .env file is not found.
    """
    current = Path.cwd().resolve()

    while True:
        env_path = current / ENV_FILE
        if env_path.exists():
            return env_path

        if current.parent == current:
            break
        current = current.parent

    raise EnvFileNotFoundError(
        f".env file not found. Please create a .env file in {Path.cwd()} or a parent directory. "
        f"Required variables: STRATA_SQLALCHEMY_URL"
    )


def validate_env_file() -> None:
    """
    Validate that .env file exists in the current directory or parent.

    Raises:
        EnvFileNotFoundError: If .env file is not found.
    """
    get_env_path()


def get_config() -> StrataConfig:
    """
    Load configuration from .env file.

    Returns:
        StrataConfig: Configuration dataclass with all required values.

    Raises:
        ConfigurationError: If required configuration is missing.
    """
    _reload_dotenv()

    sqlalchemy_url = os.getenv("STRATA_SQLALCHEMY_URL")
    if not sqlalchemy_url:
        raise ConfigurationError(
            "STRATA_SQLALCHEMY_URL is required in .env file. "
            'Example: STRATA_SQLALCHEMY_URL="postgresql://user:password@localhost:5432/mydb"'
        )

    async_mode_str = os.getenv("STRATA_ASYNC", "").lower()
    async_mode = async_mode_str in ("true", "1", "yes")

    model_paths_str = os.getenv("STRATA_MODEL_PATHS", "")
    model_paths = None
    if model_paths_str:
        model_paths = [p.strip() for p in model_paths_str.split(",") if p.strip()]

    postgres_schema = os.getenv("STRATA_POSTGRES_SCHEMA", None)

    return StrataConfig(
        sqlalchemy_url=sqlalchemy_url,
        async_mode=async_mode,
        model_paths=model_paths,
        postgres_schema=postgres_schema,
    )


def get_non_secret_env_vars() -> dict[str, str]:
    """
    Get environment variables for display (excluding secrets).

    Returns:
        dict: Non-sensitive environment variables.
    """
    public_vars = {
        "STRATA_SQLALCHEMY_URL": "***" if os.getenv("STRATA_SQLALCHEMY_URL") else None,
        "STRATA_ASYNC": os.getenv("STRATA_ASYNC", "false"),
        "STRATA_MODEL_PATHS": os.getenv("STRATA_MODEL_PATHS", ""),
        "STRATA_POSTGRES_SCHEMA": os.getenv("STRATA_POSTGRES_SCHEMA", ""),
    }
    return {k: v for k, v in public_vars.items() if v}
