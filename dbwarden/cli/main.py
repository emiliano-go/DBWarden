import typer

from dbwarden.cli.validators import validate_directory
from dbwarden.commands import (
    handle_check_db,
    handle_diff,
    handle_env,
    handle_history,
    handle_init,
    handle_lock_status,
    handle_make_migrations,
    handle_migrate,
    handle_mode,
    handle_new,
    handle_rollback,
    handle_squash,
    handle_status,
    handle_unlock,
    handle_version,
)
from dbwarden.logging import get_logger

app = typer.Typer(
    help="""DBWarden - Professional database migration system for SQLAlchemy models

All commands support the --verbose / -v flag for detailed output.""",
    add_completion=False,
)


@app.command()
def init():
    """Initialize the migrations directory."""
    handle_init()


@app.command()
def make_migrations(
    description: str = typer.Argument(None, help="Description for the migration"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Auto-generate SQL migration from SQLAlchemy models."""
    validate_directory()
    handle_make_migrations(description=description, verbose=verbose)


@app.command()
def new(
    description: str = typer.Argument(..., help="Description of the migration"),
    version: str = typer.Option(None, "--version", help="Version of the migration"),
):
    """Create a new manual migration file."""
    validate_directory()
    handle_new(description=description, version=version)


@app.command()
def migrate(
    count: int = typer.Option(
        None, "--count", "-c", help="Number of migrations to apply"
    ),
    to_version: str = typer.Option(
        None, "--to-version", "-t", help="Migrate to a specific version"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    baseline: bool = typer.Option(
        False, "--baseline", help="Mark migrations as applied without executing"
    ),
    with_backup: bool = typer.Option(
        False, "--with-backup", "-b", help="Create a backup before migrating"
    ),
    backup_dir: str = typer.Option(
        None, "--backup-dir", help="Directory for backup files"
    ),
):
    """Apply pending migrations to the database."""
    validate_directory()
    handle_migrate(
        count=count,
        to_version=to_version,
        verbose=verbose,
        baseline=baseline,
        with_backup=with_backup,
        backup_dir=backup_dir,
    )


@app.command()
def rollback(
    count: int = typer.Option(
        None, "--count", "-c", help="Number of migrations to rollback"
    ),
    to_version: str = typer.Option(
        None, "--to-version", "-t", help="Rollback to a specific version"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Rollback the last applied migration."""
    validate_directory()
    handle_rollback(count=count, to_version=to_version, verbose=verbose)


@app.command()
def history():
    """Show the full migration history."""
    validate_directory()
    handle_history()


@app.command()
def status():
    """Show migration status (applied and pending)."""
    validate_directory()
    handle_status()


@app.command()
def check_db(
    output: str = typer.Option(
        "txt", "--out", "-o", help="Output format (json, yaml, sql, txt)"
    ),
):
    """Inspect the live database schema."""
    validate_directory()
    handle_check_db(output_format=output)


@app.command()
def diff(
    diff_type: str = typer.Argument(
        "all", help="Type of diff (models, migrations, all)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Show structural differences between models and database."""
    validate_directory()
    handle_diff(diff_type=diff_type, verbose=verbose)


@app.command()
def mode():
    """Display whether execution is sync or async."""
    handle_mode()


@app.command()
def squash(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Merge multiple consecutive migrations into one."""
    validate_directory()
    handle_squash(verbose=verbose)


@app.command()
def env():
    """Display relevant environment variables without leaking secrets."""
    handle_env()


@app.command()
def version():
    """Display DBWarden version and compatibility information."""
    handle_version()


@app.command()
def lock_status():
    """Check if migration is currently locked."""
    validate_directory()
    handle_lock_status()


@app.command()
def unlock():
    """Release the migration lock."""
    validate_directory()
    handle_unlock()


def main() -> None:
    """Main entry point for DBWarden CLI."""
    from dbwarden.database import reset_connection_logging

    reset_connection_logging()
    app()


if __name__ == "__main__":
    main()
