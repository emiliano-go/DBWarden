from enum import Enum

from sqlalchemy.engine import make_url

from dbwarden.config import get_database


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


SQLITE_QUERIES = {
    QueryMethod.CREATE_MIGRATIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_migrations (
            version VARCHAR(255),
            description VARCHAR(500),
            filename VARCHAR(500) UNIQUE,
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


POSTGRES_QUERIES = {
    QueryMethod.CREATE_MIGRATIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_migrations (
            version VARCHAR(255) UNIQUE,
            description VARCHAR(500),
            filename VARCHAR(500) UNIQUE,
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
        ON CONFLICT (version) DO UPDATE SET
            checksum = EXCLUDED.checksum,
            applied_at = CURRENT_TIMESTAMP
    """,
    QueryMethod.DELETE_VERSION: SQLITE_QUERIES[QueryMethod.DELETE_VERSION],
    QueryMethod.GET_ALL_MIGRATIONS: SQLITE_QUERIES[QueryMethod.GET_ALL_MIGRATIONS],
    QueryMethod.GET_LATEST_VERSION: SQLITE_QUERIES[QueryMethod.GET_LATEST_VERSION],
    QueryMethod.GET_MIGRATED_VERSIONS: SQLITE_QUERIES[
        QueryMethod.GET_MIGRATED_VERSIONS
    ],
    QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS: """
        SELECT tablename FROM pg_catalog.pg_tables
        WHERE schemaname = current_schema() AND tablename = 'dbwarden_migrations'
    """,
    QueryMethod.CHECK_IF_VERSION_EXISTS: SQLITE_QUERIES[
        QueryMethod.CHECK_IF_VERSION_EXISTS
    ],
    QueryMethod.ACQUIRE_LOCK: """
        INSERT INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT (id)
        DO UPDATE SET locked = EXCLUDED.locked, acquired_at = EXCLUDED.acquired_at
    """,
    QueryMethod.RELEASE_LOCK: """
        INSERT INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, FALSE, NULL)
        ON CONFLICT (id)
        DO UPDATE SET locked = EXCLUDED.locked, acquired_at = EXCLUDED.acquired_at
    """,
    QueryMethod.CHECK_LOCK: SQLITE_QUERIES[QueryMethod.CHECK_LOCK],
    QueryMethod.GET_TABLE_NAMES: """
        SELECT tablename AS name
        FROM pg_catalog.pg_tables
        WHERE schemaname = current_schema()
        ORDER BY tablename
    """,
    QueryMethod.GET_TABLE_COLUMNS: """
        SELECT column_name AS name, data_type AS type
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = :table_name
        ORDER BY ordinal_position
    """,
    QueryMethod.GET_TABLE_INDEXES: """
        SELECT indexname AS name, indexdef AS sql
        FROM pg_indexes
        WHERE schemaname = current_schema() AND tablename = :table_name
    """,
    QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS: SQLITE_QUERIES[
        QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS
    ],
    QueryMethod.GET_RUNS_ALWAYS_FILENAMES: SQLITE_QUERIES[
        QueryMethod.GET_RUNS_ALWAYS_FILENAMES
    ],
    QueryMethod.UPSERT_REPEATABLE_MIGRATION: """
        INSERT INTO dbwarden_migrations
        (version, description, filename, migration_type, checksum)
        VALUES (NULL, :description, :filename, :migration_type, :checksum)
        ON CONFLICT (filename)
        DO UPDATE SET
            description = EXCLUDED.description,
            migration_type = EXCLUDED.migration_type,
            checksum = EXCLUDED.checksum,
            applied_at = CURRENT_TIMESTAMP
    """,
    QueryMethod.DELETE_REPEATABLE_BY_FILENAME: SQLITE_QUERIES[
        QueryMethod.DELETE_REPEATABLE_BY_FILENAME
    ],
}


MYSQL_QUERIES = {
    QueryMethod.CREATE_MIGRATIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_migrations (
            version VARCHAR(255),
            description VARCHAR(500),
            filename VARCHAR(500) UNIQUE,
            migration_type VARCHAR(50),
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(128)
        )
    """,
    QueryMethod.CREATE_LOCK_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_lock (
            id INT PRIMARY KEY,
            locked BOOLEAN DEFAULT FALSE,
            acquired_at TIMESTAMP NULL
        )
    """,
    QueryMethod.INSERT_VERSION: SQLITE_QUERIES[QueryMethod.INSERT_VERSION],
    QueryMethod.DELETE_VERSION: SQLITE_QUERIES[QueryMethod.DELETE_VERSION],
    QueryMethod.GET_ALL_MIGRATIONS: SQLITE_QUERIES[QueryMethod.GET_ALL_MIGRATIONS],
    QueryMethod.GET_LATEST_VERSION: SQLITE_QUERIES[QueryMethod.GET_LATEST_VERSION],
    QueryMethod.GET_MIGRATED_VERSIONS: SQLITE_QUERIES[
        QueryMethod.GET_MIGRATED_VERSIONS
    ],
    QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS: """
        SELECT table_name AS name
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = 'dbwarden_migrations'
    """,
    QueryMethod.CHECK_IF_VERSION_EXISTS: SQLITE_QUERIES[
        QueryMethod.CHECK_IF_VERSION_EXISTS
    ],
    QueryMethod.ACQUIRE_LOCK: """
        INSERT INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, TRUE, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE
            locked = VALUES(locked),
            acquired_at = VALUES(acquired_at)
    """,
    QueryMethod.RELEASE_LOCK: """
        INSERT INTO dbwarden_lock (id, locked, acquired_at)
        VALUES (1, FALSE, NULL)
        ON DUPLICATE KEY UPDATE
            locked = VALUES(locked),
            acquired_at = VALUES(acquired_at)
    """,
    QueryMethod.CHECK_LOCK: SQLITE_QUERIES[QueryMethod.CHECK_LOCK],
    QueryMethod.GET_TABLE_NAMES: """
        SELECT table_name AS name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
        ORDER BY table_name
    """,
    QueryMethod.GET_TABLE_COLUMNS: """
        SELECT column_name AS name, column_type AS type
        FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = :table_name
        ORDER BY ordinal_position
    """,
    QueryMethod.GET_TABLE_INDEXES: """
        SELECT index_name AS name, NULL AS sql
        FROM information_schema.statistics
        WHERE table_schema = DATABASE() AND table_name = :table_name
    """,
    QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS: SQLITE_QUERIES[
        QueryMethod.GET_RUNS_ON_CHANGE_CHECKSUMS
    ],
    QueryMethod.GET_RUNS_ALWAYS_FILENAMES: SQLITE_QUERIES[
        QueryMethod.GET_RUNS_ALWAYS_FILENAMES
    ],
    QueryMethod.UPSERT_REPEATABLE_MIGRATION: """
        INSERT INTO dbwarden_migrations
        (version, description, filename, migration_type, checksum)
        VALUES (NULL, :description, :filename, :migration_type, :checksum)
        ON DUPLICATE KEY UPDATE
            description = VALUES(description),
            migration_type = VALUES(migration_type),
            checksum = VALUES(checksum),
            applied_at = CURRENT_TIMESTAMP
    """,
    QueryMethod.DELETE_REPEATABLE_BY_FILENAME: SQLITE_QUERIES[
        QueryMethod.DELETE_REPEATABLE_BY_FILENAME
    ],
}


CLICKHOUSE_QUERIES = {
    QueryMethod.CREATE_MIGRATIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_migrations (
            version String,
            description String,
            filename String,
            migration_type String,
            applied_at DateTime DEFAULT now(),
            checksum String
        ) ENGINE = MergeTree()
        ORDER BY filename
    """,
    QueryMethod.CREATE_LOCK_TABLE: """
        CREATE TABLE IF NOT EXISTS dbwarden_lock (
            id Int32,
            locked UInt8 DEFAULT 0,
            acquired_at Nullable(DateTime)
        ) ENGINE = MergeTree()
        ORDER BY id
    """,
    QueryMethod.INSERT_VERSION: """
        INSERT INTO dbwarden_migrations (version, description, filename, migration_type, checksum)
        VALUES (:version, :description, :filename, :migration_type, :checksum)
    """,
    QueryMethod.DELETE_VERSION: """
        ALTER TABLE dbwarden_migrations DELETE WHERE version = :version
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
        SELECT version FROM dbwarden_migrations
        WHERE version IS NOT NULL
        ORDER BY applied_at ASC
    """,
    QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS: """
        SELECT name FROM system.tables
        WHERE database = currentDatabase() AND name = 'dbwarden_migrations'
    """,
    QueryMethod.CHECK_IF_VERSION_EXISTS: """
        SELECT count() FROM dbwarden_migrations WHERE version = :version
    """,
    QueryMethod.ACQUIRE_LOCK: """
        ALTER TABLE dbwarden_lock UPDATE locked = 1, acquired_at = now() WHERE id = 1
    """,
    QueryMethod.RELEASE_LOCK: """
        ALTER TABLE dbwarden_lock UPDATE locked = 0, acquired_at = NULL WHERE id = 1
    """,
    QueryMethod.CHECK_LOCK: """
        SELECT locked FROM dbwarden_lock WHERE id = 1
    """,
    QueryMethod.GET_TABLE_NAMES: """
        SELECT name FROM system.tables
        WHERE database = currentDatabase()
        ORDER BY name
    """,
    QueryMethod.GET_TABLE_COLUMNS: """
        SELECT name, type, is_nullable, default_expression
        FROM system.columns
        WHERE database = currentDatabase() AND table = :table_name
    """,
    QueryMethod.GET_TABLE_INDEXES: """
        SELECT name, expression FROM system.data_skipping_indices
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
    QueryMethod.UPSERT_REPEATABLE_MIGRATION: """
        INSERT INTO dbwarden_migrations (version, description, filename, migration_type, checksum)
        VALUES (NULL, :description, :filename, :migration_type, :checksum)
    """,
    QueryMethod.DELETE_REPEATABLE_BY_FILENAME: """
        ALTER TABLE dbwarden_migrations DELETE WHERE filename = :filename AND migration_type IN ('runs_always', 'runs_on_change')
    """,
}


def _get_backend_name(db_name: str | None = None) -> str:
    try:
        config = get_database(db_name)
        return config.database_type
    except Exception:
        return "sqlite"


def _get_queries_for_backend(db_name: str | None = None) -> dict:
    backend = _get_backend_name(db_name)
    if backend == "postgresql":
        return POSTGRES_QUERIES
    if backend in ("mysql", "mariadb"):
        return MYSQL_QUERIES
    if backend == "clickhouse":
        return CLICKHOUSE_QUERIES
    return SQLITE_QUERIES


def get_query(method: QueryMethod, db_name: str | None = None, **kwargs) -> str:
    """Get a SQL query by method for current backend."""

    return _get_queries_for_backend(db_name).get(method, "")
