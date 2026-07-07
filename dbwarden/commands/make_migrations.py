import os
import re
import sys
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbwarden.config import get_database, get_multi_db_config
from dbwarden.constants import RUNS_ALWAYS_FILE_PREFIX, RUNS_ON_CHANGE_FILE_PREFIX
from dbwarden.engine.checksum import calculate_checksum
from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.engine.model_discovery import (
    get_all_model_tables,
    auto_discover_model_paths,
    filter_model_tables_by_name,
    validate_model_tables_exist,
    generate_create_table_sql,
    generate_drop_object_sql,
    generate_add_column_sql,
    extract_tables_from_migrations,
    extract_tables_from_database,
    _extract_create_table_columns,
    _qualified_name,
    _quote_pg,
)
from dbwarden.engine.model_discovery import _get_backend_name as _get_backend_name_md
from dbwarden.engine.migration_name import Change, autogenerate_migration_name
from dbwarden.engine.version import (
    get_migrations_directory,
    get_next_migration_number,
    generate_migration_filename,
    generate_repeatable_filename,
)
from dbwarden import __version__
from dbwarden.engine.offline import model_state_to_dict
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


def get_model_state_path(db_name: str | None = None, legacy: bool = False) -> Path:
    base = Path(".dbwarden")
    if legacy:
        return base / "model_state.json"
    return base / f"model_state.{db_name or 'default'}.json"


def get_current_model_state_path(db_name: str | None = None) -> Path:
    state_path = get_model_state_path(db_name)
    legacy_state_path = get_model_state_path(db_name, legacy=True)
    if state_path.exists():
        if legacy_state_path.exists() and _legacy_state_should_override(db_name, state_path, legacy_state_path):
            return legacy_state_path
        return state_path
    if legacy_state_path.exists():
        return legacy_state_path
    return state_path


