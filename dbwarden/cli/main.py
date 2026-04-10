import typer

from dbwarden.cli.validators import validate_directory
from dbwarden.commands import (
    handle_check_db,
    handle_config,
    handle_database_add,
    handle_database_list,
    handle_database_remove,
    handle_diff,
    handle_history,
    handle_init,
    handle_lock_status,
    handle_make_migrations,
    handle_migrate,
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

database_app = typer.Typer(help="Manage databases in warden.toml")
app.add_typer(database_app, name="database")


@app.command()
def init(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Database name to create migration directory for"
    ),
):
    """Initialize the migrations directory."""
    handle_init(database=database)


@database_app.command("list")
def database_list():
    """List all configured databases."""
    handle_database_list()


@database_app.command("add")
def database_add(
    name: str = typer.Argument(..., help="Database name"),
    url: str = typer.Option(..., "--url", "-u", help="SQLAlchemy database URL"),
    model_paths: list[str] | None = typer.Option(
        None, "--model-paths", "-m", help="Model paths"
    ),
    migrations_dir: str | None = typer.Option(
        None, "--migrations-dir", help="Migration directory"
    ),
    default: bool = typer.Option(False, "--default", help="Set as default database"),
):
    """Add a new database to the configuration."""
    handle_database_add(
        name=name,
        url=url,
        model_paths=model_paths,
        migrations_dir=migrations_dir,
        default=default,
    )


@database_app.command("remove")
def database_remove(
    name: str = typer.Argument(..., help="Database name to remove"),
    force: bool = typer.Option(
        False, "--force", help="Force removal of default database"
    ),
):
    """Remove a database from the configuration."""
    handle_database_remove(name=name, force=force)


@app.command()
def make_migrations(
    description: str = typer.Argument(None, help="Description for the migration"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Auto-generate SQL migration from SQLAlchemy models."""
    validate_directory()
    handle_make_migrations(description=description, verbose=verbose, database=database)


@app.command()
def new(
    description: str = typer.Argument(..., help="Description of the migration"),
    version: str | None = typer.Option(
        None, "--version", help="Version of the migration"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Create a new manual migration file."""
    validate_directory()
    handle_new(description=description, version=version, database=database)


@app.command()
def migrate(
    count: int | None = typer.Option(
        None, "--count", "-c", help="Number of migrations to apply"
    ),
    to_version: str | None = typer.Option(
        None, "--to-version", "-t", help="Migrate to a specific version"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Run migrations on all databases sequentially"
    ),
    baseline: bool = typer.Option(
        False, "--baseline", help="Mark migrations as applied without executing"
    ),
    with_backup: bool = typer.Option(
        False, "--with-backup", "-b", help="Create a backup before migrating"
    ),
    backup_dir: str | None = typer.Option(
        None, "--backup-dir", help="Directory for backup files"
    ),
):
    """Apply pending migrations to the database."""
    validate_directory()
    handle_migrate(
        count=count,
        to_version=to_version,
        verbose=verbose,
        database=database,
        all_databases=all_databases,
        baseline=baseline,
        with_backup=with_backup,
        backup_dir=backup_dir,
    )


@app.command()
def rollback(
    count: int | None = typer.Option(
        None, "--count", "-c", help="Number of migrations to rollback"
    ),
    to_version: str | None = typer.Option(
        None, "--to-version", "-t", help="Rollback to a specific version"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Rollback the last applied migration."""
    validate_directory()
    handle_rollback(
        count=count, to_version=to_version, verbose=verbose, database=database
    )


@app.command()
def history(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Show the full migration history."""
    validate_directory()
    handle_history(database=database)


@app.command()
def status(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
    all_databases: bool = typer.Option(
        False, "--all", "-a", help="Show status for all databases"
    ),
):
    """Show migration status (applied and pending)."""
    validate_directory()
    handle_status(database=database, all_databases=all_databases)


@app.command()
def check_db(
    output: str = typer.Option(
        "txt", "--out", "-o", help="Output format (json, yaml, sql, txt)"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Inspect the live database schema."""
    validate_directory()
    handle_check_db(output_format=output, database=database)


@app.command()
def diff(
    diff_type: str = typer.Argument(
        "all", help="Type of diff (models, migrations, all)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Show structural differences between models and database."""
    validate_directory()
    handle_diff(diff_type=diff_type, verbose=verbose, database=database)


@app.command()
def squash(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Merge multiple consecutive migrations into one."""
    validate_directory()
    handle_squash(verbose=verbose, database=database)


@app.command()
def config():
    """Display current warden.toml configuration."""
    handle_config()


@app.command()
def version():
    """Display DBWarden version and compatibility information."""
    handle_version()


@app.command()
def lock_status(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Check if migration is currently locked."""
    validate_directory()
    handle_lock_status(database=database)


@app.command()
def unlock(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Target database name"
    ),
):
    """Release the migration lock."""
    validate_directory()
    handle_unlock(database=database)


def main() -> None:
    """Main entry point for DBWarden CLI."""
    from dbwarden.database import reset_connection_logging

    reset_connection_logging()
    app()


if __name__ == "__main__":
    main()
