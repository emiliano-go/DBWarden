from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Mapping

from sqlalchemy.engine import make_url

from dbwarden.config import get_config


class QueryMethod(Enum):
    """Supported database query identifiers."""

    CREATE_MIGRATIONS_TABLE = "create_migrations_table"
    CREATE_LOCK_TABLE = "create_lock_table"
    INIT_LOCK_ROW = "init_lock_row"
    INSERT_VERSION = "insert_version"
    DELETE_VERSION = "delete_version"
    GET_ALL_MIGRATIONS = "get_all_migrations"
    GET_LATEST_VERSION = "get_latest_version"
    GET_MIGRATED_VERSIONS = "get_migrated_versions"
    CHECK_IF_MIGRATIONS_TABLE_EXISTS = "check_if_migrations_table_exists"
    CHECK_IF_VERSION_EXISTS = "check_if_version_exists"
    ACQUIRE_LOCK = "acquire_lock"
    RELEASE_LOCK = "release_lock"
    CHECK_LOCK = "check_lock"
    GET_TABLE_NAMES = "get_table_names"
    GET_TABLE_COLUMNS = "get_table_columns"
    GET_TABLE_INDEXES = "get_table_indexes"
    GET_RUNS_ON_CHANGE_CHECKSUMS = "get_runs_on_change_checksums"
    GET_RUNS_ALWAYS_FILENAMES = "get_runs_always_filenames"
    UPSERT_REPEATABLE_MIGRATION = "upsert_repeatable_migration"
    DELETE_REPEATABLE_BY_FILENAME = "delete_repeatable_by_filename"


@dataclass(frozen=True)
class DialectDefinition:
    """Encapsulates SQL templates and capabilities for a database dialect."""

    name: str
    queries: Mapping[QueryMethod, str]
    supports_repeatable_upsert: bool = True

    def get_query(self, method: QueryMethod) -> str:
        return self.queries.get(method, "")


SQLITE_QUERIES: dict[QueryMethod, str] = {
    QueryMethod.CREATE_MIGRATIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version VARCHAR(255) UNIQUE,
            description VARCHAR(500),
            filename VARCHAR(500),
            migration_type VARCHAR(50),
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(128)
        )
    """,
    QueryMethod.CREATE_LOCK_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_lock (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            locked BOOLEAN DEFAULT FALSE,
            acquired_at TIMESTAMP
        )
    """,
    QueryMethod.INIT_LOCK_ROW: """
        INSERT OR IGNORE INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, FALSE, NULL)
    """,
    QueryMethod.INSERT_VERSION: """
        INSERT INTO dbwarden_migrations (version, description, filename, migration_type, checksum)
        VALUES (:version, :description, :filename, :migration_type, :checksum)
    """,
    QueryMethod.DELETE_VERSION: """
        DELETE FROM dbwarden_migrations WHERE version = :version
    """,
    QueryMethod.GET_ALL_MIGRATIONS: """
        SELECT * FROM dbwarden_migrations ORDER BY applied_at ASC
    """,
    QueryMethod.GET_LATEST_VERSION: """
        SELECT * FROM dbwarden_migrations
        WHERE version IS NOT NULL
        ORDER BY applied_at DESC
        LIMIT 1
    """,
    QueryMethod.GET_MIGRATED_VERSIONS: """
        SELECT version FROM dbwarden_migrations WHERE version IS NOT NULL ORDER BY applied_at ASC
    """,
    QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS: """
        SELECT name FROM sqlite_master WHERE type='table' AND name='dbwarden_migrations'
    """,
    QueryMethod.CHECK_IF_VERSION_EXISTS: """
        SELECT COUNT(*) FROM dbwarden_migrations WHERE version = :version
    """,
    QueryMethod.ACQUIRE_LOCK: """
        INSERT OR REPLACE INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, TRUE, CURRENT_TIMESTAMP)
    """,
    QueryMethod.RELEASE_LOCK: """
        INSERT OR REPLACE INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, FALSE, NULL)
    """,
    QueryMethod.CHECK_LOCK: """
        SELECT locked FROM dbwarden_lock WHERE id = 1
    """,
    QueryMethod.GET_TABLE_NAMES: """
        SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name
    """,
    QueryMethod.GET_TABLE_COLUMNS: """
        PRAGMA table_info(:table_name)
    """,
    QueryMethod.GET_TABLE_INDEXES: """
        SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=:table_name
    """,
    QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS: """
        SELECT filename, checksum FROM dbwarden_migrations
        WHERE migration_type = 'runs_on_change'
    """,
    QueryMethod.GET_RUNS_ALWAYS_FILENAMES: """
        SELECT filename FROM dbwarden_migrations
        WHERE migration_type = 'runs_always'
    """,
    QueryMethod.UPSERT_REPEATABLE_MIGRATION: """
        INSERT OR REPLACE INTO dbwarden_migrations
        (version, description, filename, migration_type, checksum)
        VALUES (NULL, :description, :filename, :migration_type, :checksum)
    """,
    QueryMethod.DELETE_REPEATABLE_BY_FILENAME: """
        DELETE FROM dbwarden_migrations
        WHERE filename = :filename AND migration_type IN ('runs_always', 'runs_on_change')
    """,
}


