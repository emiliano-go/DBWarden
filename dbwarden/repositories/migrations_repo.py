from typing import Optional

from sqlalchemy import Result, Row, text

from dbwarden.database.connection import get_db_connection
from dbwarden.database.queries import QueryMethod, get_query
from dbwarden.models import MigrationRecord


def run_migration(
    sql_statements: list[str],
    version: Optional[str],
    migration_operation: str,
    filename: str,
    migration_type: str = "versioned",
) -> None:
    """Execute SQL statements and record the migration."""
    from dbwarden.engine.checksum import calculate_checksum
    from dbwarden.engine.file_parser import get_description_from_filename

    with get_db_connection() as connection:
        for statement in sql_statements:
            connection.execute(text(statement))

        if migration_operation == "upgrade":
            description = get_description_from_filename(filename)
            checksum = calculate_checksum(sql_statements)

            connection.execute(
                text(get_query(QueryMethod.INSERT_VERSION)),
                parameters={
                    "version": version,
                    "description": description,
                    "filename": filename,
                    "migration_type": migration_type,
                    "checksum": checksum,
                },
            )
        elif migration_operation == "rollback":
            connection.execute(
                text(get_query(QueryMethod.DELETE_VERSION)),
                parameters={"version": version},
            )


def fetch_latest_versioned_migration() -> Optional[MigrationRecord]:
    """Get the most recently applied versioned migration."""
    if not migrations_table_exists():
        return None

    with get_db_connection() as connection:
        result = connection.execute(text(get_query(QueryMethod.GET_LATEST_VERSION)))
        latest_migration = result.first()

    if not latest_migration:
        return None
    return MigrationRecord(
        order_executed=0,
        version=latest_migration.version,
        description=latest_migration.description,
        filename=latest_migration.filename,
        migration_type=latest_migration.migration_type,
        applied_at=latest_migration.applied_at,
        checksum=latest_migration.checksum,
    )


def create_migrations_table_if_not_exists() -> None:
    """Create the migrations table if it doesn't exist."""
    with get_db_connection() as connection:
        connection.execute(text(get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)))


def migrations_table_exists() -> bool:
    """Check if migrations table exists."""
    with get_db_connection() as connection:
        result = connection.execute(
            text(get_query(QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS))
        )
        return result.scalar_one_or_none() is not None


def get_migration_records() -> list[MigrationRecord]:
    """Get all migration records."""
    if not migrations_table_exists():
        return []

    with get_db_connection() as connection:
        results = connection.execute(text(get_query(QueryMethod.GET_ALL_MIGRATIONS)))
        return [
            MigrationRecord(
                order_executed=i,
                version=row.version,
                description=row.description,
                filename=row.filename,
                migration_type=row.migration_type,
                applied_at=row.applied_at,
                checksum=row.checksum,
            )
            for i, row in enumerate(results.fetchall())
        ]


def get_migrated_versions() -> list[str]:
    """Get all applied migration versions."""
    if not migrations_table_exists():
        return []

    with get_db_connection() as connection:
        results = connection.execute(text(get_query(QueryMethod.GET_MIGRATED_VERSIONS)))
        return [row.version for row in results.fetchall()]


def get_latest_versions(
    limit: int | None = None, starting_version: str | None = None
) -> list[str]:
    """Get recent migration versions."""
    if limit:
        with get_db_connection() as connection:
            result = connection.execute(
                text(
                    f"SELECT version FROM dbwarden_migrations WHERE version IS NOT NULL ORDER BY applied_at DESC LIMIT :limit"
                ),
                parameters={"limit": limit},
            )
            return [row.version for row in result.fetchall()]
    elif starting_version:
        with get_db_connection() as connection:
            result = connection.execute(
                text(
                    "SELECT version FROM dbwarden_migrations WHERE version > :starting_version AND version IS NOT NULL ORDER BY applied_at ASC"
                ),
                parameters={"starting_version": starting_version},
            )
            return [row.version for row in result.fetchall()]
    else:
        return []


def get_existing_runs_on_change_filenames_to_checksums() -> dict[str, str]:
    """
    Get filename to checksum mapping for runs-on-change migrations.

    Returns:
        dict[str, str]: Dictionary mapping filenames to their stored checksum values.
    """
    if not migrations_table_exists():
        return {}

    with get_db_connection() as connection:
        results = connection.execute(
            text(get_query(QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS))
        )
        return {row.filename: row.checksum for row in results.fetchall()}


def get_existing_runs_always_filenames() -> set[str]:
    """
    Get filenames of all runs-always migrations in the database.

    Returns:
        set[str]: Set of runs-always migration filenames.
    """
    if not migrations_table_exists():
        return set()

    with get_db_connection() as connection:
        results = connection.execute(
            text(get_query(QueryMethod.GET_RUNS_ALWAYS_FILENAMES))
        )
        return {row.filename for row in results.fetchall()}


def run_repeatable_migration(
    sql_statements: list[str],
    filename: str,
    migration_type: str,
) -> None:
    """
    Execute and update an existing repeatable migration record.

    Runs the SQL statements and updates the existing migration record
    with a new checksum and applied_at timestamp.

    Args:
        sql_statements: List of SQL statements to execute.
        filename: The migration filename.
        migration_type: Type of repeatable migration (runs_always or runs_on_change).
    """
    from dbwarden.engine.checksum import calculate_checksum
    from dbwarden.engine.file_parser import get_description_from_filename

    checksum = calculate_checksum(sql_statements)
    description = get_description_from_filename(filename)

    with get_db_connection() as connection:
        for statement in sql_statements:
            connection.execute(text(statement))

        connection.execute(
            text(get_query(QueryMethod.UPSERT_REPEATABLE_MIGRATION)),
            parameters={
                "description": description,
                "filename": filename,
                "migration_type": migration_type,
                "checksum": checksum,
            },
        )
