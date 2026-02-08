from dbwarden.commands.check_db import check_db_cmd
from dbwarden.commands.extra import diff_cmd, lock_status_cmd, squash_cmd, unlock_cmd
from dbwarden.commands.history import history_cmd
from dbwarden.commands.init import init_cmd
from dbwarden.commands.make_migrations import make_migrations_cmd, new_migration_cmd
from dbwarden.commands.migrate import migrate_cmd
from dbwarden.commands.rollback import rollback_cmd
from dbwarden.commands.status import status_cmd
from dbwarden.commands.utils import env_cmd, mode_cmd, version_cmd
from dbwarden.exceptions import DirectoryNotFoundError
from dbwarden.logging import get_logger


def handle_init() -> None:
    """Handle init command."""
    init_cmd()


def handle_make_migrations(description: str | None, verbose: bool) -> None:
    """Handle make-migrations command."""
    logger = get_logger(verbose=verbose)
    logger.log_execution_mode("async" if is_async_enabled() else "sync")
    make_migrations_cmd(description=description, verbose=verbose)


def handle_new(description: str, version: str | None) -> None:
    """Handle new command."""
    new_migration_cmd(description=description, version=version)


def handle_migrate(
    count: int | None,
    to_version: str | None,
    verbose: bool,
) -> None:
    """Handle migrate command."""
    migrate_cmd(count=count, to_version=to_version, verbose=verbose)


def handle_rollback(
    count: int | None,
    to_version: str | None,
    verbose: bool,
) -> None:
    """Handle rollback command."""
    rollback_cmd(count=count, to_version=to_version, verbose=verbose)


def handle_history() -> None:
    """Handle history command."""
    history_cmd()


def handle_status() -> None:
    """Handle status command."""
    status_cmd()


def handle_check_db(output_format: str) -> None:
    """Handle check-db command."""
    check_db_cmd(output_format=output_format)


def handle_diff(diff_type: str, verbose: bool) -> None:
    """Handle diff command."""
    diff_cmd(diff_type=diff_type, verbose=verbose)


def handle_mode() -> None:
    """Handle mode command."""
    mode_cmd()


def handle_squash(verbose: bool) -> None:
    """Handle squash command."""
    squash_cmd(verbose=verbose)


def handle_env() -> None:
    """Handle env command."""
    env_cmd()


def handle_version() -> None:
    """Handle version command."""
    version_cmd()


def handle_lock_status() -> None:
    """Handle lock-status command."""
    lock_status_cmd()


def handle_unlock() -> None:
    """Handle unlock command."""
    unlock_cmd()


def is_async_enabled() -> bool:
    """Check if async mode is enabled."""
    from dbwarden.database.connection import is_async_enabled

    return is_async_enabled()
