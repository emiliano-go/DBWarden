import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from dbwarden.constants import RUNS_ALWAYS_FILE_PREFIX, RUNS_ON_CHANGE_FILE_PREFIX
from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.engine.version import (
    get_migrations_directory,
    get_runs_always_filepaths,
    get_runs_on_change_filepaths,
    resolve_migration_order,
)
from dbwarden.logging import get_logger
from dbwarden.repositories import (
    create_migrations_table_if_not_exists,
    create_lock_table_if_not_exists,
    fetch_latest_versioned_migration,
    get_existing_runs_always_filenames,
    get_existing_runs_on_change_filenames_to_checksums,
    get_migrated_versions,
    run_migration,
    run_repeatable_migration,
)


def create_backup(sqlalchemy_url: str, backup_dir: str) -> str:
    """
    Create a backup of the database.

    Args:
        sqlalchemy_url: Database connection URL.
        backup_dir: Directory to store backups.

    Returns:
        str: Path to the backup file.
    """
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")

    if sqlalchemy_url.startswith("sqlite:///"):
        db_path = sqlalchemy_url.replace("sqlite:///", "")
        if db_path:
            shutil.copy2(db_path, backup_path)
        else:
            conn = sqlite3.connect(":memory:")
            conn.close()

    return backup_path


def set_baseline_migration(migrations_dir: str, version: str) -> None:
    """
    Mark all migrations up to and including the specified version as applied.

    Args:
        migrations_dir: Path to migrations directory.
        version: Version to set as baseline.
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
            )
            applied.append(v)

    return applied


def migrate_cmd(
    count: int | None = None,
    to_version: str | None = None,
    verbose: bool = False,
    baseline: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
) -> None:
    """
    Apply pending migrations to the database.

    Args:
        count: Number of migrations to apply.
        to_version: Apply migrations up to this version.
        verbose: Enable verbose logging.
        baseline: Mark migrations as applied without executing.
        with_backup: Create a backup before migrating.
        backup_dir: Directory for backup files.
    """
    logger = get_logger(verbose=verbose)
    logger.log_execution_mode("async" if is_async_enabled() else "sync")

    if count is not None and to_version is not None:
        raise ValueError("Cannot specify both 'count' and 'to_version'.")

    if count is not None and count < 1:
        raise ValueError("'count' must be a positive integer.")

    from dbwarden.config import get_config

    config = get_config()
    sqlalchemy_url = config.sqlalchemy_url

    if with_backup:
        backup_directory = backup_dir or os.path.join(os.getcwd(), "backups")
        backup_path = create_backup(sqlalchemy_url, backup_directory)
        logger.log_backup_created(backup_path)

    migrations_dir = get_migrations_directory()

    create_migrations_table_if_not_exists()
    create_lock_table_if_not_exists()

    applied_versions = set(get_migrated_versions())

    if baseline:
        if not to_version:
            raise ValueError("--baseline requires --to-version to be specified.")

        set_baseline_migration(migrations_dir, to_version)
        logger.log_baseline_set(to_version)
        print(f"Baseline set at version: {to_version}")
        return

    filepaths_by_version = _get_filepaths_by_version(
        count=count,
        to_version=to_version,
        migrations_dir=migrations_dir,
        applied_versions=applied_versions,
    )

    runs_always_filepaths = get_runs_always_filepaths(migrations_dir)
    runs_on_change_filepaths = get_runs_on_change_filepaths(
        migrations_dir, changed_only=True
    )

    if (
        not filepaths_by_version
        and not runs_always_filepaths
        and not runs_on_change_filepaths
    ):
        print("Migrations are up to date.")
        return

    if filepaths_by_version:
        logger.log_pending_migrations(list(filepaths_by_version.keys()))

    versioned_count = 0
    seed_count = 0

    for version, filepath in filepaths_by_version.items():
        filename = filepath.split("/")[-1]
        sql_statements = parse_upgrade_statements(filepath)

        for sql in sql_statements:
            logger.log_sql_statement(sql)

        start_time = time.time()
        logger.log_migration_start(version, filename)

        run_migration(
            sql_statements=sql_statements,
            version=version,
            migration_operation="upgrade",
            filename=filename,
        )

        duration = time.time() - start_time
        logger.log_migration_end(version, filename, duration)
        versioned_count += 1

    existing_runs_always = get_existing_runs_always_filenames()
    existing_runs_on_change = get_existing_runs_on_change_filenames_to_checksums()

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
            )
        else:
            run_migration(
                sql_statements=sql_statements,
                version=None,
                migration_operation="upgrade",
                filename=filename,
                migration_type="runs_always",
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
        )

        duration = time.time() - start_time
        logger.log_migration_end("ROC", filename, duration)

    total = versioned_count + seed_count
    if total > 0:
        print(f"Migrations completed successfully: {total} migrations applied.")
    else:
        print("No migrations to apply.")


def _get_filepaths_by_version(
    count: int | None = None,
    to_version: str | None = None,
    migrations_dir: str | None = None,
    applied_versions: set[str] | None = None,
) -> dict[str, str]:
    """Get pending migration file paths."""
    from dbwarden.engine.version import get_migration_filepaths_by_version

    if migrations_dir is None:
        migrations_dir = get_migrations_directory()

    filepaths = get_migration_filepaths_by_version(
        directory=migrations_dir,
    )

    if applied_versions is None:
        applied_versions = set(get_migrated_versions())

    filepaths = {v: p for v, p in filepaths.items() if v not in applied_versions}

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


def is_async_enabled() -> bool:
    """Check if async mode is enabled."""
    from dbwarden.database.connection import is_async_enabled

    return is_async_enabled()