def _legacy_state_should_override(
    db_name: str | None,
    state_path: Path,
    legacy_state_path: Path,
) -> bool:
    try:
        legacy_state = json.loads(legacy_state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    legacy_db = legacy_state.get("database")
    if legacy_db:
        return legacy_db == (db_name or "default")

    try:
        return legacy_state_path.stat().st_mtime >= state_path.stat().st_mtime
    except OSError:
        return False


def _run_offline_migrations(
    description: str | None = None, database: str | None = None, migration_type: str = "versioned",
    clickhouse_engine_recreate: bool = False,
    drop_preserved_clickhouse_table: bool | None = None,
    rename_flags: list[str] | None = None,
    rename_table_flags: list[str] | None = None,
) -> None:
    from dbwarden.engine.offline import diff_model_states, model_state_to_dict, normalize_model_state
    from dbwarden.engine.snapshot import snapshot_diff_to_sql, _apply_rename_intents

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

    state_path = get_model_state_path(db_name)
    legacy_state_path = get_model_state_path(db_name, legacy=True)
    read_state_path = get_current_model_state_path(db_name)

    if not read_state_path.exists():
        console.print(f"Error: {get_model_state_path(db_name)} not found.", style="red")
        console.print("Run 'dbwarden export-models' first to establish a baseline.", style="yellow")
        return

    try:
        prev_state = normalize_model_state(json.loads(read_state_path.read_text()))
    except json.JSONDecodeError:
        console.print(f"Error: {read_state_path} contains invalid JSON.", style="red")
        console.print("Run 'dbwarden export-models' again to regenerate the state file.", style="yellow")
        return
    from dbwarden import __version__ as _dw_version

    # If no migration files exist yet, this is a first run.
    # Treat prev_state as empty so ALL tables get CREATE TABLE SQL,
    # not just the delta (which is empty because export-models already captured them).
    try:
        _migrations_dir = get_migrations_directory(database)
    except Exception:
        _migrations_dir = str(Path.cwd() / config.migrations_dir)
    if not list(Path(_migrations_dir).glob("*.sql")):
        prev_state["tables"] = {}
        prev_state["indexes"] = {}
        prev_state["constraints"] = {}
        prev_state["enums"] = {}

    current_tables = get_all_model_tables(model_paths, db_name=db_name)
    validate_model_tables_exist(current_tables, config.model_tables, db_name)
    current_tables = filter_model_tables_by_name(current_tables, config.model_tables)
    current_state = model_state_to_dict(current_tables, dbwarden_version=_dw_version)

    upgrade_ops, rollback_ops = diff_model_states(prev_state, current_state)

    # --- Column rename flag processing ---
    rename_intents: list[RenameIntent] = []
    if rename_flags:
        rename_intents = _parse_rename_flags(rename_flags)

    confirmed_renames: set[tuple[str, str, str]] = set()
    resolved_from_map: dict[tuple[str, str, str], str] = {}

    for intent in rename_intents:
        key = (intent.table, intent.old_name, intent.new_name)
        confirmed_renames.add(key)
        resolved_from_map[key] = "rename_flag"

    if confirmed_renames:
        upgrade_ops, rollback_ops = _apply_rename_intents(
            upgrade_ops, rollback_ops, confirmed_renames, resolved_from_map
        )

    # --- Table rename flag processing ---
    confirmed_table_intents: set[tuple[str, str]] = set()
    table_resolved_from_map: dict[tuple[str, str], str] = {}

    if rename_table_flags:
        table_intents = _parse_rename_table_flags(rename_table_flags)
        for intent in table_intents:
            key = (intent["old_table"], intent["new_table"])
            confirmed_table_intents.add(key)
            table_resolved_from_map[key] = "rename_flag"

    _check_recreate_rename_conflict(upgrade_ops, confirmed_table_intents)

    if confirmed_table_intents:
        table_rename_ops = _build_table_rename_ops(confirmed_table_intents, table_resolved_from_map)
        upgrade_ops = table_rename_ops["upgrade"] + upgrade_ops
        rollback_ops = table_rename_ops["rollback"] + rollback_ops

    _resolve_clickhouse_recreate_ops(
        upgrade_ops,
        rollback_ops,
        clickhouse_engine_recreate=clickhouse_engine_recreate,
        drop_preserved_clickhouse_table=drop_preserved_clickhouse_table,
    )

    if not upgrade_ops:
        console.print("No offline schema changes detected between model state and current models.", style="cyan")
        return

    from dbwarden.engine.version import get_migration_filepaths_by_version

    upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(
        upgrade_ops, rollback_ops, database=database, db_name=db_name,
    )

    # Prepend PostgreSQL preamble (extensions, domains, sequences)
    upgrade_sql, rollback_sql, changes = _prepend_pg_preamble(
        upgrade_sql, rollback_sql, changes, database,
    )

    if not upgrade_sql.strip():
        console.print("No offline schema changes detected between model state and current models.", style="cyan")
        return

    from dbwarden.engine.version import get_migrations_directory as _get_migrations_dir
    try:
        migrations_dir = _get_migrations_dir(database)
    except Exception:
        config = get_database(database)
        migrations_dir = str(Path.cwd() / config.migrations_dir)
        Path(migrations_dir).mkdir(parents=True, exist_ok=True)
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

    safe_desc = re.sub(r"[^a-zA-Z0-9]", "_", (description or "offline_migration")).lower()
    safe_desc = re.sub(r"_+", "_", safe_desc).strip("_")[:60]
    if not safe_desc:
        safe_desc = "offline_migration"
    if migration_type in ("runs_always", "ra"):
        filename = generate_repeatable_filename(db_name, safe_desc, RUNS_ALWAYS_FILE_PREFIX)
    elif migration_type in ("runs_on_change", "roc"):
        filename = generate_repeatable_filename(db_name, safe_desc, RUNS_ON_CHANGE_FILE_PREFIX)
    else:
        existing_versions = get_migration_filepaths_by_version(migrations_dir)
        next_version = f"{int(max(existing_versions.keys(), default='0000')) + 1:04d}"
        filename = generate_migration_filename(db_name, safe_desc, next_version)

    header = "-- upgrade\n\n"
    header += "\n\n".join(filtered_statements)
    header += "\n\n-- rollback\n\n"
    header += "\n\n".join(reversed(filtered_rollback))
    header += "\n"

    filepath = os.path.join(migrations_dir, filename)
    with open(filepath, "w") as f:
        f.write(header)

    # Write plan
    migration_id = Path(filename).stem
    plan = build_migration_plan(migration_id, changes, "\n\n".join(filtered_statements))
    plan_path = filepath.replace(".sql", ".plan.json")
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2, default=str)

    console.print(f"Created migration file: {filepath}", style="green")
    console.print(f"Created migration plan: {plan_path}", style="green")
    console.print(f"Tables included: {', '.join(sorted(set(c.table for c in changes if hasattr(c, 'table') and c.table)))}", style="cyan")

    file_state = dict(current_state)
    file_state["database"] = db_name or "default"
    state_payload = json.dumps(file_state, indent=2, default=str) + "\n"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state_payload)
    if legacy_state_path != state_path:
        legacy_state_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_state_path.write_text(state_payload)
    logger = get_logger()
    logger.info(f"Updated model state: {state_path}")


