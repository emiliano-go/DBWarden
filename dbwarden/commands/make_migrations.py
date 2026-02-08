import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dbwarden.config import get_config
from dbwarden.engine.model_discovery import (
    get_all_model_tables,
    auto_discover_model_paths,
    generate_create_table_sql,
    generate_drop_table_sql,
)
from dbwarden.engine.version import (
    get_migrations_directory,
    get_next_migration_number,
    get_migration_filepaths_by_version,
)
from dbwarden.logging import get_logger
from dbwarden.repositories import get_migrated_versions


def make_migrations_cmd(
    description: str | None = None,
    verbose: bool = False,
) -> None:
    """
    Auto-generate SQL migration from SQLAlchemy models.

    Args:
        description: Description for the migration.
        verbose: Enable verbose logging.
    """
    logger = get_logger(verbose=verbose)

    applied_versions = get_migrated_versions()

    migrations_dir = get_migrations_directory()
    pending_migrations = get_migration_filepaths_by_version(migrations_dir)

    pending_to_apply = {
        v: p for v, p in pending_migrations.items() if v not in applied_versions
    }

    if pending_to_apply:
        raise ValueError(
            f"Cannot generate migrations while {len(pending_to_apply)} migrations are pending. "
            f"Please run 'dbwarden migrate' first."
        )

    logger.log_execution_mode("async" if is_async_enabled() else "sync")

    config = get_config()
    model_paths = config.model_paths

    if model_paths is None:
        model_paths = auto_discover_model_paths()

    if not model_paths:
        logger.warning("No model paths found. Please set DBWARDEN_MODEL_PATHS in .env")
        print("No SQLAlchemy models found. Please:")
        print("  1. Create models/ directory with your SQLAlchemy models")
        print("  2. Or set DBWARDEN_MODEL_PATHS in .env")
        return

    logger.info(f"Discovering models in: {model_paths}")
    tables = get_all_model_tables(model_paths)

    if not tables:
        logger.warning("No tables found in models")
        print("No tables found in the specified model paths.")
        return

    logger.info(f"Found {len(tables)} tables in models")

    migrations_dir = get_migrations_directory()
    next_number = get_next_migration_number(migrations_dir)
    safe_desc = re.sub(r"[^a-zA-Z0-9]", "_", description or "auto_generated").lower()
    filename = f"{next_number}_{safe_desc}.sql"

    upgrade_sql, rollback_sql = generate_migration_sql(tables)

    filepath = os.path.join(migrations_dir, filename)

    content = f"""-- upgrade

{upgrade_sql}

-- rollback

{rollback_sql}
"""

    with open(filepath, "w") as f:
        f.write(content)

    logger.info(f"Created migration file: {filename}")
    print(f"Created migration file: {filepath}")
    print(f"Tables included: {', '.join(t.name for t in tables)}")


def generate_migration_sql(tables: list) -> tuple[str, str]:
    """
    Generate upgrade and rollback SQL from table definitions.

    Args:
        tables: List of ModelTable objects.

    Returns:
        Tuple of (upgrade_sql, rollback_sql).
    """
    upgrade_parts = []
    rollback_parts = []

    for table in tables:
        upgrade_parts.append(generate_create_table_sql(table))
        rollback_parts.append(generate_drop_table_sql(table.name))

    rollback_parts.reverse()

    return "\n\n".join(upgrade_parts), "\n\n".join(rollback_parts)


def new_migration_cmd(description: str, version: str | None = None) -> None:
    """
    Create a new manual migration file.

    Args:
        description: Description of the migration.
        version: Version number for the migration.
    """
    logger = get_logger()

    migrations_dir = get_migrations_directory()

    if version is None:
        version = get_next_migration_number(migrations_dir)

    safe_description = re.sub(r"[^a-zA-Z0-9]", "_", description).lower()
    filename = f"{version}_{safe_description}.sql"
    filepath = os.path.join(migrations_dir, filename)

    content = f"""-- upgrade

-- {description}

-- rollback

-- {description}
"""

    with open(filepath, "w") as f:
        f.write(content)

    logger.info(f"Created migration file: {filename}")
    print(f"Created migration file: {filepath}")


def is_async_enabled() -> bool:
    """Check if async mode is enabled."""
    from dbwarden.database.connection import is_async_enabled

    return is_async_enabled()
