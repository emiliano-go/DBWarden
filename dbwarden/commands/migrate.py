import time

from dbwarden.constants import RUNS_ALWAYS_FILE_PREFIX, RUNS_ON_CHANGE_FILE_PREFIX
from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.engine.version import (
    get_migrations_directory,
    get_runs_always_filepaths,
    get_runs_on_change_filepaths,
)
from dbwarden.logging import get_logger
from dbwarden.repositories import (
    create_migrations_table_if_not_exists,
    create_lock_table_if_not_exists,
    fetch_latest_versioned_migration,
    get_existing_runs_always_filenames,
    get_existing_runs_on_change_filenames_to_checksums,
    run_migration,
    run_repeatable_migration,
)


def migrate_cmd(
    count: int | None = None,
    to_version: str | None = None,
    verbose: bool = False,
) -> None:
    """
    Apply pending migrations to the database.

    Args:
        count: Number of migrations to apply.
        to_version: Apply migrations up to this version.
        verbose: Enable verbose logging.
    """
    logger = get_logger(verbose=verbose)
    logger.log_execution_mode("async" if is_async_enabled() else "sync")

    if count is not None and to_version is not None:
        raise ValueError("Cannot specify both 'count' and 'to_version'.")

    if count is not None and count < 1:
        raise ValueError("'count' must be a positive integer.")

    migrations_dir = get_migrations_directory()

    create_migrations_table_if_not_exists()
    create_lock_table_if_not_exists()

    latest_migration = fetch_latest_versioned_migration()

    filepaths_by_version = _get_filepaths_by_version(
        latest_migration=latest_migration,
        count=count,
        to_version=to_version,
        migrations_dir=migrations_dir,
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

    print(
        f"Migrations completed successfully: {len(filepaths_by_version)} migrations applied."
    )


def _get_filepaths_by_version(
    latest_migration,
    count: int | None = None,
    to_version: str | None = None,
    migrations_dir: str | None = None,
) -> dict[str, str]:
    """Get pending migration file paths."""
    from dbwarden.engine.version import get_migration_filepaths_by_version
    from dbwarden.repositories import get_migrated_versions

    if migrations_dir is None:
        migrations_dir = get_migrations_directory()

    filepaths = get_migration_filepaths_by_version(
        directory=migrations_dir,
    )

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
