from rich.table import Table

from dbwarden.engine.version import get_migrations_directory
from dbwarden.exceptions import DBDisconnectedError
from dbwarden.logging import get_logger
from dbwarden.output import console
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
        console.print(
            f"Migrations directory not found for database '{db_name}'. Run 'dbwarden init' first.",
            style="yellow",
        )
        return

    applied_versions = []
    try:
        if migrations_table_exists(database):
            applied_versions = get_migrated_versions(database)
    except DBDisconnectedError:
        console.print(
            "Database disconnected \u2014 showing migration files only, "
            "applied status unknown.",
            style="yellow",
        )

    from dbwarden.engine.version import get_migration_filepaths_by_version

    all_migrations = get_migration_filepaths_by_version(directory=migrations_dir)
    pending_versions = [v for v in all_migrations.keys() if v not in applied_versions]

    table = Table(
        title=f"Migration Status - {db_name}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Status", style="cyan")
    table.add_column("Version", style="white")
    table.add_column("Filename", style="green")

    for version, filepath in all_migrations.items():
        filename = filepath.split("/")[-1]
        if version in applied_versions:
            status = "[green]Applied[/green]"
        else:
            status = "[yellow]Pending[/yellow]"
        table.add_row(status, version, filename)

    console.print(table)

    console.print(f"\nApplied: {len(applied_versions)}", style="green")
    console.print(f"Pending: {len(pending_versions)}", style="yellow")
    console.print(f"Total: {len(all_migrations)}", style="cyan")

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
            console.print(f"\n{'=' * 50}", style="dim")
            try:
                status_single(db_name)
            except Exception as e:
                console.print(
                    f"Error getting status for database '{db_name}': {e}",
                    style="bold red",
                )
    else:
        status_single(database)
