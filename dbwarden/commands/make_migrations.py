import os
import re
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dbwarden.config import get_database, get_multi_db_config
from dbwarden.engine.checksum import calculate_checksum
from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.engine.model_discovery import (
    get_all_model_tables,
    auto_discover_model_paths,
    generate_create_table_sql,
    generate_drop_object_sql,
    generate_add_column_sql,
    extract_tables_from_migrations,
    extract_tables_from_database,
    ModelTable,
)
from dbwarden.engine.migration_name import Change, autogenerate_migration_name
from dbwarden.engine.version import (
    get_migrations_directory,
    get_next_migration_number,
    generate_migration_filename,
)
from dbwarden.logging import get_logger
from dbwarden.output import console


@dataclass
class RenameIntent:
    table: str
    old_name: str
    new_name: str


def _parse_rename_flags(flags: list[str]) -> list[RenameIntent]:
    intents: list[RenameIntent] = []
    for flag in flags:
        parts = flag.split(".", 1)
        if len(parts) != 2 or ":" not in parts[1]:
            raise ValueError(
                f"Invalid --rename format: {flag!r}. Expected table.old_name:new_name"
            )
        table = parts[0]
        old_new = parts[1].split(":", 1)
        if len(old_new) != 2 or not old_new[0] or not old_new[1]:
            raise ValueError(
                f"Invalid --rename format: {flag!r}. Expected table.old_name:new_name"
            )
        intents.append(RenameIntent(table=table, old_name=old_new[0], new_name=old_new[1]))
    return intents


def _format_rename_warning(intents: list[tuple[str, str, str, str]]) -> str:
    lines = [
        "The following auto-detected column renames were not confirmed:"
    ]
    for tbl, old, new, _flag_example in intents:
        lines.append(
            f"  {tbl}.{old} \u2192 {new} (use --rename {tbl}.{old}:{new} to confirm)"
        )
    lines.append("These will be emitted as DROP + ADD instead of RENAME.")
    return "\n".join(lines)


