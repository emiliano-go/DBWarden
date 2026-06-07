from __future__ import annotations

import time

from dbwarden.config import get_database
from dbwarden.engine.file_parser import parse_rollback_statements
from dbwarden.engine.version import get_migration_filepaths_by_version, get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.output import console
from dbwarden.repositories import (
    create_lock_table_if_not_exists,
    create_migrations_table_if_not_exists,
    get_migrated_versions,
    run_migration,
)


def downgrade_cmd(
    to_version: str,
    verbose: bool = False,
    database: str | None = None,
) -> None:
    config = get_database(database)
    actual_db_name = database or config.sqlalchemy_url.split("/")[-1].split("?")[0]
    logger = get_logger(
        verbose=verbose, db_name=actual_db_name, db_type=config.database_type
    )

    migrations_dir = get_migrations_directory(database)

    create_migrations_table_if_not_exists(database)
    create_lock_table_if_not_exists(database)

    applied_versions = get_migrated_versions(database)
    if not applied_versions:
        console.print("Nothing to downgrade.", style="cyan")
        return

    if to_version not in applied_versions:
        console.print(
            f"Target version {to_version} has not been applied. Cannot downgrade.",
            style="red",
        )
        return

    versions_to_revert = [v for v in applied_versions if v > to_version]
    if not versions_to_revert:
        console.print(f"Already at version {to_version}. Nothing to downgrade.", style="cyan")
        return

    filepaths = get_migration_filepaths_by_version(
        directory=migrations_dir,
        version_to_start_from=to_version,
        end_version=versions_to_revert[-1],
    )

    reverted = []
    for version in reversed(versions_to_revert):
        if version not in filepaths:
            console.print(
                f"Migration file for version {version} not found.", style="red"
            )
            continue

        filepath = filepaths[version]
        filename = filepath.split("/")[-1]
        sql_statements = parse_rollback_statements(filepath)

        if not sql_statements:
            logger.info(f"No rollback statements found for {filename}, skipping.")
            continue

        for sql in sql_statements:
            logger.log_sql_statement(sql)

        start_time = time.time()
        logger.info(f"Downgrading migration: {filename} (version: {version})")

        run_migration(
            sql_statements=sql_statements,
            version=version,
            migration_operation="rollback",
            filename=filename,
            db_name=database,
        )

        duration = time.time() - start_time
        logger.info(f"Downgrade completed: {filename} in {duration:.2f}s")
        reverted.append(version)

    if reverted:
        console.print(
            f"Downgrade completed: {len(reverted)} migration(s) reverted to version {to_version}.",
            style="green",
        )
    else:
        console.print("No migrations were downgraded.", style="yellow")
