import json
import os
import shutil
import sqlite3
import stat
import time
from datetime import datetime
from pathlib import Path

from dbwarden.constants import RUNS_ALWAYS_FILE_PREFIX
from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.exceptions import LockError
from dbwarden.engine.version import (
    get_migrations_directory,
    get_runs_always_filepaths,
    get_runs_on_change_filepaths,
)
from dbwarden.logging import get_logger
from dbwarden.metrics import (
    increment_migration_errors,
    increment_migrations_total,
    metrics_enabled,
    observe_migration_duration,
    set_pending_migrations,
    set_schema_version,
)
from dbwarden import __version__
from dbwarden.output import console
from dbwarden.repositories import (
    create_migrations_table_if_not_exists,
    create_lock_table_if_not_exists,
    get_existing_runs_always_filenames,
    get_applied_checksums,
    get_migrated_versions,
    run_migration,
    run_repeatable_migration,
)
from dbwarden.repositories.lock_repo import acquire_lock, check_lock, release_lock
from dbwarden.engine.model_discovery import (
    get_all_model_tables,
    filter_model_tables_by_name,
    validate_model_tables_exist,
)
from dbwarden.engine.offline import model_state_to_dict


def create_backup(sqlalchemy_url: str, backup_dir: str) -> str:
    """
    Create a backup of the database.

    Args:
        sqlalchemy_url: Database connection URL.
        backup_dir: Directory to store backups.

    Returns:
        str: Path to the backup file.

    Raises:
        ValueError: If backup_dir is world-writable.
    """
    # Check backup_dir is not world-writable
    backup_dir_path = Path(backup_dir)
    try:
        mode = backup_dir_path.stat().st_mode
        if mode & stat.S_IWOTH:
            raise ValueError(
                f"Backup directory '{backup_dir}' is world-writable. "
                "Use a secure directory with restricted permissions."
            )
    except FileNotFoundError:
        # Directory doesn't exist yet - will be created with safe permissions
        pass

    os.makedirs(backup_dir, exist_ok=True)
    
    # Ensure directory has safe permissions after creation
    os.chmod(backup_dir, 0o700)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Add microseconds + short random to prevent collision
    import secrets
    import uuid
    unique = f"{timestamp}_{secrets.randbelow(1000):03d}"
    backup_path = os.path.join(backup_dir, f"backup_{unique}.db")

    # Handle collision with incrementing suffix
    base = backup_path
    counter = 1
    while os.path.exists(backup_path):
        backup_path = base.replace(".db", f"_{counter}.db")
        counter += 1
        if counter > 100:
            raise RuntimeError("Too many backup collisions")

    if sqlalchemy_url.startswith("sqlite:///"):
        db_path = sqlalchemy_url.replace("sqlite:///", "")
        if db_path:
            # Copy without preserving permissions
            shutil.copy(db_path, backup_path)
            os.chmod(backup_path, 0o644)
        else:
            conn = sqlite3.connect(":memory:")
            conn.close()

    return backup_path


def set_baseline_migration(
    migrations_dir: str, version: str, db_name: str | None = None
) -> list[str] | None:
    """
    Mark all migrations up to and including the specified version as applied.

    Args:
        migrations_dir: Path to migrations directory.
        version: Version to set as baseline.
        db_name: Database name.

    Returns:
        list[str]: List of applied versions.
    """
    from dbwarden.engine.file_parser import parse_migration_header
    from dbwarden.engine.checksum import calculate_checksum
    from dbwarden.engine.version import get_migration_filepaths_by_version

    filepaths = get_migration_filepaths_by_version(migrations_dir)

    applied = []
    for v, fp in sorted(filepaths.items()):
        if v <= version:
            statements = parse_upgrade_statements(fp)
            checksum = calculate_checksum(statements)
            filename = fp.split("/")[-1]
            description = parse_migration_header(fp).description or filename

            run_migration(
                sql_statements=statements,
                version=v,
                migration_operation="upgrade",
                filename=filename,
                db_name=db_name,
            )
            applied.append(v)

    return applied