def make_migrations_cmd(
    description: str | None = None,
    verbose: bool = False,
    database: str | None = None,
    output_plan: bool = False,
    output_sql: bool = False,
    rename_flags: list[str] | None = None,
    safe_type_change: bool = False,
    rename_table_flags: list[str] | None = None,
    concurrent: bool = True,
    offline: bool = False,
    migration_type: str = "versioned",
    clickhouse_engine_recreate: bool = False,
    drop_preserved_clickhouse_table: bool | None = None,
    postgres_auto_using: bool = False,
) -> None:
    """
    Auto-generate SQL migration from SQLAlchemy models.

    Args:
        description: Description for the migration.
        verbose: Enable verbose logging.
        database: Target database name.
        output_plan: Print the migration plan JSON without writing files.
        output_sql: Print the raw migration SQL to stdout without writing files.
        rename_flags: List of user-supplied --rename flag strings.
        safe_type_change: Use multi-step safe type change strategy.
        rename_table_flags: List of user-supplied --rename-table flag strings.
        concurrent: Use CREATE INDEX CONCURRENTLY on PostgreSQL.
        offline: Use model state file instead of live database.
        migration_type: Output prefix: 'versioned' (default), 'runs_always'/'ra', or 'runs_on_change'/'roc'.
        postgres_auto_using: Emit active USING clause on PostgreSQL ALTER COLUMN TYPE.
    """
    logger = get_logger()

    if offline:
        _run_offline_migrations(
            description=description, database=database, migration_type=migration_type,
            clickhouse_engine_recreate=clickhouse_engine_recreate,
            drop_preserved_clickhouse_table=drop_preserved_clickhouse_table,
            rename_flags=rename_flags,
            rename_table_flags=rename_table_flags,
        )
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
    tables = get_all_model_tables(model_paths, db_name=db_name)
    validate_model_tables_exist(tables, config.model_tables, db_name)
    tables = filter_model_tables_by_name(tables, config.model_tables)

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
        snapshot = find_latest_snapshot(db_name)
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
        clickhouse_engine_recreate=clickhouse_engine_recreate,
        drop_preserved_clickhouse_table=drop_preserved_clickhouse_table,
        postgres_auto_using=postgres_auto_using,
    )

    safe_desc = _resolve_migration_description(description, changes)
    if migration_type in ("runs_always", "ra"):
        filename = generate_repeatable_filename(db_name, safe_desc, RUNS_ALWAYS_FILE_PREFIX)
    elif migration_type in ("runs_on_change", "roc"):
        filename = generate_repeatable_filename(db_name, safe_desc, RUNS_ON_CHANGE_FILE_PREFIX)
    else:
        filename = generate_migration_filename(db_name, safe_desc, next_number)
    plan = build_migration_plan(
        migration_id=Path(filename).stem,
        changes=changes,
        upgrade_sql=upgrade_sql,
    )

    if output_plan:
        console.print(json.dumps(plan, indent=2), markup=False, highlight=False)
        return

    if output_sql:
        console.print(upgrade_sql, markup=False, highlight=False)
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

    state = model_state_to_dict(tables, dbwarden_version=__version__)
    state_payload = json.dumps(state, indent=2, default=str) + "\n"
    state_path = get_model_state_path(db_name)
    legacy_path = get_model_state_path(db_name, legacy=True)
    if legacy_path != state_path:
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(state_payload)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state_payload)
    logger.info(f"Model state written: {state_path}")

    try:
        from dbwarden.engine.snapshot import write_snapshot
        snapshot = model_state_to_dict(tables, dbwarden_version=__version__)
        snapshot["format_version"] = 1
        write_snapshot(
            snapshot,
            database=database,
            migration_id=Path(filename).stem,
        )
    except Exception:
        logger.exception("Failed to write schema snapshot")


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

    op_types: dict[str, int] = {}
    for op in operations:
        t = op["type"]
        op_types[t] = op_types.get(t, 0) + 1

    summary = {
        "total_operations": len(operations),
        "operation_counts": op_types,
        "create_tables": op_types.get("create_table", 0),
        "drop_tables": op_types.get("drop_table", 0),
        "drop_columns": op_types.get("drop_column", 0),
    }

    return {
        "migration_id": migration_id,
        "operations": operations,
        "summary": summary,
        "required_flags": [],
        "checksum": checksum,
    }