def _prompt_rename_confirmations(
    renames: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    confirmed: list[tuple[str, str, str]] = []
    if not renames:
        return confirmed
    if len(renames) == 1:
        tbl, old, new = renames[0]
        answer = input(
            f"Detected rename: {tbl}.{old} \u2192 {tbl}.{new}. Confirm rename? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            confirmed.append((tbl, old, new))
    else:
        print("Detected column renames:")
        for i, (tbl, old, new) in enumerate(renames, 1):
            print(f"  [{i}] {tbl}.{old} \u2192 {tbl}.{new}")
        print("  [s] Skip all")
        print("  [a] Accept all")
        answer = input("Select renames to confirm (e.g. 1,3 or a or s): ").strip().lower()
        if answer == "a":
            confirmed.extend(renames)
        elif answer != "s":
            for part in answer.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(renames):
                        confirmed.append(renames[idx])
    return confirmed


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
    output_plan: bool = False,
    rename_flags: list[str] | None = None,
) -> None:
    """
    Auto-generate SQL migration from SQLAlchemy models.

    Args:
        description: Description for the migration.
        verbose: Enable verbose logging.
        database: Target database name.
        output_plan: Print the migration plan JSON without writing files.
        rename_flags: List of user-supplied --rename flag strings.
    """
    logger = get_logger()

    config = get_database(database)
    multi_config = get_multi_db_config()
    db_name = database or multi_config.default
    model_paths = config.model_paths

    if model_paths is None:
        model_paths = auto_discover_model_paths()

    if not model_paths:
        logger.warning("No model paths found. Please set model_paths in warden.toml")
        console.print("No SQLAlchemy models found. Please:", style="yellow")
        console.print("  1. Create models/ directory with your SQLAlchemy models", style="white")
        console.print("  2. Or set model_paths in dbwarden config", style="white")
        return

    logger.log_model_paths(model_paths)
    logger.info(f"Discovering models in: {model_paths}")
    tables = get_all_model_tables(model_paths, db_name=database)

    if not tables:
        logger.warning("No tables found in models")
        console.print("No tables found in the specified model paths.", style="yellow")
        return

    for table in tables:
        logger.log_model_discovered(table.name, [c.name for c in table.columns])

    logger.info(f"Found {len(tables)} tables in models")

    rename_intents: list[RenameIntent] = []
    if rename_flags:
        rename_intents = _parse_rename_flags(rename_flags)

    confirmed_renames: set[tuple[str, str, str]] = set()
    resolved_from_map: dict[tuple[str, str, str], str] = {}

    for intent in rename_intents:
        key = (intent.table, intent.old_name, intent.new_name)
        confirmed_renames.add(key)
        resolved_from_map[key] = "rename_flag"

    try:
        from dbwarden.engine.snapshot import (
            find_latest_snapshot,
            diff_models_against_snapshot,
        )
        snapshot = find_latest_snapshot(database)
    except Exception:
        snapshot = None

    if snapshot is not None:
        model_by_name = {t.name: t for t in tables}
        snapshot_tables = snapshot.get("tables", {})
        auto_detected_renames: list[tuple[str, str, str]] = []

        for table in tables:
            if table.name not in snapshot_tables:
                continue
            snap_cols = snapshot_tables[table.name].get("columns", {})
            model_cols = {c.name: c for c in table.columns}

            dropped = [(n, snap_cols[n]) for n in snap_cols if n not in model_cols]
            added = [(n, model_cols[n]) for n in model_cols if n not in snap_cols]

            if not dropped or not added:
                continue

            from dbwarden.engine.snapshot import detect_renames
            renames = detect_renames(table.name, dropped, added)
            for old, new in renames:
                key = (table.name, old, new)
                if key not in confirmed_renames:
                    auto_detected_renames.append((table.name, old, new))

        if auto_detected_renames:
            if sys.stdin.isatty():
                prompted = _prompt_rename_confirmations(auto_detected_renames)
                for key in prompted:
                    confirmed_renames.add(key)
                    resolved_from_map[key] = "prompt"
            else:
                logger.warning(_format_rename_warning(
                    (t, o, n, f"{t}.{o}:{n}")
                    for t, o, n in auto_detected_renames
                ))
                console.print(
                    _format_rename_warning(
                        (t, o, n, f"{t}.{o}:{n}")
                        for t, o, n in auto_detected_renames
                    ),
                    style="yellow",
                )

    migrations_dir = get_migrations_directory(database)
    next_number = get_next_migration_number(migrations_dir)

    upgrade_sql, rollback_sql, changes = generate_migration_sql(
        tables, migrations_dir, database, db_name,
        confirmed_renames=confirmed_renames,
        resolved_from_map=resolved_from_map,
    )

    safe_desc = _resolve_migration_description(description, changes)
    filename = generate_migration_filename(db_name, safe_desc, next_number)
    plan = build_migration_plan(
        migration_id=Path(filename).stem,
        changes=changes,
        upgrade_sql=upgrade_sql,
    )

    if output_plan:
        console.print(json.dumps(plan, indent=2), markup=False, highlight=False)
        return

    if not upgrade_sql.strip():
        console.print(
            "No new migrations to generate - all models already covered by existing migrations.",
            style="cyan",
        )
        return

    filepath = os.path.join(migrations_dir, filename)
    plan_filepath = str(Path(filepath).with_suffix(".plan.json"))

    migrations_dir_canonical = os.path.realpath(migrations_dir)
    filepath_canonical = os.path.realpath(filepath)
    if not filepath_canonical.startswith(migrations_dir_canonical + os.sep):
        raise ValueError(
            f"Invalid migration path: {filename} resolves outside migrations directory. "
            "Path traversal not allowed."
        )

    content = f"""-- upgrade

{upgrade_sql}

-- rollback

{rollback_sql}
"""

    with open(filepath, "w") as f:
        f.write(content)

    with open(plan_filepath, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
        f.write("\n")

    logger.info(f"Created migration file: {filename}")
    console.print(f"Created migration file: {filepath}", style="green")
    console.print(f"Created migration plan: {plan_filepath}", style="green")
    console.print(f"Tables included: {', '.join(t.name for t in tables)}", style="cyan")


def _resolve_migration_description(
    description: str | None,
    changes: list[Change],
) -> str:
    if description is None and changes:
        safe_desc = autogenerate_migration_name(changes)
        if not safe_desc:
            safe_desc = "auto_generated"
        return safe_desc
    return re.sub(r"[^a-zA-Z0-9]", "_", description or "auto_generated").lower()


def build_migration_plan(
    migration_id: str,
    changes: list[Change],
    upgrade_sql: str,
) -> dict[str, object]:
    operations = [_build_plan_operation(change) for change in changes]
    checksum = calculate_checksum([upgrade_sql]) if upgrade_sql.strip() else calculate_checksum([])
    return {
        "migration_id": migration_id,
        "operations": operations,
        "required_flags": [],
        "checksum": checksum,
    }


def _build_plan_operation(change: Change) -> dict[str, str]:
    operation: dict[str, str] = {
        "type": change.operation,
        "table": change.table,
        "severity": "INFO",
    }
    if change.resolved_from:
        operation["resolved_from"] = change.resolved_from
    if change.target:
        if change.operation == "rename_column":
            operation["new_name"] = change.target
        else:
            operation["column"] = change.target
    return operation


def generate_migration_sql(
    tables: list,
    migrations_dir: str | None = None,
    database: str | None = None,
    db_name: str | None = None,
    confirmed_renames: set[tuple[str, str, str]] | None = None,
    resolved_from_map: dict[tuple[str, str, str], str] | None = None,
) -> tuple[str, str, list[Change]]:
    """
    Generate upgrade and rollback SQL from table definitions.

    Compares model tables with the actual database schema to generate:
    - CREATE TABLE for new tables
    - ALTER TABLE ADD COLUMN for new columns in existing tables

    When a schema snapshot exists, it uses the snapshot for rename detection.
    Otherwise falls back to diffing against the live database.

    Args:
        tables: List of ModelTable objects.
        migrations_dir: Path to migrations directory.
        database: Database name for backend-specific types.
        db_name: Database name for filename generation.
        confirmed_renames: Set of (table, old_name, new_name) tuples confirmed by user.
        resolved_from_map: Optional mapping from rename key to origin string.

    Returns:
        Tuple of (upgrade_sql, rollback_sql, changes).
    """
    upgrade_sql: str = ""
    rollback_sql: str = ""
    changes: list[Change] = []
    snapshot: Any = None
    confirmed_renames = confirmed_renames or set()

    try:
        from dbwarden.engine.snapshot import (
            find_latest_snapshot,
            diff_models_against_snapshot,
            snapshot_diff_to_sql,
            _apply_rename_intents,
        )

        snapshot = find_latest_snapshot(database)
    except Exception:
        snapshot = None

    if snapshot is not None:
        try:
            upgrade_ops, rollback_ops = diff_models_against_snapshot(
                tables, snapshot, database=database, db_name=db_name
            )
            if confirmed_renames:
                upgrade_ops, rollback_ops = _apply_rename_intents(
                    upgrade_ops, rollback_ops, confirmed_renames, resolved_from_map
                )
            upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(
                upgrade_ops, rollback_ops, database=database, db_name=db_name
            )
        except Exception:
            snapshot = None

    if snapshot is None:
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

        upgrade_parts: list[str] = []
        rollback_parts: list[str] = []
        changes: list[Change] = []

        for table in tables:
            existing_columns = known_tables.get(table.name, set())

            if not existing_columns:
                create_sql = generate_create_table_sql(table, db_name)
                upgrade_parts.append(create_sql)
                rollback_parts.append(generate_drop_object_sql(table))
                changes.append(Change(operation="create_table", table=table.name))
            else:
                for column in table.columns:
                    if column.name.lower() not in existing_columns:
                        alter_sql = generate_add_column_sql(table.name, column, db_name)
                        upgrade_parts.append(alter_sql)
                        rollback_parts.append(
                            f"ALTER TABLE {table.name} DROP COLUMN {column.name}"
                        )
                        changes.append(Change(operation="add_column", table=table.name, target=column.name))
                        known_tables.setdefault(table.name, set()).add(column.name.lower())

        rollback_parts.reverse()

        if migrations_dir:
            existing_statements = get_pending_migration_statements(migrations_dir)
            filtered_upgrade_parts = []
            filtered_rollback_parts = []
            filtered_changes = []

            for upgrade_sql, rollback_sql in zip(upgrade_parts, rollback_parts):
                if upgrade_sql.strip() in existing_statements:
                    continue
                filtered_upgrade_parts.append(upgrade_sql)
                filtered_rollback_parts.append(rollback_sql)

            for change, upgrade_sql in zip(changes, upgrade_parts):
                if upgrade_sql.strip() in existing_statements:
                    continue
                filtered_changes.append(change)

            upgrade_parts = filtered_upgrade_parts
            rollback_parts = filtered_rollback_parts
            changes = filtered_changes

        upgrade_sql = "\n\n".join(upgrade_parts)
        rollback_sql = "\n\n".join(rollback_parts)

    if migrations_dir:
        existing_statements = get_pending_migration_statements(migrations_dir)
        if upgrade_sql.strip():
            from dbwarden.engine.snapshot import _filter_duplicates_from_snapshot_diff
            upgrade_sql, rollback_sql, changes = _filter_duplicates_from_snapshot_diff(
                upgrade_sql, rollback_sql, changes, existing_statements
            )

    return upgrade_sql, rollback_sql, changes


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
    multi_config = get_multi_db_config()
    db_name = database or multi_config.default

    migrations_dir = get_migrations_directory(database)

    if version is None:
        version = get_next_migration_number(migrations_dir)

    safe_description = re.sub(r"[^a-zA-Z0-9]", "_", description).lower()
    filename = generate_migration_filename(db_name, safe_description, version)
    filepath = os.path.join(migrations_dir, filename)

    # Validate the final path stays within migrations directory
    migrations_dir_canonical = os.path.realpath(migrations_dir)
    filepath_canonical = os.path.realpath(filepath)
    if not filepath_canonical.startswith(migrations_dir_canonical + os.sep):
        raise ValueError(
            f"Invalid migration path: {filename} resolves outside migrations directory. "
            "Path traversal not allowed."
        )

    content = f"""-- upgrade

-- {description}

-- rollback

-- {description}
"""

    with open(filepath, "w") as f:
        f.write(content)

    logger.info(f"Created migration file: {filename}")
    console.print(f"Created migration file: {filepath}", style="green")
