import os
import re
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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


def _parse_rename_table_flags(raw_flags: list[str]) -> list[dict[str, str]]:
    intents: list[dict[str, str]] = []
    for flag in raw_flags:
        if ":" not in flag:
            raise ValueError(
                f"Invalid --rename-table format: '{flag}'. "
                f"Expected: old_table:new_table"
            )
        old_table, new_table = flag.split(":", 1)
        old_table = old_table.strip()
        new_table = new_table.strip()
        if not old_table or not new_table:
            raise ValueError(
                f"Invalid --rename-table format: '{flag}'. "
                f"Expected: old_table:new_table"
            )
        intents.append({"old_table": old_table, "new_table": new_table})
    return intents


def _validate_table_rename_intents(
    intents: list[dict[str, str]],
    snapshot: dict[str, Any],
    model_table_names: set[str],
) -> None:
    snapshot_tables = set(snapshot.get("tables", {}).keys())
    for intent in intents:
        if intent["old_table"] not in snapshot_tables:
            raise ValueError(
                f"--rename-table: table '{intent['old_table']}' does not exist "
                f"in latest snapshot."
            )
        if intent["new_table"] in snapshot_tables:
            raise ValueError(
                f"--rename-table: table '{intent['new_table']}' already exists "
                f"in latest snapshot."
            )
        if intent["old_table"] in model_table_names:
            raise ValueError(
                f"--rename-table: '{intent['old_table']}' still present in models. "
                f"Remove it before declaring a rename."
            )
        if intent["new_table"] not in model_table_names:
            raise ValueError(
                f"--rename-table: '{intent['new_table']}' not found in models. "
                f"Add it before declaring a rename."
            )


def _format_table_rename_warning(candidates: list[tuple[str, str, float]]) -> str:
    lines = [
        "Warning: table rename candidates detected but running non-interactive. "
        "Emitting drop+add."
    ]
    for old, new, ratio in candidates:
        lines.append(f"  {old} \u2192 {new}  ({int(ratio * 100):d}% columns match)")
    lines.append("Rerun with --rename-table old:new to resolve.")
    return "\n".join(lines)


