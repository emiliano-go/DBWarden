from __future__ import annotations

import json

from rich.table import Table

from dbwarden.config import get_database, get_multi_db_config
from dbwarden.engine.migration_name import Change
from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.output import console


def diff_cmd(
    output_format: str = "table",
    verbose: bool = False,
    database: str | None = None,
    offline: bool = False,
) -> None:
    """
    Show structural differences between models and database.

    Args:
        output_format: Output format (table, json, sql).
        verbose: Enable verbose logging.
        database: Target database name.
        offline: Use model state file instead of live database snapshot.
    """
    config = get_database(database)
    actual_db_name = database or get_multi_db_config().default
    logger = get_logger(
        verbose=verbose, db_name=actual_db_name, db_type=config.database_type
    )

    from dbwarden.engine.model_discovery import (
        get_all_model_tables,
        filter_model_tables_by_name,
        validate_model_tables_exist,
    )

    if not config.model_paths:
        console.print("No model paths configured. Add model_paths to your dbwarden.py config.", style="yellow")
        return

    tables = get_all_model_tables(config.model_paths, db_name=actual_db_name)
    validate_model_tables_exist(tables, config.model_tables, actual_db_name)
    tables = filter_model_tables_by_name(tables, config.model_tables)
    if not tables:
        console.print("No SQLAlchemy models found in the configured model paths.", style="yellow")
        return

    if offline:
        snapshot = _load_offline_snapshot(actual_db_name)
        if snapshot is None:
            return
    else:
        snapshot = _load_live_snapshot(database, logger)

    if snapshot is None:
        console.print("Could not load schema snapshot. Run 'dbwarden migrate' to create one.", style="yellow")
        return

    from dbwarden.engine.snapshot import (
        _filter_duplicates_from_snapshot_diff,
        diff_models_against_snapshot,
        snapshot_diff_to_sql,
    )

    upgrade_ops, rollback_ops = diff_models_against_snapshot(
        tables, snapshot, database=database, db_name=actual_db_name
    )

    if not upgrade_ops:
        console.print("No differences found between models and database.", style="green")
        return

    from dbwarden.engine.snapshot import _apply_rename_intents

    upgrade_ops, rollback_ops = _apply_rename_intents(upgrade_ops, rollback_ops, set())

    upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(
        upgrade_ops, rollback_ops, database=database, db_name=actual_db_name,
    )

    _filter_migration_snapshots(database, upgrade_sql, upgrade_ops, rollback_sql, rollback_ops, changes)

    if output_format == "json":
        _display_json(changes)
    elif output_format == "sql":
        _display_sql(upgrade_sql)
    else:
        _display_table(changes)


def _load_live_snapshot(database: str | None, logger) -> dict | None:
    """Extract a full schema snapshot from the live database."""
    from dbwarden.engine.snapshot import extract_full_schema_snapshot
    try:
        return extract_full_schema_snapshot(database=database)
    except Exception as exc:
        logger.warning("Failed to extract live schema snapshot: %s", exc)
        return None


def _load_offline_snapshot(database: str | None) -> dict | None:
    """Load the model state from an exported JSON file."""
    from dbwarden.commands.make_migrations import get_current_model_state_path, get_model_state_path

    state_path = get_current_model_state_path(database)
    legacy_state_path = get_model_state_path(database, legacy=True)

    if not state_path.exists():
        console.print(
            f"No model state file found at {get_model_state_path(database)}. "
            "Run 'dbwarden export-models' first.",
            style="yellow",
        )
        return None
    try:
        import json
        return json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"Failed to read model state file: {exc}", style="red")
        return None


def _filter_migration_snapshots(database, upgrade_sql, upgrade_ops, rollback_sql, rollback_ops, changes):
    """Try to deduplicate against existing migration statements."""
    from dbwarden.commands.make_migrations import get_pending_migration_statements
    from dbwarden.engine.snapshot import _filter_duplicates_from_snapshot_diff

    migrations_dir = get_migrations_directory(database)
    if not migrations_dir:
        return

    existing_statements = get_pending_migration_statements(migrations_dir)
    if upgrade_sql.strip():
        upgrade_sql, rollback_sql, changes = _filter_duplicates_from_snapshot_diff(
            upgrade_sql, rollback_sql, list(changes), existing_statements
        )


def _display_table(changes: list[Change]) -> None:
    """Display changes as a Rich table."""
    if not changes:
        console.print("No differences found after filtering.", style="green")
        return

    table = Table(title="Schema Diff", show_header=True, header_style="bold magenta")
    table.add_column("Operation", style="cyan")
    table.add_column("Table", style="green")
    table.add_column("Target", style="yellow")
    table.add_column("Severity", style="white")

    for change in changes:
        severity = _severity_for(change.operation)
        table.add_row(
            change.operation,
            change.table or "",
            change.target or "",
            severity,
        )

    console.print(table)
    console.print(f"\nTotal changes: {len(changes)}", style="bold")


def _display_sql(upgrade_sql: str) -> None:
    """Display the generated upgrade SQL."""
    if not upgrade_sql.strip():
        console.print("No SQL changes to display.", style="green")
        return

    import re
    statements = [s.strip() for s in re.split(r"\n\n+", upgrade_sql) if s.strip()]
    console.print("\nGenerated migration SQL:", style="bold cyan")
    for stmt in statements:
        console.print(f"\n{stmt}", markup=False, highlight=False)


def _display_json(changes: list[Change]) -> None:
    """Display changes as JSON."""
    data = [
        {
            "operation": c.operation,
            "table": c.table,
            "target": c.target,
            "severity": _severity_for(c.operation),
        }
        for c in changes
    ]
    console.print(json.dumps(data, indent=2), markup=False, highlight=False)


def _severity_for(operation: str) -> str:
    """Map an operation to a severity level."""
    destructive = {"drop_table", "drop_column", "drop_index", "drop_foreign_key",
                   "drop_unique_constraint", "drop_check_constraint", "drop_exclude_constraint"}
    if operation in destructive:
        return "WARNING"
    return "INFO"


def lock_status_cmd(database: str | None = None) -> None:
    """Check if migration is currently locked."""
    from dbwarden.repositories import check_lock

    is_locked = check_lock(database)
    if is_locked:
        console.print("Migration lock: ACTIVE", style="yellow")
        console.print("Another migration process may be running.", style="white")
    else:
        console.print("Migration lock: INACTIVE", style="green")


def unlock_cmd(database: str | None = None) -> None:
    """Release the migration lock."""
    from dbwarden.repositories import release_lock, check_lock

    if not check_lock(database):
        console.print("Migration lock is not currently held.", style="yellow")
        return

    if release_lock(database):
        console.print("Migration lock released successfully.", style="green")
    else:
        console.print("Failed to release migration lock.", style="bold red")
