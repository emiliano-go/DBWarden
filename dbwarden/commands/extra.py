from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.repositories import get_migration_records, migrations_table_exists


def diff_cmd(diff_type: str = "all", verbose: bool = False) -> None:
    """
    Show structural differences between models and database or migrations and database.

    Args:
        diff_type: Type of diff (models, migrations, all).
        verbose: Enable verbose logging.
    """
    logger = get_logger(verbose=verbose)

    if not migrations_table_exists():
        print("No migrations table found. Run 'dbwarden migrate' first.")
        return

    print("Diff functionality - compares database schema with models/migrations")
    print("\nThis feature requires:")
    print("  1. SQLAlchemy model definitions")
    print("  2. model_paths in warden.toml")
    print("\nFor now, use 'dbwarden check-db' to inspect the current database schema.")


def squash_cmd(verbose: bool = False) -> None:
    """
    Merge multiple consecutive migrations into one.

    Args:
        verbose: Enable verbose logging.
    """
    logger = get_logger(verbose=verbose)

    from dbwarden.repositories import get_migration_records

    if not migrations_table_exists():
        print("No migrations found. Nothing to squash.")
        return

    records = get_migration_records()
    if not records:
        print("No migrations applied. Nothing to squash.")
        return

    pending_count = _get_pending_count()
    if pending_count > 0:
        print(f"Cannot squash: {pending_count} migrations are pending.")
        print("Please run 'dbwarden migrate' first.")
        return

    logger.info("Squash functionality - merges consecutive migrations")
    print("This feature will combine multiple migration files into one.")
    print("Use --help for more information on advanced usage.")


def _get_pending_count() -> int:
    """Get the count of pending migrations."""
    from dbwarden.engine.version import get_migration_filepaths_by_version
    from dbwarden.repositories import get_migrated_versions

    migrations_dir = get_migrations_directory()
    applied = get_migrated_versions()
    all_migrations = get_migration_filepaths_by_version(directory=migrations_dir)
    return len([v for v in all_migrations if v not in applied])


def lock_status_cmd() -> None:
    """Check if migration is currently locked."""
    from dbwarden.repositories import check_lock

    is_locked = check_lock()
    if is_locked:
        print("Migration lock: ACTIVE")
        print("Another migration process may be running.")
    else:
        print("Migration lock: INACTIVE")


def unlock_cmd() -> None:
    """Release the migration lock."""
    from dbwarden.repositories import release_lock

    success = release_lock()
    if success:
        print("Migration lock released successfully.")
    else:
        print("Failed to release lock. Lock may not be held.")