def _prompt_table_rename_confirmations(
    candidates: list[tuple[str, str, float]],
) -> list[dict[str, str]]:
    confirmed: list[dict[str, str]] = []
    if not candidates:
        return confirmed
    if len(candidates) == 1:
        old, new, ratio = candidates[0]
        answer = input(
            f"Possible table rename detected:\n"
            f"  {old} \u2192 {new}  ({int(ratio * 100):d}% columns match)\n\n"
            f"Treat as rename? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            confirmed.append({"old_table": old, "new_table": new})
    else:
        print("Possible table renames detected:")
        for i, (old, new, ratio) in enumerate(candidates, 1):
            print(f"  [{i}] {old} \u2192 {new}     ({int(ratio * 100):d}% columns match)")
        print()
        print("Treat as renames? (default: all yes)")
        print("  - Press Enter to rename all")
        answer = input('  - Type numbers to drop+add instead (e.g. "1" or "1 2"): ').strip()
        if not answer:
            for old, new, _ in candidates:
                confirmed.append({"old_table": old, "new_table": new})
        else:
            decline_indices: set[int] = set()
            for part in answer.split():
                if part.isdigit():
                    decline_indices.add(int(part) - 1)
            for i, (old, new, _) in enumerate(candidates):
                if i not in decline_indices:
                    confirmed.append({"old_table": old, "new_table": new})
    return confirmed


def _detect_table_rename_candidates(
    snapshot: dict[str, Any],
    model_tables: list,
    confirmed_table_intents: set[tuple[str, str]],
) -> list[tuple[str, str, float]]:
    from dbwarden.engine.snapshot import _compute_table_overlap, RENAME_TABLE_OVERLAP_THRESHOLD

    snapshot_tables = set(snapshot.get("tables", {}).keys())
    model_table_names = {t.name for t in model_tables}

    dropped_tables = snapshot_tables - model_table_names
    added_tables = model_table_names - snapshot_tables

    candidates: list[tuple[str, str, float]] = []
    for dropped in dropped_tables:
        for added in added_tables:
            if (dropped, added) in confirmed_table_intents:
                continue
            overlap = _compute_table_overlap(dropped, added, snapshot, model_tables)
            if overlap >= RENAME_TABLE_OVERLAP_THRESHOLD:
                candidates.append((dropped, added, overlap))
    return candidates


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


def _run_offline_migrations(description: str | None = None, database: str | None = None) -> None:
    import json
    import os
    from datetime import datetime, timezone
    from pathlib import Path

    from dbwarden.config import get_database, get_multi_db_config
    from dbwarden.engine.model_discovery import get_all_model_tables
    from dbwarden.engine.offline import diff_model_states, model_state_to_dict
    from dbwarden.engine.snapshot import snapshot_diff_to_sql
    from dbwarden.engine.version import get_migrations_directory, get_migration_filepaths_by_version

    config = get_database(database)
    multi_config = get_multi_db_config()
    db_name = database or multi_config.default
    model_paths = config.model_paths

    if not model_paths:
        model_paths = auto_discover_model_paths()

    if not model_paths:
        logger = get_logger()
        logger.warning("No model paths found. Please set model_paths in dbwarden config")
        console.print("No SQLAlchemy models found. Please:", style="yellow")
        console.print("  1. Create models/ directory with your SQLAlchemy models", style="white")
        console.print("  2. Or set model_paths in dbwarden config", style="white")
        return

    state_path = Path(".dbwarden/model_state.json")

    if not state_path.exists():
        console.print("Error: .dbwarden/model_state.json not found.", style="red")
        console.print("Run 'dbwarden export-models' first to establish a baseline.", style="yellow")
        return

    prev_state = json.loads(state_path.read_text())
    current_tables = get_all_model_tables(model_paths, db_name=database)
    current_state = model_state_to_dict(current_tables)

    upgrade_ops, rollback_ops = diff_model_states(prev_state, current_state)

    if not upgrade_ops:
        console.print("No new migrations to generate - all models already covered by existing migrations.", style="cyan")
        return

    from dbwarden.engine.snapshot import snapshot_diff_to_sql, Change
    from dbwarden.engine.version import get_migration_filepaths_by_version

    upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(
        upgrade_ops, rollback_ops, database=database, db_name=db_name,
    )

    if not upgrade_sql.strip():
        console.print("No new migrations to generate - all models already covered by existing migrations.", style="cyan")
        return

    migrations_dir = get_migrations_directory(database)
    existing_statements = get_pending_migration_statements(migrations_dir)

    filtered_statements = []
    filtered_rollback = []
    for u_sql, r_sql in zip(upgrade_sql.strip().split("\n\n"), rollback_sql.strip().split("\n\n")):
        if u_sql.strip() and u_sql.strip() not in existing_statements:
            filtered_statements.append(u_sql.strip())
            filtered_rollback.append(r_sql.strip())

    if not filtered_statements:
        console.print("No new migrations to generate - all models already covered by existing migrations.", style="cyan")
        return

    existing_versions = get_migration_filepaths_by_version(migrations_dir)
    next_version = f"{int(max(existing_versions.keys(), default='0000')) + 1:04d}"
    safe_desc = (description or "offline migration").replace(" ", "_").lower()[:60]
    filename = f"{db_name}__{next_version}_{safe_desc}.sql"

    header = f"-- upgrade\n\n"
    header += "\n\n".join(filtered_statements)
    header += "\n\n-- rollback\n\n"
    header += "\n\n".join(reversed(filtered_rollback))
    header += "\n"

    filepath = os.path.join(migrations_dir, filename)
    with open(filepath, "w") as f:
        f.write(header)

    # Write plan
    migration_id = f"{db_name}__{next_version}_{safe_desc}"
    plan = build_migration_plan(migration_id, changes, "\n\n".join(filtered_statements))
    plan_path = filepath.replace(".sql", ".plan.json")
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2, default=str)

    console.print(f"Created migration file: {filepath}", style="green")
    console.print(f"Created migration plan: {plan_path}", style="green")
    console.print(f"Tables included: {', '.join(sorted(set(c.table for c in changes if hasattr(c, 'table') and c.table)))}", style="cyan")

    state_path.write_text(json.dumps(current_state, indent=2, default=str) + "\n")
    logger = get_logger()
    logger.info(f"Updated model state: {state_path}")