def migrate_single(
    db_name: str | None = None,
    count: int | None = None,
    to_version: str | None = None,
    verbose: bool = False,
    baseline: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    dry_run: bool = False,
    sandbox: bool = False,
    apply_seeds: bool = False,
) -> None:
    """
    Apply pending migrations to a single database.

    Args:
        db_name: Database name.
        count: Number of migrations to apply.
        to_version: Apply migrations up to this version.
        verbose: Enable verbose logging.
        baseline: Mark migrations as applied without executing.
        with_backup: Create a backup before migrating.
        backup_dir: Directory for backup files.
        dry_run: Display pending migrations without executing them.
        sandbox: Apply migrations in a temporary sandbox database instead.
    """
    from dbwarden.config import get_database

    config = get_database(db_name)
    sqlalchemy_url = config.sqlalchemy_url
    actual_db_name = db_name or config.sqlalchemy_url.split("/")[-1].split("?")[0]

    logger = get_logger(
        verbose=verbose, db_name=actual_db_name, db_type=config.database_type
    )

    if db_name:
        console.print(f"\n=== Migrating database: {db_name} ===", style="bold cyan")

    sandbox_provider = None
    _sandbox_cm = None
    if sandbox:
        from dbwarden.engine.sandbox import create_sandbox_provider
        from dbwarden.database.connection import sandbox_override as _sandbox_ctx

        sandbox_provider = create_sandbox_provider(config.database_type)
        sandbox_url = sandbox_provider.start()
        sandbox_db_type = sandbox_provider.get_database_type()
        console.print(
            f"Sandbox started: {sandbox_provider.__class__.__name__} ({sandbox_url})",
            style="yellow",
        )
        _sandbox_cm = _sandbox_ctx(sandbox_url, sandbox_db_type)
        _sandbox_cm.__enter__()

    lock_acquired = False
    try:
        if with_backup and not sandbox:
            backup_directory = backup_dir or os.path.join(os.getcwd(), "backups")
            backup_path = create_backup(sqlalchemy_url, backup_directory)
            logger.log_backup_created(backup_path)

        migrations_dir = get_migrations_directory(db_name)

        if not dry_run:
            create_migrations_table_if_not_exists(db_name)
            create_lock_table_if_not_exists(db_name)

            if check_lock(db_name):
                raise LockError(
                    "Migration lock is already held. Another migration process may be running. "
                    "Use 'dbwarden unlock' to release the lock if necessary."
                )
            if not acquire_lock(db_name):
                raise LockError("Could not acquire migration lock.")
            lock_acquired = True

        applied_versions = set()
        applied_checksums = set()
        if not dry_run:
            applied_versions = set(get_migrated_versions(db_name))
            applied_checksums = get_applied_checksums(db_name)

        if baseline:
            if not to_version:
                raise ValueError("--baseline requires --to-version to be specified.")

            applied = set_baseline_migration(migrations_dir, to_version, db_name)
            logger.log_baseline_set(to_version)
            console.print(f"Baseline set at version: {to_version}", style="green")
            if applied:
                _write_migration_snapshot(
                    db_name=db_name,
                    migration_id=f"baseline-{applied[-1]}",
                )
            return

        filepaths_by_version = _get_filepaths_by_version(
            count=count,
            to_version=to_version,
            migrations_dir=migrations_dir,
            applied_versions=applied_versions,
            db_name=db_name,
        )

        runs_always_filepaths = get_runs_always_filepaths(migrations_dir)
        runs_on_change_filepaths = get_runs_on_change_filepaths(
            migrations_dir, changed_only=True, db_name=db_name
        )

        if (
            not filepaths_by_version
            and not runs_always_filepaths
            and not runs_on_change_filepaths
        ):
            console.print("Migrations are up to date.", style="cyan")
            return

        if filepaths_by_version:
            logger.log_pending_migrations(list(filepaths_by_version.keys()))

        if metrics_enabled() and not dry_run:
            set_pending_migrations(
                actual_db_name, len(filepaths_by_version)
            )

        if dry_run:
            console.print("[bold yellow]DRY RUN[/bold yellow] - No changes applied\n")

        versioned_count = 0
        latest_version = "0"

        from dbwarden.engine.checksum import calculate_checksum

        for version, filepath in filepaths_by_version.items():
            filename = filepath.split("/")[-1]
            sql_statements = parse_upgrade_statements(filepath)
            checksum = calculate_checksum(sql_statements)

            if checksum in applied_checksums:
                logger.log_migration_skipped(version, filename, checksum)
                continue

            for sql in sql_statements:
                logger.log_sql_statement(sql)

            if dry_run:
                console.print(
                    f"  [yellow]Would apply[/yellow] version {version}: {filename}"
                )
                for sql in sql_statements:
                    console.print(f"    {sql}")
                continue

            start_time = time.time()
            logger.log_migration_start(version, filename)

            run_migration(
                sql_statements=sql_statements,
                version=version,
                migration_operation="upgrade",
                filename=filename,
                db_name=db_name,
            )

            _write_migration_snapshot(
                db_name=db_name,
                migration_id=Path(filename).stem,
            )

            duration = time.time() - start_time
            logger.log_migration_end(version, filename, duration)
            versioned_count += 1
            applied_checksums.add(checksum)
            latest_version = version
            increment_migrations_total(actual_db_name, version, success=True)
            observe_migration_duration(actual_db_name, version, duration)

        if dry_run:
            console.print(
                f"\n[bold]Dry-run summary:[/bold] "
                f"{len(filepaths_by_version)} versioned, "
                f"{len(runs_always_filepaths)} runs-always, "
                f"{len(runs_on_change_filepaths)} runs-on-change "
                "migrations would be applied.\n"
            )
            return

        existing_runs_always = get_existing_runs_always_filenames(db_name)

        for filepath in runs_always_filepaths:
            filename = filepath.split("/")[-1]
            sql_statements = parse_upgrade_statements(filepath)

            start_time = time.time()
            logger.log_migration_start("RA", filename)

            if filename in existing_runs_always:
                run_repeatable_migration(
                    sql_statements=sql_statements,
                    filename=filename,
                    migration_type="runs_always",
                    db_name=db_name,
                )
            else:
                run_migration(
                    sql_statements=sql_statements,
                    version=None,
                    migration_operation="upgrade",
                    filename=filename,
                    migration_type="runs_always",
                    db_name=db_name,
                )

            duration = time.time() - start_time
            logger.log_migration_end("RA", filename, duration)

        for filepath in runs_on_change_filepaths:
            filename = filepath.split("/")[-1]
            sql_statements = parse_upgrade_statements(filepath)

            start_time = time.time()
            logger.log_migration_start("ROC", filename)

            run_repeatable_migration(
                sql_statements=sql_statements,
                filename=filename,
                migration_type="runs_on_change",
                db_name=db_name,
            )

            duration = time.time() - start_time
            logger.log_migration_end("ROC", filename, duration)

        # After migrations complete, auto-apply pending seeds if configured or --apply-seeds
        if config.auto_apply_seeds or apply_seeds:
            _apply_pending_seeds_after_migrate(db_name)

        if versioned_count > 0:
            console.print(
                f"Migrations completed successfully: {versioned_count} migrations applied.",
                style="green",
            )
            if metrics_enabled():
                set_schema_version(actual_db_name, latest_version)
                set_pending_migrations(actual_db_name, 0)
            _write_model_state(config=config, db_name=db_name)
        elif runs_always_filepaths or runs_on_change_filepaths:
            _write_model_state(config=config, db_name=db_name)

    except Exception:
        if metrics_enabled():
            increment_migration_errors(actual_db_name)
        raise
    finally:
        if lock_acquired:
            release_lock(db_name)
        if sandbox_provider:
            sandbox_provider.stop()
            console.print("Sandbox stopped.", style="yellow")
        if _sandbox_cm is not None:
            _sandbox_cm.__exit__(None, None, None)