def _resolve_clickhouse_recreate_ops(
    upgrade_ops: list[dict[str, Any]],
    rollback_ops: list[dict[str, Any]],
    clickhouse_engine_recreate: bool,
    drop_preserved_clickhouse_table: bool | None,
) -> None:
    recreate_ops = [op for op in upgrade_ops if op.get("type") == "recreate_ch_table"]
    if not recreate_ops:
        return
    if not clickhouse_engine_recreate:
        tables = ", ".join(sorted(op["table"] for op in recreate_ops))
        raise ValueError(
            f"ClickHouse engine change detected for {tables}. Rerun with --clickhouse-engine-recreate to generate a rebuild migration."
        )

    drop_old = drop_preserved_clickhouse_table
    if drop_old is None and sys.stdin.isatty():
        answer = input(
            "Drop preserved old ClickHouse table after swap? [y/N]: "
        ).strip().lower()
        drop_old = answer in ("y", "yes")
    if drop_old is None:
        drop_old = False

    for op in upgrade_ops:
        if op.get("type") == "recreate_ch_table":
            op["drop_old_after_swap"] = drop_old
    for op in rollback_ops:
        if op.get("type") == "recreate_ch_table":
            op["drop_old_after_swap"] = drop_old


def _check_recreate_rename_conflict(
    ops: list[dict[str, Any]],
    confirmed_table_intents: set[tuple[str, str]],
) -> None:
    recreate_tables = {op["table"] for op in ops if op.get("type") == "recreate_ch_table"}
    rename_old_tables = {old for old, _ in confirmed_table_intents}
    conflict = recreate_tables & rename_old_tables
    if conflict:
        names = ", ".join(sorted(conflict))
        raise ValueError(
            f"Table(s) {names} have both a rename and an engine change in the same migration. "
            "Perform the rename and engine change as separate migrations."
        )


def _check_migration_scope(upgrade_ops: list[dict[str, Any]],
                           database: str | None = None) -> list[str]:
    """Warn about unusually large or destructive migrations.

    Returns a list of warning messages. Does not block generation.
    """
    warnings: list[str] = []
    create_tables = [op for op in upgrade_ops if op["type"] == "create_table"]
    drop_tables = [op for op in upgrade_ops if op["type"] == "drop_table"]
    drop_cols = [op for op in upgrade_ops if op["type"] == "drop_column"]
    total_ops = len(upgrade_ops)

    if len(create_tables) > 5:
        warnings.append(
            f"Migration creates {len(create_tables)} tables ({create_tables[0]['table']}, ...). "
            "Large schema additions may indicate un-scoped model diffing."
        )
    if len(drop_tables) > 3:
        tables_list = ", ".join(t["table"] for t in drop_tables[:5])
        warnings.append(
            f"Migration drops {len(drop_tables)} tables ({tables_list}, ...). "
            "This may include tables that should be excluded via model_tables."
        )
    if len(drop_cols) > 3:
        cols_list = ", ".join(f"{c['table']}.{c['column']}" for c in drop_cols[:5])
        warnings.append(
            f"Migration drops {len(drop_cols)} columns ({cols_list}, ...). "
            "Dropping many columns can cause application failures."
        )
    if total_ops > 30:
        warnings.append(
            f"Migration has {total_ops} operations. Consider splitting into smaller, "
            "focused migrations."
        )
    return warnings


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


_ALTER_ADD_COLUMN_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+ADD\s+(?:COLUMN\s+)?(\S+)",
    re.IGNORECASE,
)