def make_migrations_cmd(
    description: str | None = None,
    verbose: bool = False,
    database: str | None = None,
    output_plan: bool = False,
    rename_flags: list[str] | None = None,
    safe_type_change: bool = False,
    rename_table_flags: list[str] | None = None,
    concurrent: bool = True,
    offline: bool = False,
) -> None:
    """
    Auto-generate SQL migration from SQLAlchemy models.

    Args:
        description: Description for the migration.
        verbose: Enable verbose logging.
        database: Target database name.
        output_plan: Print the migration plan JSON without writing files.
        rename_flags: List of user-supplied --rename flag strings.
        safe_type_change: Use multi-step safe type change strategy.
        rename_table_flags: List of user-supplied --rename-table flag strings.
        concurrent: Use CREATE INDEX CONCURRENTLY on PostgreSQL.
        offline: Use model state file instead of live database.
    """
    logger = get_logger()

    if offline:
        _run_offline_migrations(description=description, database=database)
        return

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

    # --- Column rename flags ---
    rename_intents: list[RenameIntent] = []
    if rename_flags:
        rename_intents = _parse_rename_flags(rename_flags)

    confirmed_renames: set[tuple[str, str, str]] = set()
    resolved_from_map: dict[tuple[str, str, str], str] = {}

    for intent in rename_intents:
        key = (intent.table, intent.old_name, intent.new_name)
        confirmed_renames.add(key)
        resolved_from_map[key] = "rename_flag"

    # --- Table rename flags ---
    confirmed_table_intents: set[tuple[str, str]] = set()
    table_resolved_from_map: dict[tuple[str, str], str] = {}

    if rename_table_flags:
        table_intents = _parse_rename_table_flags(rename_table_flags)
        for intent in table_intents:
            key = (intent["old_table"], intent["new_table"])
            confirmed_table_intents.add(key)
            table_resolved_from_map[key] = "rename_flag"

    try:
        from dbwarden.engine.snapshot import (
            find_latest_snapshot,
            diff_models_against_snapshot,
            _compute_table_overlap,
            RENAME_TABLE_OVERLAP_THRESHOLD,
        )
        snapshot = find_latest_snapshot(database)
    except Exception:
        snapshot = None

    # Apply table renames to snapshot before column rename detection
    if snapshot is not None and confirmed_table_intents:
        snapshot_tables = dict(snapshot.get("tables", {}))
        for old_table, new_table in confirmed_table_intents:
            if old_table in snapshot_tables:
                snapshot_tables[new_table] = snapshot_tables.pop(old_table)
        snapshot["tables"] = snapshot_tables

    if snapshot is not None:
        model_by_name = {t.name: t for t in tables}
        snapshot_tables = snapshot.get("tables", {})
        auto_detected_renames: list[tuple[str, str, str]] = []

        # --- Table rename auto-detection ---
        model_table_names = {t.name for t in tables}
        snap_table_names = set(snapshot_tables.keys())
        dropped_tables_list = snap_table_names - model_table_names
        added_tables_list = model_table_names - snap_table_names

        table_candidates: list[tuple[str, str, float]] = []
        for dropped in dropped_tables_list:
            for added in added_tables_list:
                if (dropped, added) in confirmed_table_intents:
                    continue
                overlap = _compute_table_overlap(dropped, added, snapshot, tables)
                if overlap >= RENAME_TABLE_OVERLAP_THRESHOLD:
                    table_candidates.append((dropped, added, overlap))

        if table_candidates:
            if sys.stdin.isatty():
                prompted_tables = _prompt_table_rename_confirmations(table_candidates)
                for intent in prompted_tables:
                    key = (intent["old_table"], intent["new_table"])
                    confirmed_table_intents.add(key)
                    table_resolved_from_map[key] = "prompt"
            else:
                logger.warning(_format_table_rename_warning(table_candidates))
                console.print(
                    _format_table_rename_warning(table_candidates),
                    style="yellow",
                )

        # Apply any newly confirmed table renames to snapshot
        if confirmed_table_intents:
            snapshot_tables = dict(snapshot.get("tables", {}))
            for old_table, new_table in confirmed_table_intents:
                if old_table in snapshot_tables:
                    snapshot_tables[new_table] = snapshot_tables.pop(old_table)
            snapshot["tables"] = snapshot_tables

        # --- Column rename auto-detection ---
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
        safe_type_change=safe_type_change,
        confirmed_table_intents=confirmed_table_intents,
        table_resolved_from_map=table_resolved_from_map,
        concurrent=concurrent,
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