def _apply_pending_seeds_after_migrate(db_name: str | None = None) -> None:
    from dbwarden.engine.seeds import get_pending_seeds, apply_single_seed
    from dbwarden.repositories.seeds_repo import (
        create_seeds_table_if_not_exists,
        get_seeds_directory,
    )
    from dbwarden.engine.code_seeds import get_pending_code_seeds, apply_code_seed

    try:
        seeds_dir = get_seeds_directory(db_name)
    except Exception:
        seeds_dir = None

    file_seeds_applied = 0
    if seeds_dir:
        create_seeds_table_if_not_exists(db_name)
        pending = get_pending_seeds(seeds_dir, db_name=db_name)
        if pending:
            console.print(f"Applying {len(pending)} pending seed(s)...", style="cyan")
            for version, (filepath, seed_type) in sorted(pending.items()):
                apply_single_seed(version, filepath, seed_type, db_name=db_name)
                file_seeds_applied += 1

    code_seeds = get_pending_code_seeds(db_name)
    if code_seeds:
        if not file_seeds_applied:
            create_seeds_table_if_not_exists(db_name)
        console.print(f"Applying {len(code_seeds)} pending code seed(s)...", style="cyan")
        for cls in code_seeds:
            apply_code_seed(cls, db_name=db_name)

    if file_seeds_applied or code_seeds:
        console.print("Seeds applied successfully.", style="green")
    else:
        console.print("Seeds are up to date.", style="cyan")


