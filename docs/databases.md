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

PostgreSQL:

- Strong support for JSONB, UUID, rich DDL
- Prefer production runs on actual PostgreSQL instance

MySQL/MariaDB:

- Similar behavior; MariaDB configured separately via `database_type`
- Validate engine-specific syntax in manual migrations

SQLite:

- Great for local tests and dev loops
- Different type affinity and DDL limitations vs server databases

ClickHouse:

- Optimized for analytics workloads
- DBWarden can now render engine and table settings from model metadata
- Use `__table_args__` for `clickhouse_engine`, `clickhouse_order_by`, `clickhouse_primary_key`, `clickhouse_partition_by`, `clickhouse_sample_by`, and `clickhouse_ttl`
- Use column `info` for `clickhouse_type` and `clickhouse_codec` hints
- **Replicated engines**: use `clickhouse_zookeeper_path` and `clickhouse_replica_name` with `clickhouse_engine` for Replicated\* engine tables
- **Dictionaries**: use `clickhouse_dictionary=True` with `clickhouse_dict_layout`, `clickhouse_dict_source`, and `clickhouse_dict_lifetime` to define external dictionaries
- See [SQLAlchemy Models](models.md) for model examples

## Recommended Verification Workflow

```bash
# local loop on dev DB
dbwarden --dev migrate -d primary

# pre-release validation on production-like DB
dbwarden migrate -d primary
dbwarden status -d primary
```