def _build_table_rename_ops(
    confirmed_table_intents: set[tuple[str, str]],
    table_resolved_from_map: dict[tuple[str, str], str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    upgrade: list[dict[str, Any]] = []
    rollback: list[dict[str, Any]] = []
    for old_table, new_table in confirmed_table_intents:
        origin = (table_resolved_from_map or {}).get((old_table, new_table))
        upgrade.append({
            "type": "rename_table",
            "old_table": old_table,
            "new_table": new_table,
            "resolved_from": origin,
        })
        rollback.append({
            "type": "rename_table",
            "old_table": new_table,
            "new_table": old_table,
        })
    return {"upgrade": upgrade, "rollback": rollback}


def _build_plan_operation(change: Change) -> dict[str, str]:
    operation: dict[str, str] = {
        "type": change.operation,
        "table": change.table,
        "severity": "INFO",
    }
    if change.resolved_from:
        operation["resolved_from"] = change.resolved_from
    if change.target:
        if change.operation in ("rename_column", "rename_table"):
            operation["new_name"] = change.target
        else:
            operation["column"] = change.target
    if change.operation == "rename_table":
        operation["old_table"] = change.table
    return operation


def generate_migration_sql(
    tables: list,
    migrations_dir: str | None = None,
    database: str | None = None,
    db_name: str | None = None,
    confirmed_renames: set[tuple[str, str, str]] | None = None,
    resolved_from_map: dict[tuple[str, str, str], str] | None = None,
    safe_type_change: bool = False,
    confirmed_table_intents: set[tuple[str, str]] | None = None,
    table_resolved_from_map: dict[tuple[str, str], str] | None = None,
    concurrent: bool = True,
) -> tuple[str, str, list[Change]]:
    """
    Generate upgrade and rollback SQL from table definitions.

    Compares model tables with the actual database schema to generate:
    - CREATE TABLE for new tables
    - ALTER TABLE ADD COLUMN for new columns in existing tables
    - ALTER COLUMN TYPE / SET NOT NULL / DROP DEFAULT for column-level changes

    When a schema snapshot exists, it uses the snapshot for rename detection
    and column-level change detection.
    Otherwise falls back to diffing against the live database (no column-level changes).

    Args:
        tables: List of ModelTable objects.
        migrations_dir: Path to migrations directory.
        database: Database name for backend-specific types.
        db_name: Database name for filename generation.
        confirmed_renames: Set of (table, old_name, new_name) tuples confirmed by user.
        resolved_from_map: Optional mapping from rename key to origin string.
        safe_type_change: Use multi-step safe type change strategy.
        confirmed_table_intents: Set of (old_table, new_table) tuples confirmed by user.
        table_resolved_from_map: Optional mapping from table rename key to origin string.

    Returns:
        Tuple of (upgrade_sql, rollback_sql, changes).
    """
    upgrade_sql: str = ""
    rollback_sql: str = ""
    changes: list[Change] = []
    snapshot: Any = None
    confirmed_renames = confirmed_renames or set()
    confirmed_table_intents = confirmed_table_intents or set()

    try:
        from dbwarden.engine.snapshot import (
            find_latest_snapshot,
            diff_models_against_snapshot,
            snapshot_diff_to_sql,
            _apply_rename_intents,
            _rename_table_sql,
            TableRenameIntent,
            StatementOrder,
            MigrationStatement,
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

            # Prepend table rename ops to the diff output
            table_rename_ops = _build_table_rename_ops(confirmed_table_intents, table_resolved_from_map)
            upgrade_ops = table_rename_ops["upgrade"] + upgrade_ops
            rollback_ops = table_rename_ops["rollback"] + rollback_ops

            upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(
                upgrade_ops, rollback_ops, database=database, db_name=db_name,
                safe_type_change=safe_type_change,
                concurrent=concurrent,
            )
        except Exception:
            snapshot = None

    if snapshot is None:
        table_rename_ops = _build_table_rename_ops(confirmed_table_intents, table_resolved_from_map)
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

        # Prepend table rename ops in live-DB fallback path
        if table_rename_ops["upgrade"]:
            from dbwarden.engine.snapshot import snapshot_diff_to_sql
            rename_upgrade, rename_rollback, rename_changes = snapshot_diff_to_sql(
                table_rename_ops["upgrade"], table_rename_ops["rollback"],
                database=database, db_name=db_name,
            )
            if rename_upgrade.strip():
                upgrade_sql = rename_upgrade + "\n\n" + upgrade_sql
                rollback_sql = rename_rollback + "\n\n" + rollback_sql
                changes = rename_changes + changes

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
