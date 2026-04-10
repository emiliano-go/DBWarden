from dbwarden.commands.check_db import check_db_cmd
from dbwarden.commands.database import (
    handle_database_add,
    handle_database_list,
    handle_database_remove,
)
from dbwarden.commands.extra import diff_cmd, lock_status_cmd, squash_cmd, unlock_cmd
from dbwarden.commands.history import history_cmd
from dbwarden.commands.init import init_cmd
from dbwarden.commands.make_migrations import make_migrations_cmd, new_migration_cmd
from dbwarden.commands.migrate import migrate_cmd
from dbwarden.commands.rollback import rollback_cmd
from dbwarden.commands.status import status_cmd
from dbwarden.commands.utils import config_cmd, version_cmd
from dbwarden.exceptions import DirectoryNotFoundError


def handle_init(database: str | None = None) -> None:
    """Handle init command."""
    init_cmd(database=database)


def handle_make_migrations(
    description: str | None, verbose: bool, database: str | None = None
) -> None:
    """Handle make-migrations command."""
    make_migrations_cmd(description=description, verbose=verbose, database=database)


def handle_new(
    description: str, version: str | None, database: str | None = None
) -> None:
    """Handle new command."""
    new_migration_cmd(description=description, version=version, database=database)


def handle_migrate(
    count: int | None,
    to_version: str | None,
    verbose: bool,
    database: str | None = None,
    all_databases: bool = False,
    baseline: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
) -> None:
    """Handle migrate command."""
    migrate_cmd(
        count=count,
        to_version=to_version,
        verbose=verbose,
        database=database,
        all_databases=all_databases,
        baseline=baseline,
        with_backup=with_backup,
        backup_dir=backup_dir,
    )


def handle_rollback(
    count: int | None,
    to_version: str | None,
    verbose: bool,
    database: str | None = None,
) -> None:
    """Handle rollback command."""
    rollback_cmd(count=count, to_version=to_version, verbose=verbose, database=database)


def handle_history(database: str | None = None) -> None:
    """Handle history command."""
    history_cmd(database=database)


def handle_status(database: str | None = None, all_databases: bool = False) -> None:
    """Handle status command."""
    status_cmd(database=database, all_databases=all_databases)


def handle_check_db(output_format: str, database: str | None = None) -> None:
    """Handle check-db command."""
    check_db_cmd(output_format=output_format, database=database)


def handle_diff(diff_type: str, verbose: bool, database: str | None = None) -> None:
    """Handle diff command."""
    diff_cmd(diff_type=diff_type, verbose=verbose, database=database)


def handle_squash(verbose: bool, database: str | None = None) -> None:
    """Handle squash command."""
    squash_cmd(verbose=verbose, database=database)


def handle_config() -> None:
    """Handle config command."""
    config_cmd()


def handle_version() -> None:
    """Handle version command."""
    version_cmd()


def handle_lock_status(database: str | None = None) -> None:
    """Handle lock-status command."""
    lock_status_cmd(database=database)


def handle_unlock(database: str | None = None) -> None:
    """Handle unlock command."""
    unlock_cmd(database=database)