def migrate_cmd(
    count: int | None = None,
    to_version: str | None = None,
    verbose: bool = False,
    database: str | None = None,
    all_databases: bool = False,
    baseline: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    dry_run: bool = False,
    sandbox: bool = False,
    apply_seeds: bool = False,
) -> None:
    """
    Apply pending migrations to the database.

    Args:
        count: Number of migrations to apply.
        to_version: Apply migrations up to this version.
        verbose: Enable verbose logging.
        database: Database name to target.
        all_databases: Run migrations on all databases sequentially.
        baseline: Mark migrations as applied without executing.
        with_backup: Create a backup before migrating.
        backup_dir: Directory for backup files.
        dry_run: Display pending migrations without executing them.
        sandbox: Apply migrations in a temporary sandbox database instead.
        apply_seeds: Apply pending seeds after migrations (overrides config).
    """
    if count is not None and to_version is not None:
        raise ValueError("Cannot specify both 'count' and 'to-version'.")

    if count is not None and count < 1:
        raise ValueError("'count' must be a positive integer.")

    if all_databases:
        from dbwarden.config import get_multi_db_config

        config = get_multi_db_config()
        databases = config.databases

        for db_name in databases:
            try:
                migrate_single(
                    db_name=db_name,
                    count=count,
                    to_version=to_version,
                    verbose=verbose,
                    baseline=baseline,
                    with_backup=with_backup,
                    backup_dir=backup_dir,
                    dry_run=dry_run,
                    sandbox=sandbox,
                    apply_seeds=apply_seeds,
                )
            except Exception as e:
                console.print(f"Error migrating database '{db_name}': {e}", style="bold red")
                continue
    else:
        migrate_single(
            db_name=database,
            count=count,
            to_version=to_version,
            verbose=verbose,
            baseline=baseline,
            with_backup=with_backup,
            backup_dir=backup_dir,
            dry_run=dry_run,
            sandbox=sandbox,
            apply_seeds=apply_seeds,
        )


def _write_migration_snapshot(
    db_name: str | None = None,
    migration_id: str = "",
) -> None:
    from dbwarden.engine.snapshot import extract_full_schema_snapshot, write_snapshot

    try:
        snapshot = extract_full_schema_snapshot(database=db_name)
        filepath = write_snapshot(
            snapshot,
            database=db_name,
            migration_id=migration_id,
        )
        logger = get_logger(db_name=db_name)
        logger.info(f"Schema snapshot written: {filepath}")
    except Exception as exc:
        logger = get_logger(db_name=db_name)
        logger.warning(f"Failed to write schema snapshot", exc_info=True)


def _write_model_state(
    config=None,
    db_name: str | None = None,
) -> None:
    """Export current model definitions to a database-specific model state file."""
    if config is None:
        from dbwarden.config import get_database
        config = get_database(db_name)

    model_paths = config.model_paths
    if not model_paths:
        return

    try:
        tables = get_all_model_tables(model_paths, db_name=db_name)
        validate_model_tables_exist(tables, config.model_tables, db_name or "default")
        tables = filter_model_tables_by_name(tables, config.model_tables)
        state = model_state_to_dict(tables, dbwarden_version=__version__)
        from dbwarden.commands.make_migrations import get_model_state_path

        legacy_path = get_model_state_path(db_name, legacy=True)
        state_path = get_model_state_path(db_name)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        file_state = dict(state)
        file_state["database"] = db_name or "default"
        payload = json.dumps(file_state, indent=2, default=str) + "\n"
        if legacy_path != state_path:
            legacy_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_path.write_text(payload)
        state_path.write_text(payload)
        logger = get_logger(db_name=db_name)
        logger.info(f"Model state written: {state_path}")
    except Exception as exc:
        logger = get_logger(db_name=db_name)
        logger.warning(f"Failed to write model state", exc_info=True)


def _get_filepaths_by_version(
    count: int | None = None,
    to_version: str | None = None,
    migrations_dir: str | None = None,
    applied_versions: set[str] | None = None,
    db_name: str | None = None,
) -> dict[str, str]:
    """Get pending migration file paths."""
    from dbwarden.engine.version import get_migration_filepaths_by_version

    if migrations_dir is None:
        migrations_dir = get_migrations_directory(db_name)

    filepaths = get_migration_filepaths_by_version(
        directory=migrations_dir,
    )

    if count:
        filepaths = dict(list(filepaths.items())[:count])
    elif to_version:
        seen = {}
        for v, p in filepaths.items():
            seen[v] = p
            if v == to_version:
                break
        filepaths = seen

    return filepaths
