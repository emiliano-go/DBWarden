import time

from dbwarden.engine.file_parser import parse_rollback_statements
from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.repositories import (
    create_lock_table_if_not_exists,
    create_migrations_table_if_not_exists,
    get_latest_versions,
    run_migration,
)


def rollback_cmd(
    count: int | None = None,
    to_version: str | None = None,
    verbose: bool = False,
) -> None:
    """
    Rollback the last applied migration.

    Args:
        count: Number of migrations to rollback.
        to_version: Rollback to a specific version.
        verbose: Enable verbose logging.
    """
    logger = get_logger(verbose=verbose)
    logger.log_execution_mode("async" if is_async_enabled() else "sync")

    if count is not None and to_version is not None:
        raise ValueError("Cannot specify both 'count' and 'to_version'.")

    migrations_dir = get_migrations_directory()

    create_migrations_table_if_not_exists()
    create_lock_table_if_not_exists()

    if count is None and to_version is None:
        count = 1

    latest_versions = get_latest_versions(limit=count, starting_version=to_version)

    if not latest_versions:
        print("Nothing to rollback.")
        return

    versions_to_rollback = _get_versions_to_rollback(
        latest_versions=latest_versions,
        migrations_dir=migrations_dir,
    )

    for version, filepath in reversed(list(versions_to_rollback.items())):
        filename = filepath.split("/")[-1]
        sql_statements = parse_rollback_statements(filepath)

        for sql in sql_statements:
            logger.log_sql_statement(sql)

        start_time = time.time()
        logger.info(f"Rolling back migration: {filename} (version: {version})")

        run_migration(
            sql_statements=sql_statements,
            version=version,
            migration_operation="rollback",
            filename=filename,
        )

        duration = time.time() - start_time
        logger.info(f"Rollback completed: {filename} in {duration:.2f}s")

    print(
        f"Rollback completed successfully: {len(versions_to_rollback)} migrations reverted."
    )


def _get_versions_to_rollback(
    latest_versions: list[str],
    migrations_dir: str,
) -> dict[str, str]:
    """Get migration file paths for versions to rollback."""
    from dbwarden.engine.version import get_migration_filepaths_by_version

    if not latest_versions:
        return {}

    filepaths = get_migration_filepaths_by_version(
        directory=migrations_dir,
        version_to_start_from=None,
        end_version=latest_versions[-1],
    )

    return dict(reversed(list(filepaths.items())))


def is_async_enabled() -> bool:
    """Check if async mode is enabled."""
    from dbwarden.database.connection import is_async_enabled

    return is_async_enabled()