def _merge_pending_migrations_into_snapshot(
    snapshot: dict[str, Any],
    migrations_dir: str,
) -> None:
    from dbwarden.engine.file_parser import parse_upgrade_statements

    if not os.path.exists(migrations_dir):
        return

    tables = snapshot.setdefault("tables", {})

    for filename in sorted(os.listdir(migrations_dir)):
        if not filename.endswith(".sql"):
            continue
        filepath = os.path.join(migrations_dir, filename)
        statements = parse_upgrade_statements(filepath)

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            table_name, col_names = _extract_create_table_columns(stmt)
            if table_name and col_names and table_name not in tables:
                col_dict: dict[str, dict[str, Any]] = {}
                for col_name in col_names:
                    col_dict[col_name] = {
                        "type": "unknown",
                        "nullable": True,
                        "primary_key": False,
                    }
                tables[table_name] = {
                    "columns": col_dict,
                    "primary_key": [],
                    "comment": None,
                }
                continue

            m = _ALTER_ADD_COLUMN_RE.match(stmt)
            if m:
                tbl_name = m.group(1).strip('"`\'')
                col_name = m.group(2).strip('"`\'')
                if tbl_name in tables:
                    existing_cols = tables[tbl_name].setdefault("columns", {})
                    if col_name not in existing_cols:
                        existing_cols[col_name] = {
                            "type": "unknown",
                            "nullable": True,
                            "primary_key": False,
                        }
                else:
                    tables[tbl_name] = {
                        "columns": {
                            col_name: {
                                "type": "unknown",
                                "nullable": True,
                                "primary_key": False,
                            }
                        },
                        "primary_key": [],
                        "comment": None,
                    }


# Kept for backward compatibility — referenced by tests.
# These helper functions have been replaced by RegistryDriver handlers
# (DomainHandler, SequenceHandler) in _prepend_pg_preamble.
def _build_domain_sql(domain: dict) -> str:
    schema = domain.get("schema")
    name = domain["name"]
    qname = _qualified_name(name, schema)
    domain_type = domain.get("type", "text")
    parts = [f"CREATE DOMAIN {qname} AS {domain_type}"]
    if domain.get("default"):
        parts.append(f"DEFAULT {domain['default']}")
    if domain.get("not_null"):
        parts.append("NOT NULL")
    if domain.get("check"):
        parts.append(f"CHECK ({domain['check']})")
    return " ".join(parts) + ";"


def _build_sequence_sql(seq: dict) -> str:
    schema = seq.get("schema")
    name = seq["name"]
    qname = _qualified_name(name, schema)
    parts = [f"CREATE SEQUENCE IF NOT EXISTS {qname}"]
    if seq.get("increment") is not None:
        parts.append(f"INCREMENT BY {seq['increment']}")
    if seq.get("minvalue") is not None:
        parts.append(f"MINVALUE {seq['minvalue']}")
    if seq.get("maxvalue") is not None:
        parts.append(f"MAXVALUE {seq['maxvalue']}")
    if seq.get("start") is not None:
        parts.append(f"START WITH {seq['start']}")
    if seq.get("cycle"):
        parts.append("CYCLE")
    else:
        parts.append("NO CYCLE")
    if seq.get("owned_by"):
        parts.append(f"OWNED BY {seq['owned_by']}")
    return " ".join(parts) + ";"


def _drop_domain_sql(domain: dict) -> str:
    schema = domain.get("schema")
    name = domain["name"]
    qname = _qualified_name(name, schema)
    return f"DROP DOMAIN IF EXISTS {qname};"


def _drop_sequence_sql(seq: dict) -> str:
    schema = seq.get("schema")
    name = seq["name"]
    qname = _qualified_name(name, schema)
    return f"DROP SEQUENCE IF EXISTS {qname};"