CLICKHOUSE_QUERIES: dict[QueryMethod, str] = {
    QueryMethod.CREATE_MIGRATIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_migrations (
            version Nullable(String),
            description Nullable(String),
            filename String,
            migration_type String,
            applied_at DateTime DEFAULT now(),
            checksum Nullable(String)
        )
        ENGINE = ReplacingMergeTree()
        ORDER BY (migration_type, filename, version)
        SETTINGS allow_nullable_key = 1
    """,
    QueryMethod.CREATE_LOCK_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_lock (
            id UInt8,
            locked UInt8,
            acquired_at Nullable(DateTime)
        )
        ENGINE = ReplacingMergeTree()
        ORDER BY (id)
    """,
    QueryMethod.INIT_LOCK_ROW: """
        INSERT INTO dbwarden_lock (id, locked, acquired_at)
        SELECT 1, 0, NULL
        WHERE NOT EXISTS (
            SELECT 1 FROM dbwarden_lock WHERE id = 1
        )
    """,
    QueryMethod.INSERT_VERSION: """
        INSERT INTO dbwarden_migrations (version, description, filename, migration_type, checksum)
        VALUES (:version, :description, :filename, :migration_type, :checksum)
    """,
    QueryMethod.DELETE_VERSION: """
        ALTER TABLE dbwarden_migrations DELETE WHERE version = :version SETTINGS mutations_sync = 1
    """,
    QueryMethod.GET_ALL_MIGRATIONS: """
        SELECT version, description, filename, migration_type, applied_at, checksum
        FROM dbwarden_migrations
        ORDER BY applied_at ASC
    """,
    QueryMethod.GET_LATEST_VERSION: """
        SELECT version, description, filename, migration_type, applied_at, checksum
        FROM dbwarden_migrations
        WHERE version IS NOT NULL
        ORDER BY applied_at DESC
        LIMIT 1
    """,
    QueryMethod.GET_MIGRATED_VERSIONS: """
        SELECT version FROM dbwarden_migrations WHERE version IS NOT NULL ORDER BY applied_at ASC
    """,
    QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS: """
        SELECT name FROM system.tables
        WHERE database = currentDatabase() AND name = 'dbwarden_migrations'
        LIMIT 1
    """,
    QueryMethod.CHECK_IF_VERSION_EXISTS: """
        SELECT count() FROM dbwarden_migrations WHERE version = :version
    """,
    QueryMethod.ACQUIRE_LOCK: """
        ALTER TABLE dbwarden_lock
        UPDATE locked = 1, acquired_at = now()
        WHERE id = 1 AND (locked = 0 OR locked IS NULL)
        SETTINGS mutations_sync = 1
    """,
    QueryMethod.RELEASE_LOCK: """
        ALTER TABLE dbwarden_lock
        UPDATE locked = 0, acquired_at = NULL
        WHERE id = 1
        SETTINGS mutations_sync = 1
    """,
    QueryMethod.CHECK_LOCK: """
        SELECT locked FROM dbwarden_lock WHERE id = 1 LIMIT 1
    """,
    QueryMethod.GET_TABLE_NAMES: """
        SELECT name FROM system.tables
        WHERE database = currentDatabase() AND name NOT LIKE '.inner.%'
        ORDER BY name
    """,
    QueryMethod.GET_TABLE_COLUMNS: """
        SELECT name, type
        FROM system.columns
        WHERE database = currentDatabase() AND table = :table_name
        ORDER BY position
    """,
    QueryMethod.GET_TABLE_INDEXES: """
        SELECT name, expr
        FROM system.data_skipping_indices
        WHERE database = currentDatabase() AND table = :table_name
    """,
    QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS: """
        SELECT filename, checksum FROM dbwarden_migrations
        WHERE migration_type = 'runs_on_change'
    """,
    QueryMethod.GET_RUNS_ALWAYS_FILENAMES: """
        SELECT filename FROM dbwarden_migrations
        WHERE migration_type = 'runs_always'
    """,
    QueryMethod.UPSERT_REPEATABLE_MIGRATION: "",
    QueryMethod.DELETE_REPEATABLE_BY_FILENAME: """
        ALTER TABLE dbwarden_migrations
        DELETE WHERE filename = :filename AND migration_type IN ('runs_always', 'runs_on_change')
        SETTINGS mutations_sync = 1
    """,
}


SQLITE_DIALECT = DialectDefinition(name="sqlite", queries=SQLITE_QUERIES)
CLICKHOUSE_DIALECT = DialectDefinition(
    name="clickhouse",
    queries=CLICKHOUSE_QUERIES,
    supports_repeatable_upsert=False,
)


def _dialect_for_backend(backend: str) -> DialectDefinition:
    backend = backend.lower()
    if backend.startswith("clickhouse"):
        return CLICKHOUSE_DIALECT
    if "clickhouse" in backend:
        return CLICKHOUSE_DIALECT
    return SQLITE_DIALECT


@lru_cache(maxsize=8)
def _dialect_for_url(url: str) -> DialectDefinition:
    backend = make_url(url).get_backend_name()
    return _dialect_for_backend(backend)


def get_current_dialect() -> DialectDefinition:
    """Return the dialect definition for the active configuration."""

    config = get_config()
    database_type = getattr(config, "database_type", "")
    if database_type:
        return _dialect_for_backend(database_type)
    return _dialect_for_url(config.sqlalchemy_url)


def get_query(method: QueryMethod, **kwargs) -> str:
    """Return the SQL template for the active dialect and requested method."""

    return get_current_dialect().get_query(method)
