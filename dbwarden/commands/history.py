from dbwarden.exceptions import DBDisconnectedError
from dbwarden.logging import get_logger
from dbwarden.output import data_table, render, warning
from dbwarden.repositories import get_migration_records, migrations_table_exists


def history_cmd(database: str | None = None) -> None:
    """Display the migration history in a formatted table."""
    logger = get_logger()

    db_name = database or "default"

    try:
        table_exists = migrations_table_exists(database)
    except DBDisconnectedError:
        warning("Database disconnected - cannot retrieve migration history.")
        return

    if not table_exists:
        warning(f"No migrations have been applied to '{db_name}' yet.")
        return

    migration_records = get_migration_records(database)
    if not migration_records:
        warning(f"No migrations have been applied to '{db_name}' yet.")
        return

    render(
        data_table(
            f"Migration History - {db_name}",
            ("Version", "Order Executed", "Description", "Applied At", "Type"),
            (
                (
                    record.version or "N/A",
                    record.order_executed,
                    record.description,
                    record.applied_at,
                    record.migration_type,
                )
                for record in migration_records
            ),
        )
    )
    logger.info(f"Total migrations applied: {len(migration_records)}")
