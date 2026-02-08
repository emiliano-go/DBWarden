from rich.console import Console
from rich.table import Table

from dbwarden.logging import get_logger
from dbwarden.repositories import get_migration_records, migrations_table_exists


def history_cmd() -> None:
    """Display the migration history in a formatted table."""
    logger = get_logger()
    console = Console()

    if not migrations_table_exists():
        console.print("[yellow]No migrations have been applied yet.[/yellow]")
        return

    migration_records = get_migration_records()
    if not migration_records:
        console.print("[yellow]No migrations have been applied yet.[/yellow]")
        return

    table = Table(
        title="Migration History", show_header=True, header_style="bold magenta"
    )
    table.add_column("Version", style="cyan", no_wrap=True)
    table.add_column("Order Executed", style="green")
    table.add_column("Description", style="white")
    table.add_column("Applied At", style="green", no_wrap=True)
    table.add_column("Type", style="yellow")

    for record in migration_records:
        version = record.version or "N/A"
        table.add_row(
            version,
            str(record.order_executed),
            record.description,
            str(record.applied_at),
            record.migration_type,
        )

    console.print(table)
    logger.info(f"Total migrations applied: {len(migration_records)}")
