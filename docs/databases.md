# Supported Databases

DBWarden supports PostgreSQL, MySQL, MariaDB, SQLite, and ClickHouse.

## Backend Matrix

| Backend | `database_type` | Typical URL |
|---------|------------------|-------------|
| PostgreSQL | `postgresql` | `postgresql://user:pass@host:5432/db` |
| MySQL | `mysql` | `mysql://user:pass@host:3306/db` |
| MariaDB | `mariadb` | `mariadb://user:pass@host:3306/db` |
| SQLite | `sqlite` | `sqlite:///./app.db` |
| ClickHouse | `clickhouse` | `clickhouse://user:pass@host:8123/db` |

## Config Examples

PostgreSQL:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
)
```

MySQL:

```python
legacy = database_config(
    database_name="legacy",
    database_type="mysql",
    database_url_sync="mysql://user:password@localhost:3306/legacy",
)
```

SQLite:

```python
dev = database_config(
    database_name="dev",
    database_type="sqlite",
    database_url_sync="sqlite:///./development.db",
)
```

ClickHouse:

```python
analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="clickhouse://user:password@localhost:8123/analytics",
)
```

## Internal Connection Handling

DBWarden uses SQLAlchemy engines, with backend-specific URL normalization where needed.

Conceptual flow:

```python
def get_engine(config):
    url = config.sqlalchemy_url
    if config.database_type == "clickhouse":
        url = normalize_clickhouse_dialect(url)
    return create_engine(url)
```

For PostgreSQL schema support, DBWarden sets `search_path` on connection when `postgres_schema` is configured.

## Development Database Strategy

Recommended pattern:

- Production-like primary DB (for example PostgreSQL)
- SQLite for dev DB via `dev_database_url`
- Run local commands with `--dev`

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

```bash
dbwarden --dev make-migrations "sync models" -d primary
dbwarden --dev migrate -d primary
```

## Translation Note

When targeting SQLite in dev mode, DBWarden translates unsupported backend-specific types/defaults.

- Unknown/unsupported types fallback to `TEXT` with warnings
- `--strict-translation` turns those warnings into errors

Details: [SQL Translation](sql-translation.md)

## Backend-Specific Notes

Each backend has deep-dive documentation:

| Backend | Guide |
|---------|-------|
| PostgreSQL | [SQL Databases](databases/sql-databases.md) |
| MySQL / MariaDB | [SQL Databases](databases/sql-databases.md) |
| SQLite | [SQL Databases](databases/sql-databases.md) |
| ClickHouse | [ClickHouse](databases/clickhouse.md) |

### PostgreSQL

- Transactional DDL — entire migration file succeeds or rolls back atomically
- Column rename: uses `ALTER TABLE ... RENAME COLUMN ... TO ...`
- Index creation: uses `CREATE INDEX CONCURRENTLY` for non-blocking behavior
- Deferrable FK constraints: `DEFERRABLE INITIALLY DEFERRED`
- Best suited for production workloads with JSONB, UUID, full-text search
- Prefer production runs on actual PostgreSQL instance

### MySQL / MariaDB

- **DDL is NOT transactional** — each statement auto-commits; partial failure possible
- MariaDB configured as `database_type="mariadb"` (separate from MySQL)
- FK drop uses `DROP FOREIGN KEY` (not `DROP CONSTRAINT`)
- Column type/nullable changes use `MODIFY COLUMN` (requires full column definition)
- Validate engine-specific syntax in manual migrations

### SQLite

- Great for local tests and dev loops via `--dev` mode
- Limited DDL: no `ALTER COLUMN TYPE`, no `SET/DROP NOT NULL`, no FK alterations
- `--safe-type-change` emits a comment (not supported)
- Type affinity differs from server databases
- See [SQL Translation](sql-translation.md) for dev-mode type mapping

### ClickHouse

- HTTP-based wire protocol; DBWarden uses ClickHouse client, not SQLAlchemy session
- Several DDL operations emit comment placeholders only: table rename, column type change, nullable change, FK, indexes, safe type change
- Full engine metadata support via `__table_args__` (`clickhouse_engine`, `clickhouse_order_by`, etc.)
- Supports materialized views, projections, dictionaries, replicated engines
- See [ClickHouse Deep Dive](databases/clickhouse.md) for full details

## Recommended Verification Workflow

```bash
# local loop on dev DB
dbwarden --dev migrate -d primary

# pre-release validation on production-like DB
dbwarden migrate -d primary
dbwarden status -d primary
```
