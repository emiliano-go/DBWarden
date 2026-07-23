from dbwarden.engine.version import get_migrations_directory
from dbwarden.exceptions import DBDisconnectedError
from dbwarden.logging import get_logger
from dbwarden.output import data_table, error, kv_table, render, section, warning
from dbwarden.repositories import (
    get_migrated_versions,
    migrations_table_exists,
)


def status_single(database: str | None = None) -> None:
    """Display migration status for a single database."""
    logger = get_logger()

    db_name = database or "default"

    try:
        migrations_dir = get_migrations_directory(database)
    except Exception:
        warning(f"Migrations directory not found for database '{db_name}'. Run 'dbwarden init' first.")
        return

    applied_versions = []
    try:
        if migrations_table_exists(database):
            applied_versions = get_migrated_versions(database)
    except DBDisconnectedError:
        warning("Database disconnected - showing migration files only, applied status unknown.")

    from dbwarden.engine.version import get_migration_filepaths_by_version

    all_migrations = get_migration_filepaths_by_version(directory=migrations_dir)
    pending_versions = [v for v in all_migrations.keys() if v not in applied_versions]

    render(
        data_table(
            f"Migration Status - {db_name}",
            ("Status", "Version", "Filename"),
            (
                (
                    "Applied" if version in applied_versions else "Pending",
                    version,
                    filepath.split("/")[-1],
                )
                for version, filepath in all_migrations.items()
            ),
        )
    )

    render(kv_table("Summary", {
        "Applied": len(applied_versions),
        "Pending": len(pending_versions),
        "Total": len(all_migrations),
    }))

    if pending_versions:
        logger.info(f"Pending migrations: {', '.join(pending_versions)}")


def status_cmd(
    database: str | None = None,
    all_databases: bool = False,
) -> None:
    """Display migration status: applied and pending migrations."""
    if all_databases:
        from dbwarden.config import get_multi_db_config

        config = get_multi_db_config()
        databases = config.databases

        for db_name in databases:
            section(db_name)
            try:
                status_single(db_name)
            except Exception as e:
                error(f"Error getting status for database '{db_name}': {e}")
    else:
        status_single(database)
