import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dbwarden.config import get_database
from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.engine.model_discovery import (
    get_all_model_tables,
    auto_discover_model_paths,
    generate_create_table_sql,
    generate_drop_table_sql,
    generate_add_column_sql,
    extract_tables_from_migrations,
    extract_tables_from_database,
    ModelTable,
)
from dbwarden.engine.version import (
    get_migrations_directory,
    get_next_migration_number,
    generate_migration_filename,
)
from dbwarden.logging import get_logger


def get_pending_migration_statements(migrations_dir: str) -> set[str]:
    """
    Get all SQL statements from all migration files (for deduplication).

    Args:
        migrations_dir: Path to migrations directory.

    Returns:
        Set of normalized SQL statements from all migration files.
    """
    all_statements = set()

    if not os.path.exists(migrations_dir):
        return all_statements

    for filename in os.listdir(migrations_dir):
        if not filename.endswith(".sql"):
            continue
        filepath = os.path.join(migrations_dir, filename)
        statements = parse_upgrade_statements(filepath)
        for stmt in statements:
            normalized = stmt.strip()
            if normalized:
                all_statements.add(normalized)

    return all_statements


def make_migrations_cmd(
    description: str | None = None,
    verbose: bool = False,
    database: str | None = None,
) -> None:
    """
    Auto-generate SQL migration from SQLAlchemy models.

    Args:
        description: Description for the migration.
        verbose: Enable verbose logging.
        database: Target database name.
    """
    logger = get_logger(verbose=verbose)

    config = get_database(database)
    db_name = database or config.sqlalchemy_url.split("/")[-1].split("?")[0]
    model_paths = config.model_paths

    if model_paths is None:
        model_paths = auto_discover_model_paths()

    if not model_paths:
        logger.warning("No model paths found. Please set model_paths in warden.toml")
        print("No SQLAlchemy models found. Please:")
        print("  1. Create models/ directory with your SQLAlchemy models")
        print("  2. Or set model_paths in warden.toml")
        return

    logger.info(f"Discovering models in: {model_paths}")
    tables = get_all_model_tables(model_paths)

    if not tables:
        logger.warning("No tables found in models")
        print("No tables found in the specified model paths.")
        return

    logger.info(f"Found {len(tables)} tables in models")

    migrations_dir = get_migrations_directory(database)
    next_number = get_next_migration_number(migrations_dir)
    safe_desc = re.sub(r"[^a-zA-Z0-9]", "_", description or "auto_generated").lower()

    filename = generate_migration_filename(db_name, safe_desc, next_number)

    upgrade_sql, rollback_sql = generate_migration_sql(
        tables, migrations_dir, database, db_name
    )

    if not upgrade_sql.strip():
        print(
            "No new migrations to generate - all models already covered by existing migrations."
        )
        return

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


def generate_migration_sql(
    tables: list,
    migrations_dir: str | None = None,
    database: str | None = None,
    db_name: str | None = None,
) -> tuple[str, str]:
    """
    Generate upgrade and rollback SQL from table definitions.

    Compares model tables with the actual database schema to generate:
    - CREATE TABLE for new tables
    - ALTER TABLE ADD COLUMN for new columns in existing tables

    Args:
        tables: List of ModelTable objects.
        migrations_dir: Path to migrations directory.
        database: Database name for backend-specific types.
        db_name: Database name for filename generation.

    Returns:
        Tuple of (upgrade_sql, rollback_sql).
    """
    try:
        config = get_database(database)
        existing_tables = extract_tables_from_database(config.sqlalchemy_url)
    except Exception:
        existing_tables = {}

    migration_tables = {}
    if migrations_dir:
        migration_tables = extract_tables_from_migrations(migrations_dir)

    known_tables: dict[str, set[str]] = {
        table_name: {col.lower() for col in columns}
        for table_name, columns in existing_tables.items()
    }
    for table_name, columns in migration_tables.items():
        if table_name in known_tables:
            known_tables[table_name].update({col.lower() for col in columns})
        else:
            known_tables[table_name] = {col.lower() for col in columns}

    upgrade_parts = []
    rollback_parts = []

    for table in tables:
        existing_columns = known_tables.get(table.name, set())

        if not existing_columns:
            create_sql = generate_create_table_sql(table, db_name)
            upgrade_parts.append(create_sql)
            rollback_parts.append(generate_drop_table_sql(table.name))
        else:
            for column in table.columns:
                if column.name.lower() not in existing_columns:
                    alter_sql = generate_add_column_sql(table.name, column, db_name)
                    upgrade_parts.append(alter_sql)
                    rollback_parts.append(
                        f"ALTER TABLE {table.name} DROP COLUMN {column.name}"
                    )

                    known_tables.setdefault(table.name, set()).add(column.name.lower())

    rollback_parts.reverse()

    if migrations_dir:
        existing_statements = get_pending_migration_statements(migrations_dir)
        filtered_upgrade_parts = []
        filtered_rollback_parts = []

        for upgrade_sql, rollback_sql in zip(upgrade_parts, rollback_parts):
            if upgrade_sql.strip() in existing_statements:
                continue
            filtered_upgrade_parts.append(upgrade_sql)
            filtered_rollback_parts.append(rollback_sql)

        upgrade_parts = filtered_upgrade_parts
        rollback_parts = filtered_rollback_parts

    return "\n\n".join(upgrade_parts), "\n\n".join(rollback_parts)


def new_migration_cmd(
    description: str,
    version: str | None = None,
    database: str | None = None,
) -> None:
    """
    Create a new manual migration file.

    Args:
        description: Description of the migration.
        version: Version number for the migration.
        database: Target database name.
    """
    logger = get_logger()

    config = get_database(database)
    db_name = database or config.sqlalchemy_url.split("/")[-1].split("?")[0]

    migrations_dir = get_migrations_directory(database)

    if version is None:
        version = get_next_migration_number(migrations_dir)

    safe_description = re.sub(r"[^a-zA-Z0-9]", "_", description).lower()
    filename = generate_migration_filename(db_name, safe_description, version)
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
