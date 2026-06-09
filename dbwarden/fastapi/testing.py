from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator


@asynccontextmanager
async def override_database(
    database: str,
    url: str,
    *,
    run_migrations: bool = False,
    verbose: bool = False,
) -> AsyncGenerator[Any, None]:
    """Override a database URL for testing.

    Temporarily replaces the ``sqlalchemy_url_sync`` and
    ``sqlalchemy_url`` for the named database, optionally runs
    pending migrations, and restores the original config on exit.

    Usage::

        async with override_database("primary", "sqlite+aiosqlite:///:memory:",
                                     run_migrations=True):
            # Test code here uses the overridden database
            ...

    Args:
        database: Database name to override.
        url: Temporary database URL.
        run_migrations: Run pending migrations after override.
        verbose: Enable verbose migration output.
    """
    from dbwarden.config import get_database, get_multi_db_config

    config = get_database(database)
    original_sync = config.sqlalchemy_url_sync
    original_async = config.sqlalchemy_url

    config.sqlalchemy_url_sync = url
    config.sqlalchemy_url = url

    try:
        if run_migrations:
            from dbwarden.commands.migrate import migrate_cmd

            migrate_cmd(database=database, verbose=verbose)
        yield config
    finally:
        config.sqlalchemy_url_sync = original_sync
        config.sqlalchemy_url = original_async


@asynccontextmanager
async def migration_state(
    applied: list[str] | None = None,
    database: str | None = None,
) -> AsyncGenerator[None, None]:
    """Simulate a specific migration state for testing.

    Temporarily inserts or removes migration tracking records to
    simulate a given state without actually running migrations.

    Usage::

        async with migration_state(applied=["0001", "0002"]):
            # DB appears to have migrations 0001 and 0002 applied
            ...

    Args:
        applied: List of version strings to mark as applied.
        database: Target database name.
    """
    from dbwarden.config import get_database, get_multi_db_config
    from dbwarden.database.connection import get_db_connection
    from sqlalchemy import text

    db_name = database or get_multi_db_config().default
    config = get_database(database)
    table = config.migration_table or "_dbwarden_migrations"

    if applied:
        with get_db_connection(database) as conn:
            for version in applied:
                conn.execute(
                    text(
                        f"INSERT OR IGNORE INTO {table} "
                        f"(version, description, filename, migration_type, checksum, applied_at) "
                        f"VALUES (:v, :d, :f, :t, :c, datetime('now'))"
                    ),
                    {"v": version, "d": f"test_{version}", "f": f"test__{version}.sql", "t": "versioned", "c": ""},
                )
            conn.commit()

    try:
        yield
    finally:
        if applied:
            with get_db_connection(database) as conn:
                for version in applied:
                    conn.execute(
                        text(f"DELETE FROM {table} WHERE version = :v"),
                        {"v": version},
                    )
                conn.commit()
