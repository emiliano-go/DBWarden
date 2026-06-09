from dbwarden.config import get_database
from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.output import console
from dbwarden.repositories import get_migration_records, migrations_table_exists


def diff_cmd(
    diff_type: str = "all", verbose: bool = False, database: str | None = None
) -> None:
    """
    Show structural differences between models and database or migrations and database.

    Args:
        diff_type: Type of diff (models, migrations, all).
        verbose: Enable verbose logging.
        database: Target database name.
    """
    config = get_database(database)
    actual_db_name = database or config.sqlalchemy_url.split("/")[-1].split("?")[0]
    logger = get_logger(
        verbose=verbose, db_name=actual_db_name, db_type=config.database_type
    )

    if not migrations_table_exists(database):
        console.print("No migrations table found. Run 'dbwarden migrate' first.", style="yellow")
        return

    console.print("Diff functionality - compares database schema with models/migrations", style="cyan")
    console.print("\nThis feature requires:", style="bold white")
    console.print("  1. SQLAlchemy model definitions", style="white")
    console.print("  2. model_paths in dbwarden config", style="white")
    console.print(
        "\nFor now, use 'dbwarden check-db' to inspect the current database schema.",
        style="white",
    )


def squash_cmd(verbose: bool = False, database: str | None = None) -> None:
    """
    Merge multiple consecutive migrations into one.

    Args:
        verbose: Enable verbose logging.
        database: Target database name.
    """
    config = get_database(database)
    actual_db_name = database or config.sqlalchemy_url.split("/")[-1].split("?")[0]
    logger = get_logger(
        verbose=verbose, db_name=actual_db_name, db_type=config.database_type
    )

    from dbwarden.repositories import get_migration_records

    if not migrations_table_exists(database):
        console.print("No migrations found. Nothing to squash.", style="yellow")
        return

    records = get_migration_records(database)
    if not records:
        console.print("No migrations applied. Nothing to squash.", style="yellow")
        return

    pending_count = _get_pending_count(database)
    if pending_count > 0:
        console.print(f"Cannot squash: {pending_count} migrations are pending.", style="yellow")
        console.print("Please run 'dbwarden migrate' first.", style="white")
        return

    logger.info("Squash functionality - merges consecutive migrations")
    console.print("This feature will combine multiple migration files into one.", style="cyan")
    console.print("Use --help for more information on advanced usage.", style="white")


def _get_pending_count(database: str | None = None) -> int:
    """Get the count of pending migrations."""
    from dbwarden.engine.version import get_migration_filepaths_by_version
    from dbwarden.repositories import get_migrated_versions

    migrations_dir = get_migrations_directory(database)
    applied = get_migrated_versions(database)
    all_migrations = get_migration_filepaths_by_version(directory=migrations_dir)
    return len([v for v in all_migrations if v not in applied])


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
