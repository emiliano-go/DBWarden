from enum import Enum


class QueryMethod(Enum):
    """Database query methods."""

    CREATE_MIGRATIONS_TABLE = "create_migrations_table"
    CREATE_LOCK_TABLE = "create_lock_table"
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


SQL_QUERIES = {
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


def get_query(method: QueryMethod, **kwargs) -> str:
    """
    Get a SQL query by method.

    Args:
        method: The query method enum value.
        **kwargs: Additional parameters for query substitution.

    Returns:
        str: The SQL query string.
    """
    return SQL_QUERIES.get(method, "")
