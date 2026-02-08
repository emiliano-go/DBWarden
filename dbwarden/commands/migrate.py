import time

from dbwarden.engine.file_parser import parse_upgrade_statements
from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.repositories import (
    create_migrations_table_if_not_exists,
    create_lock_table_if_not_exists,
    fetch_latest_versioned_migration,
    run_migration,
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

    if not filepaths_by_version:
        print("Migrations are up to date.")
        return

    logger.log_pending_migrations(list(filepaths_by_version.keys()))

    for version, filepath in filepaths_by_version.items():
        filename = filename = filepath.split("/")[-1]
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

    if migrations_dir is None:
        migrations_dir = get_migrations_directory()

    filepaths = get_migration_filepaths_by_version(
        directory=migrations_dir,
        version_to_start_from=latest_migration.version if latest_migration else None,
    )

    if latest_migration:
        versions = list(filepaths.keys())
        if versions and versions[0] == latest_migration.version:
            filepaths = dict(list(filepaths.items())[1:])

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
