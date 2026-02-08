import json
import yaml

from dbwarden.config import get_config, get_non_secret_env_vars
from dbwarden.constants import DBWARDEN_VERSION
from dbwarden.database.connection import get_mode, is_async_enabled
from dbwarden.logging import get_logger


def mode_cmd() -> None:
    """Display current execution mode (sync or async)."""
    mode = get_mode()
    print(f"Execution mode: {mode}")
    print(f"Async enabled: {is_async_enabled()}")


def env_cmd() -> None:
    """Display relevant environment variables without leaking secrets."""
    logger = get_logger()
    config = get_config()
    env_vars = get_non_secret_env_vars()

    print("DBWarden Environment Configuration:")
    print("=" * 50)
    print(f"SQLAlchemy URL: {env_vars.get('STRATA_SQLALCHEMY_URL', '***')}")
    print(f"Async Mode: {env_vars.get('STRATA_ASYNC', 'false')}")
    print(f"Model Paths: {env_vars.get('STRATA_MODEL_PATHS', '(not set)')}")
    print(f"PostgreSQL Schema: {env_vars.get('STRATA_POSTGRES_SCHEMA', '(not set)')}")


def version_cmd() -> None:
    """Display DBWarden version and compatibility information."""
    print(f"DBWarden Version: {DBWARDEN_VERSION}")
    print(f"Python Version: {__import__('sys').version}")
    print("\nSupported Databases:")
    print("  - PostgreSQL (sync + async)")
    print("  - SQLite (sync + async)")
    print("  - MySQL (sync)")
    print("  - Snowflake (sync)")
    print("  - Databricks (sync)")
