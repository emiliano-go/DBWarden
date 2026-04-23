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

```toml
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
postgres_schema = "public"
```

MySQL:

```toml
[database.legacy]
database_type = "mysql"
sqlalchemy_url = "mysql://user:password@localhost:3306/legacy"
```

SQLite:

```toml
[database.dev]
database_type = "sqlite"
sqlalchemy_url = "sqlite:///./development.db"
```

ClickHouse:

```toml
[database.analytics]
database_type = "clickhouse"
sqlalchemy_url = "clickhouse://user:password@localhost:8123/analytics"
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

```toml
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
dev_database_type = "sqlite"
dev_database_url = "sqlite:///./development.db"
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
- Use manual SQL for engine/partition/order specifics when needed

## Recommended Verification Workflow

```bash
# local loop on dev DB
dbwarden --dev migrate -d primary

# pre-release validation on production-like DB
dbwarden migrate -d primary
dbwarden status -d primary
```
