from rich.console import Console
from rich.table import Table

from dbwarden.engine.version import get_migrations_directory
from dbwarden.logging import get_logger
from dbwarden.repositories import (
    get_migrated_versions,
    migrations_table_exists,
)


def status_cmd() -> None:
    """Display migration status: applied and pending migrations."""
    logger = get_logger()
    console = Console()

    try:
        migrations_dir = get_migrations_directory()
    except Exception:
        print("migrations directory not found. Run 'dbwarden init' first.")
        return

    applied_versions = []
    if migrations_table_exists():
        applied_versions = get_migrated_versions()

    from dbwarden.engine.version import get_migration_filepaths_by_version

    all_migrations = get_migration_filepaths_by_version(directory=migrations_dir)
    pending_versions = [v for v in all_migrations.keys() if v not in applied_versions]

    table = Table(
        title="Migration Status", show_header=True, header_style="bold magenta"
    )
    table.add_column("Status", style="cyan")
    table.add_column("Version", style="white")
    table.add_column("Filename", style="green")

    for version, filepath in all_migrations.items():
        filename = filepath.split("/")[-1]
        if version in applied_versions:
            status = "[green]✓ Applied[/green]"
        else:
            status = "[yellow]Pending[/yellow]"
        table.add_row(status, version, filename)

    console.print(table)

    print(f"\nApplied: {len(applied_versions)}")
    print(f"Pending: {len(pending_versions)}")
    print(f"Total: {len(all_migrations)}")

    if pending_versions:
        logger.info(f"Pending migrations: {', '.join(pending_versions)}")
