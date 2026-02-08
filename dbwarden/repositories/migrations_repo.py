from typing import Optional

from sqlalchemy import Result, Row, text

from dbwarden.database.connection import get_db_connection
from dbwarden.database.queries import SQL_QUERIES, QueryMethod
from dbwarden.models import MigrationRecord


def get_query(method: QueryMethod, **kwargs) -> str:
    """Get a SQL query by method."""
    return SQL_QUERIES.get(method, "")


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
                    f"SELECT version FROM strata_migrations WHERE version IS NOT NULL ORDER BY applied_at DESC LIMIT :limit"
                ),
                parameters={"limit": limit},
            )
            return [row.version for row in result.fetchall()]
    elif starting_version:
        with get_db_connection() as connection:
            result = connection.execute(
                text(
                    "SELECT version FROM strata_migrations WHERE version > :starting_version AND version IS NOT NULL ORDER BY applied_at ASC"
                ),
                parameters={"starting_version": starting_version},
            )
            return [row.version for row in result.fetchall()]
    else:
        return []
