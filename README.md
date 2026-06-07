<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
    <em>Everything you loved about Django migrations, in FastAPI.</em>
</p>
<p align="center">
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/v/dbwarden?color=%2334D058&label=pypi" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/pyversions/dbwarden.svg?color=%2334D058" alt="Python versions"/></a>
  <a href="https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE"><img src="https://img.shields.io/github/license/emiliano-gandini-outeda/DBWarden?color=%2334D058" alt="License"/></a>
</p>

---

**Documentation**: [emiliano-gandini-outeda.me/DBWarden](https://emiliano-gandini-outeda.me/DBWarden/)

**Source Code**: [https://github.com/emiliano-gandini-outeda/DBWarden](https://github.com/emiliano-gandini-outeda/DBWarden)

---

DBWarden is a database toolkit for FastAPI and SQLAlchemy projects.
It handles migrations, async sessions, startup validation, health
checks, observability, and seed management: all from a single
configuration source.

> **Experimental**: DBWarden is under active development.
> Breaking changes may occur between versions.

## Key Features

- **SQL-first**: Migrations are plain SQL. What you write is exactly what
  runs against your database. No DSL, no surprises.
- **Rollback included**: Every migration carries both upgrade and rollback
  SQL. Rolling back is a first-class operation, not an afterthought.
- **Schema snapshots**: After each migration, DBWarden captures the full
  schema DDL as a checksummed JSON snapshot. These snapshots power offline
  migration generation and intelligent column rename detection.
- **Column-level diffing**: Type changes, nullable changes, and default
  value changes are all detected and generate precise ALTER COLUMN
  statements. Safe multi-step type change strategy available via
  `--safe-type-change`.
- **Richer index metadata**: Partial indexes (`WHERE`), covering indexes
  (`INCLUDE`), `USING` methods, storage parameters (`WITH`), `TABLESPACE`,
  `NULLS NOT DISTINCT`, column sort order, and ClickHouse skip indexes.
  Full-content comparison on all attributes.
- **Rename detection**: `ALTER TABLE ... RENAME COLUMN` is automatically
  detected when a column disappears from the snapshot and a new column of
  the same type appears. Table renames detected by column-overlap
  heuristic. Manual `--rename` and `--rename-table` flags for explicit
  declarations.
- **FastAPI-native**: DatabaseHandle with `.async_session` / `.sync_session`
  works directly as a route annotation — no `Depends`, no `Annotated`, no
  boilerplate. Mountable health, status, migrate, and metrics routers.
- **One config, everything**: The same `database_config(...)` call that
  defines your migrations also drives your sessions, health checks, and
  seed management. No split configs.
- **Dev mode**: Run SQLite locally against a PostgreSQL production schema.
  DBWarden translates the SQL automatically.
- **Multi-database**: Configure and migrate multiple databases from a
  single project, with full isolation and uniqueness guarantees.
- **Sandbox & dry-run**: Test migrations in a temporary database
  (`--sandbox`) or preview SQL without touching anything (`--dry-run`).
  Sandbox supports in-memory SQLite and Docker-backed ClickHouse,
  PostgreSQL, and MySQL.
- **Observability**: Prometheus metrics (6 metric families), JSON logging,
  and FastAPI routers for `/metrics`, `/status`, and `/migrate` endpoints.
  All metrics are safe no-ops without `prometheus-client` installed.
- **Versioned seeds**: SQL and Python seed files with automatic versioning,
  idempotent application, rollback support, and dedicated CLI commands.
- **ClickHouse first-class**: Table options, replicated engines, external
  dictionaries, materialized views, projections, skip indexes, and a
  dedicated safety analyzer — all from SQLAlchemy model definitions.
- **Safe by default**: Migration locking, checksum integrity, collision
  detection, and schema drift checks before you deploy.

## Requirements

- Python 3.10+
- SQLAlchemy

## Installation

```bash
pip install dbwarden
```

With FastAPI integration:

```bash
pip install "dbwarden[fastapi]"
```

With observability (Prometheus metrics):

```bash
pip install "dbwarden[metrics]"
```

With sandbox support (Docker-backed test databases):

```bash
pip install "dbwarden[sandbox]"
```

## Quickstart

### 1. Configure

Run `dbwarden init` to scaffold your config file, then edit `dbwarden.py`:

```python
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/myapp",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/myapp",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
)
```

Note the split `database_url_sync` / `database_url_async` — DBWarden now
uses separate URLs for synchronous and asynchronous connections. The
`database_config()` call returns a `DatabaseHandle` that you use directly
in your FastAPI routes.

### 2. Define your models

```python
from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)

# Rich index metadata is extracted automatically:
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    total = Column(String)
    status = Column(String)

    __table_args__ = (
        Index(
            "ix_active_orders",
            "total",
            postgresql_using="gin",
            postgresql_where="status = 'active'",
        ),
    )
```

### 3. Generate a migration

```bash
dbwarden make-migrations
```

DBWarden diffs your SQLAlchemy models against the latest schema snapshot
and auto-generates the migration name from the changes it detects:

```sql
-- upgrade
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE
);
CREATE INDEX CONCURRENTLY ix_active_orders_total
    ON orders USING gin (total)
    WHERE status = 'active';

-- rollback
DROP TABLE users;
DROP INDEX ix_active_orders_total;
```

Index parameters like `USING gin`, `WHERE status = 'active'`, and
`CONCURRENTLY` are generated automatically from your model definitions.
Migration names are auto-generated too — things like
`create_table_users` or `add_index_orders_total_gin`.

### 4. Apply

```bash
dbwarden migrate
```

After each successful migration, DBWarden writes a schema snapshot to
`dbwarden/schemas/<migration_id>.schema.json`. These snapshots make
subsequent `make-migrations` runs aware of renames, type changes,
nullable changes, and default value changes — all without querying
the live database.

### 5. Check status

```bash
dbwarden status
```

That's it. Your schema is versioned, reviewable, and reversible.

---

## FastAPI Integration

The `database_config()` call returns a `DatabaseHandle` whose
`.async_session` property works directly as a FastAPI route annotation:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from dbwarden import database_config
from dbwarden.fastapi import (
    DBWardenHealthRouter,
    DBWardenRouter,
    migration_context,
    dispose_engines,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield
    dispose_engines()


app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")
app.include_router(DBWardenRouter(), prefix="/db")

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/myapp",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/myapp",
)


@app.get("/users")
async def list_users(session=primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

That is the entire integration. No `Annotated`, no `Depends`, no
`SessionDep` type alias. Just the handle's `.async_session` in the
parameter default position. FastAPI resolves it at request time,
creates a new session, and closes it after the response.

The health router provides readiness and liveness endpoints. The
DBWardenRouter provides `GET /status` (per-database migration and
seed status) and `POST /migrate` (trigger migration with dry-run
support), both optionally guarded by X-API-Key auth.

For ClickHouse, the handle provides `.sync_session` (shared, cached
AsyncClient) instead of `.async_session`:

```python
@app.get("/events")
async def list_events(client=analytics.sync_session):
    rows = client.query("SELECT * FROM events")
    return rows.result_rows
```

The dispatcher auto-routes PostgreSQL/SQLite/MySQL/MariaDB to per-request
AsyncSession and ClickHouse to shared cached AsyncClient.

---

## Observability

Export Prometheus metrics and JSON-structured logs with zero code:

```bash
DBWARDEN_METRICS=true DBWARDEN_LOG_JSON=true dbwarden migrate
```

Mount the metrics endpoint in FastAPI:

```python
from dbwarden.fastapi import MetricsRouter, MetricsMiddleware

app.include_router(MetricsRouter())
app.add_middleware(MetricsMiddleware)
```

Six metric families are instrumented automatically:

| Metric | Type | What it tracks |
|---|---|---|
| `dbwarden_migrations_total` | Counter | Migrations applied, by database and version |
| `dbwarden_migration_duration_seconds` | Histogram | Duration per migration |
| `dbwarden_schema_version` | Gauge | Current schema version per database |
| `dbwarden_seed_version` | Gauge | Current seed version per database |
| `dbwarden_migrations_pending` | Gauge | Pending migration count |
| `dbwarden_migration_errors_total` | Counter | Migration errors by type |

---

## Sandbox & Dry-Run

Test migrations before touching production:

```bash
# Preview SQL without execution:
dbwarden migrate --dry-run

# Apply in a temporary in-memory SQLite database:
dbwarden migrate --sandbox

# Apply in a Docker-backed PostgreSQL sandbox:
dbwarden migrate --sandbox --database pg-db
```

Dry-run parses pending migrations and prints the SQL that would
execute. Sandbox starts a temporary database, applies migrations
there, reports results, and tears down — all transparent to the
migration engine.

---

## Versioned Seeds

Manage reference data through versioned SQL or Python seed files:

```bash
dbwarden seed create "Initial Countries"
# → Creates dbwarden/primary/seeds/001_initial_countries.sql

dbwarden seed apply
# → Applies all pending seeds idempotently

dbwarden seed list
# → Shows applied/pending status

dbwarden seed rollback
# → Reverses the last applied seed
```

Seeds are tracked in a `_dbwarden_seeds` table with checksums,
making them safe to reapply.

---

## Generate Models

Reverse-engineer SQLAlchemy model code from a live database:

```bash
# One file per table:
dbwarden generate-models --db primary --tables users,orders

# Single models.py with ClickHouse engine metadata:
dbwarden generate-models --db clickhouse-db --clickhouse-engines --single-file
```

---

## Multi-Database

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/main",
    model_paths=["models/primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/analytics",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/analytics",
    model_paths=["models/analytics"],
)
```

```bash
dbwarden migrate --all
```

---

## Dev Mode

Use SQLite locally while targeting PostgreSQL in production.
DBWarden translates backend-specific SQL automatically:

```bash
dbwarden --dev migrate
```

The `dev_database_type` and `dev_database_url` fields in your config
define the local target. Your migration files stay unchanged.

---

## Supported Databases

| Database   | `database_type` value |
|------------|-----------------------|
| PostgreSQL | `postgresql`          |
| MySQL      | `mysql`               |
| MariaDB    | `mariadb`             |
| SQLite     | `sqlite`              |
| ClickHouse | `clickhouse`          |

---

## License

MIT