def _prepend_pg_preamble(
    upgrade_sql: str,
    rollback_sql: str,
    changes: list[Change],
    database: str | None,
) -> tuple[str, str, list[Change]]:
    """Prepend PostgreSQL preamble SQL (extensions, domains, sequences) to upgrade/rollback SQL."""
    try:
        mc = get_multi_db_config()
        db_name = database or mc.default
        config = get_database(db_name)
        if config.database_type != "postgresql":
            return upgrade_sql, rollback_sql, changes

        if config.pg_sequences or config.pg_domains or config.pg_functions or config.pg_triggers or config.pg_roles or config.pg_default_privileges or config.pg_composite_types or config.pg_extended_statistics or config.pg_event_triggers:
            from dbwarden.engine.pg_registry import (
                CompositeTypeHandler,
                DefaultPrivilegesHandler,
                DomainHandler,
                EventTriggerHandler,
                ExtendedStatisticsHandler,
                FunctionHandler,
                RegistryDriver,
                RoleHandler,
                SequenceHandler,
                TriggerHandler,
            )
            _reg = RegistryDriver()
            _reg.register(DomainHandler())
            _reg.register(SequenceHandler())
            _reg.register(FunctionHandler())
            _reg.register(TriggerHandler())
            _reg.register(RoleHandler())
            _reg.register(DefaultPrivilegesHandler())
            _reg.register(CompositeTypeHandler())
            _reg.register(ExtendedStatisticsHandler())
            _reg.register(EventTriggerHandler())
            _up_ops, _rb_ops = _reg.run({"domains": {}, "sequences": {}, "functions": {}, "tables": {}, "roles": {}, "default_privileges": {}, "composite_types": {}, "extended_stats": {}, "event_triggers": {}}, [], config)
            if _up_ops:
                _stmts = _reg.emit_all(_up_ops, db_name=db_name)
                _pg_up = "\n".join(s.upgrade_sql for s in _stmts)
                _pg_rb = "\n".join(s.rollback_sql for s in reversed(_stmts))
                if _pg_up.strip():
                    if upgrade_sql.strip():
                        upgrade_sql = _pg_up + "\n\n" + upgrade_sql
                    else:
                        upgrade_sql = _pg_up
                if _pg_rb.strip():
                    if rollback_sql.strip():
                        rollback_sql = _pg_rb + "\n\n" + rollback_sql
                    else:
                        rollback_sql = _pg_rb
                for op in reversed(_up_ops):
                    _name = (
                        op.upgrade_attrs.get("domain_name")
                        or op.upgrade_attrs.get("seq_name")
                        or op.upgrade_attrs.get("function_name")
                        or op.upgrade_attrs.get("role_name")
                        or op.upgrade_attrs.get("type_name")
                        or ""
                    )
                    changes.insert(0, Change(operation=op.object_type, table=_name))

        if config.pg_extensions:
            ext_upgrade = "\n".join(
                f'CREATE EXTENSION IF NOT EXISTS "{ext}";'
                for ext in config.pg_extensions
            )
            ext_rollback = "\n".join(
                f'DROP EXTENSION IF EXISTS "{ext}";'
                for ext in reversed(config.pg_extensions)
            )
            if upgrade_sql.strip():
                upgrade_sql = ext_upgrade + "\n\n" + upgrade_sql
            else:
                upgrade_sql = ext_upgrade
            if rollback_sql.strip():
                rollback_sql = ext_rollback + "\n\n" + rollback_sql
            else:
                rollback_sql = ext_rollback
            for ext in config.pg_extensions:
                changes.insert(0, Change(operation="create_extension", table=ext))
    except Exception:
        pass

    return upgrade_sql, rollback_sql, changes


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
    clickhouse_engine_recreate: bool = False,
    drop_preserved_clickhouse_table: bool | None = None,
    postgres_auto_using: bool = False,
) -> tuple[str, str, list[Change]]:
    """
    Generate upgrade and rollback SQL from table definitions.

    Compares model tables with the actual database schema to generate:
    - CREATE TABLE for new tables
    - ALTER TABLE ADD COLUMN for new columns in existing tables
    - ALTER COLUMN TYPE / SET NOT NULL / DROP DEFAULT for column-level changes

    When a schema snapshot exists, it uses the snapshot for rename detection
    and column-level change detection.
    Otherwise takes a fresh snapshot from the live database and diffs against it.

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
            extract_full_schema_snapshot,
            diff_models_against_snapshot,
            snapshot_diff_to_sql,
            _apply_rename_intents,
            _rename_table_sql,
            TableRenameIntent,
            StatementOrder,
            MigrationStatement,
        )

        snapshot = find_latest_snapshot(db_name)
    except Exception:
        snapshot = None

    if snapshot is None:
        try:
            config = get_database(database)
            snapshot = extract_full_schema_snapshot(
                database=db_name,
                sqlalchemy_url=config.sqlalchemy_url,
                database_type=config.database_type,
            )
        except Exception:
            snapshot = None

    if snapshot is not None and migrations_dir:
        _merge_pending_migrations_into_snapshot(snapshot, migrations_dir)

    if snapshot is not None:
        try:
            upgrade_ops, rollback_ops = diff_models_against_snapshot(
                tables, snapshot, database=database, db_name=db_name,
                clickhouse_engine_recreate=clickhouse_engine_recreate,
            )
            if confirmed_renames:
                upgrade_ops, rollback_ops = _apply_rename_intents(
                    upgrade_ops, rollback_ops, confirmed_renames, resolved_from_map
                )

            _check_recreate_rename_conflict(upgrade_ops, confirmed_table_intents)

            # Warn about unusually large or destructive migrations
            for warn in _check_migration_scope(upgrade_ops, database=database):
                logger.warning(warn)

            # Prepend table rename ops to the diff output
            table_rename_ops = _build_table_rename_ops(confirmed_table_intents, table_resolved_from_map)
            upgrade_ops = table_rename_ops["upgrade"] + upgrade_ops
            rollback_ops = table_rename_ops["rollback"] + rollback_ops
            _resolve_clickhouse_recreate_ops(
                upgrade_ops,
                rollback_ops,
                clickhouse_engine_recreate=clickhouse_engine_recreate,
                drop_preserved_clickhouse_table=drop_preserved_clickhouse_table,
            )

            upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(
                upgrade_ops, rollback_ops, database=database, db_name=db_name,
                safe_type_change=safe_type_change,
                concurrent=concurrent,
                postgres_auto_using=postgres_auto_using,
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
        backend = _get_backend_name_md(database)

        # Emit CREATE TYPE for PG enums before any table that uses them
        enum_types: dict[str, list[str]] = {}
        for table in tables:
            for col in table.columns:
                pg_type = col.pg_meta.get("pg_type", {})
                if pg_type.get("kind") == "enum":
                    type_name = pg_type.get("type_name", "")
                    if type_name and type_name not in enum_types:
                        enum_types[type_name] = pg_type.get("values", [])
        for enum_name, values in enum_types.items():
            values_sql = ", ".join(repr(v) for v in values)
            upgrade_parts.append(f"CREATE TYPE {enum_name} AS ENUM ({values_sql});")
            rollback_parts.append(f"DROP TYPE IF EXISTS {enum_name};")
            changes.append(Change(operation="create_type", table=enum_name))

        created_tables: set[str] = set()
        for table in tables:
            existing_columns = known_tables.get(table.name, set())

            if not existing_columns:
                created_tables.add(table.name)
                create_sql = generate_create_table_sql(table, db_name)
                upgrade_parts.append(create_sql)
                rollback_parts.append(generate_drop_object_sql(table))
                changes.append(Change(operation="create_table", table=table.name))
            else:
                for column in table.columns:
                    if column.name.lower() not in existing_columns:
                        alter_sql = generate_add_column_sql(
                            table.name, column, db_name, schema=table.schema
                        )
                        upgrade_parts.append(alter_sql)
                        if backend == "postgresql":
                            qtable = _quote_pg(table.name)
                            qschema = _quote_pg(table.schema) if table.schema else None
                            col_name_q = _quote_pg(column.name)
                        else:
                            qtable = table.name
                            qschema = table.schema
                            col_name_q = column.name
                        qname = _qualified_name(qtable, qschema)
                        rollback_parts.append(
                            f"ALTER TABLE {qname} DROP COLUMN {col_name_q}"
                        )
                        changes.append(Change(operation="add_column", table=table.name, target=column.name))
                        known_tables.setdefault(table.name, set()).add(column.name.lower())

        # Emit indexes and constraints for newly created tables
        for table in tables:
            if table.name not in created_tables:
                continue
            if backend == "postgresql":
                qtable = _quote_pg(table.name)
                qschema = _quote_pg(table.schema) if table.schema else None
            else:
                qtable = table.name
                qschema = table.schema
            qname = _qualified_name(qtable, qschema)
            for idx in table.indexes:
                idx_cols = ", ".join(idx.columns)
                if backend == "clickhouse":
                    ch_type = idx.clickhouse_type or "minmax"
                    ch_granularity = idx.clickhouse_granularity or 1
                    upgrade_parts.append(
                        f"ALTER TABLE {qname} ADD INDEX IF NOT EXISTS {idx.name} "
                        f"({idx_cols}) "
                        f"TYPE {ch_type} "
                        f"GRANULARITY {ch_granularity};"
                    )
                    rollback_parts.append(
                        f"ALTER TABLE {qname} DROP INDEX {idx.name};"
                    )
                else:
                    upgrade_parts.append(f"CREATE INDEX IF NOT EXISTS {idx.name} ON {qname} ({idx_cols});")
                    rollback_parts.append(f"DROP INDEX IF EXISTS {idx.name};")
                changes.append(Change(operation="add_index", table=table.name, target=idx.name))
            for fk in table.foreign_keys:
                local_cols = ", ".join(fk.get("columns", []))
                ref_table = _quote_pg(fk.get("referred_table", "")) if backend == "postgresql" else fk.get("referred_table", "")
                ref_cols = ", ".join(_quote_pg(c) if backend == "postgresql" else c for c in fk.get("referred_columns", ["id"]))
                loc_cols_q = ", ".join(_quote_pg(c) if backend == "postgresql" else c for c in fk.get("columns", []))
                fk_sql = f"ALTER TABLE {qname} ADD FOREIGN KEY ({loc_cols_q}) REFERENCES {ref_table} ({ref_cols})"
                on_delete = fk.get("on_delete", "NO ACTION")
                on_update = fk.get("on_update", "NO ACTION")
                if on_delete != "NO ACTION":
                    fk_sql += f" ON DELETE {on_delete}"
                if on_update != "NO ACTION":
                    fk_sql += f" ON UPDATE {on_update}"
                fk_sql += ";"
                upgrade_parts.append(fk_sql)
                rollback_parts.append(f"-- DROP FOREIGN KEY ({local_cols}) on {table.name} (name unknown)")
                changes.append(Change(operation="add_foreign_key", table=table.name, target=local_cols))

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

    # Prepend PostgreSQL preamble SQL (extensions, domains, sequences).
    upgrade_sql, rollback_sql, changes = _prepend_pg_preamble(
        upgrade_sql, rollback_sql, changes, database,
    )

    return upgrade_sql, rollback_sql, changes


def new_migration_cmd(
    description: str,
    version: str | None = None,
    database: str | None = None,
    migration_type: str = "versioned",
) -> None:
    """
    Create a new manual migration file.

    Args:
        description: Description of the migration.
        version: Version number for the migration.
        database: Target database name.
        migration_type: 'versioned' (default), 'runs_always'/'ra', or 'runs_on_change'/'roc'.
    """
    logger = get_logger()

    multi_config = get_multi_db_config()
    db_name = database or multi_config.default

    migrations_dir = get_migrations_directory(database)

    safe_description = re.sub(r"[^a-zA-Z0-9]", "_", description).lower()
    safe_description = re.sub(r"_+", "_", safe_description).strip("_")
    if not safe_description:
        raise ValueError("Migration description cannot be empty or contain only special characters.")

    is_repeatable = migration_type in ("runs_always", "ra", "runs_on_change", "roc")
    if is_repeatable and version is not None:
        logger.warning("--version is ignored for repeatable migrations (RA/ROC).")

    if migration_type in ("runs_always", "ra"):
        migration_type = "runs_always"
        filename = generate_repeatable_filename(
            db_name, safe_description, RUNS_ALWAYS_FILE_PREFIX
        )
    elif migration_type in ("runs_on_change", "roc"):
        migration_type = "runs_on_change"
        filename = generate_repeatable_filename(
            db_name, safe_description, RUNS_ON_CHANGE_FILE_PREFIX
        )
    else:
        migration_type = "versioned"
        if version is None:
            version = get_next_migration_number(migrations_dir)
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

    logger.info(f"Created migration file ({migration_type}): {filename}")
    console.print(f"Created migration file: {filepath}", style="green")
