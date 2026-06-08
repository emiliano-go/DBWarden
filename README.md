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
- **PostgreSQL first-class**: Identity columns, collation, storage, compression, generated columns, fillfactor, tablespace, unlogged tables, partitioning, inheritance, exclude constraints, deferred constraints, check constraints with `NO INHERIT`, index options (`USING`, `WHERE`, `INCLUDE`, `NULLS NOT DISTINCT`, column sorting), enum types, and full type normalization. Reverse-engineer with `generate-models`, feed back into `make-migrations`; **zero diff** verified.
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

### Lifespan (Engine Lifecycle)

DBWarden provides a single context manager — `dbwarden_lifespan` —
that handles both startup validation and shutdown teardown:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dbwarden_lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)
```

During **startup**, `dbwarden_lifespan` optionally runs schema validation
(`mode="check"`) or applies pending migrations (`mode="migrate"`). During
**shutdown**, it disposes every cached SQLAlchemy engine pool and drops
all ClickHouse client references — regardless of whether the startup
phase succeeded or failed.

Three modes are available:

- `mode="check"` (default) — read-only schema integrity check. Raises
  on drift unless `fail_fast=False`. Safe for production.
- `mode="migrate"` — auto-apply pending migrations on boot. Blocked in
  production unless `allow_in_production=True`.
- `mode="none"` — skip all startup logic; engine pools are still disposed
  on shutdown. Useful when you handle migrations out of band.

Under the hood, `dbwarden_lifespan` wraps `migration_context` for the
startup phase and calls `dispose_engines()` in its `finally` block.
`dispose_engines()` calls `.dispose()` on every SyncEngine and
AsyncEngine's underlying sync engine, clearing all four internal caches
(async session factories, sync session factories, ClickHouse async
clients, ClickHouse sync clients). After disposal, the next factory
request creates a fresh engine automatically — there is no permanent
registry of engines, only a URL-keyed cache.

### Per-Request Sessions (Route Dependencies)

The `database_config()` call returns a `DatabaseHandle`. Its
`.async_session` and `.sync_session` properties produce FastAPI
dependency annotations that inject a session per request:

```python
from dbwarden import database_config
from dbwarden.fastapi import DBWardenHealthRouter, DBWardenRouter

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

No `Annotated`, no `Depends`, no `SessionDep` type alias. FastAPI sees
the annotation at import time, resolves the dependency at request time,
creates a new session, and closes it after the response. The underlying
engine is not per-request — it is created once (lazily, on first
request) and cached in the URL-keyed factory dict. The lifespan owns
engine disposal; the route owns session lifetime.

**Transaction boundaries:** `handle.async_session` does **not**
auto-commit. You own the commit:
- Call `await session.commit()` explicitly after writes.
- On unhandled exception, the async context manager calls
  `await session.rollback()` automatically.
- `expire_on_commit=False` is set, so loaded objects survive
  across commit boundaries without re-querying.

For ClickHouse, the handle provides `.sync_session` which returns
a shared, cached `AsyncClient` rather than a per-request session:

```python
@app.get("/events")
async def list_events(client=analytics.sync_session):
    rows = client.query("SELECT * FROM events")
    return rows.result_rows
```

The dispatcher auto-routes PostgreSQL / SQLite / MySQL / MariaDB to
per-request `AsyncSession` and ClickHouse to a shared cached client.

### Routers

The health router provides readiness and liveness endpoints. The
DBWardenRouter provides `GET /status` (per-database migration and
seed status) and `POST /migrate` (trigger migration with dry-run
support), both optionally guarded by X-API-Key auth.

```python
app.include_router(DBWardenHealthRouter(), prefix="/health")
app.include_router(DBWardenRouter(), prefix="/db")
```

---

## Connection Lifecycle

Understanding how DBWarden creates, caches, and disposes database
connections is essential for production deployments.

### Scope

Resources live at three distinct scopes:

| Scope | Resource | Lifetime |
|---|---|---|
| **Application** | Engine pool, ClickHouse client | Created lazily on first use. Disposed by `dispose_engines()` during app shutdown. |
| **Request** | `AsyncSession` / `Session` | Created per request by FastAPI's dependency injection. Closed (and rolled back on error) at end of request. |
| **Configuration** | `DatabaseEntry` in registry | Lives for the lifetime of the Python process. `reset_registry()` clears it (used in testing). |

### How engines are cached

DBWarden maintains **two independent engine caches**, one for the
FastAPI layer and one for the CLI layer.

**FastAPI cache** (`fastapi/engines.py`): Four module-level dicts keyed
by URL (sanitized of passwords for the cache key):

- `_ASYNC_SESSION_FACTORIES` — maps cache key to `async_sessionmaker`
- `_SYNC_SESSION_FACTORIES` — maps URL to `sessionmaker`
- `_CLICKHOUSE_ASYNC_CLIENTS` — maps database name to `AsyncClient`
- `_CLICKHOUSE_SYNC_CLIENTS` — maps database name to sync `Client`

All four are thread-safe (guarded by `threading.Lock`). Engines are
created lazily on the first `_async_session_factory()` or
`_sync_session_factory()` call and cached indefinitely until
`dispose_engines()` is called.

**CLI cache** (`database/connection.py`): A single `_engine_cache` dict
mapping `(url, db_type)` to `Engine`. This cache is used by CLI commands
(migrate, seed, make-migrations, etc.). It is **not** thread-safe and
is **not** cleared by `dispose_engines()` — its engines live for the
duration of the CLI process.

### Registration guard

Calling `database_config()` twice with the same `database_name` raises
`ConfigurationError("Duplicate database_name")`. This is enforced in
`_finalize_entries()` during config finalization, not at registration
time — which means the check runs lazily when config is first accessed
rather than at import time. This is intentional: it allows test suites
to call `reset_registry()` between tests without hitting duplicates.

### What happens on shutdown

`dispose_engines()` performs four operations in order:

1. Calls `.sync_engine.dispose()` on every cached `AsyncEngine` in the
   async session factory dict, releasing all pooled connections back to
   the PostgreSQL / MySQL / SQLite server.
2. Calls `.dispose()` on every cached `Engine` in the sync session
   factory dict.
3. Clears the ClickHouse client dicts, releasing references so the
   garbage collector can close the underlying HTTP connections.
4. Clears all four factory/client dicts.

After `dispose_engines()`, the next request that triggers
`_async_session_factory()` will create a fresh engine automatically.
There is no permanent engine registry — only URL-keyed caches.

### What `dbwarden_lifespan` guarantees

The `dbwarden_lifespan` context manager wraps this into a single
async context manager suitable for FastAPI's `lifespan` parameter:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(mode="check"):
        yield
```

This guarantees:

- **Startup:** Schema validation (or auto-migration) runs before the
  application starts serving requests.
- **Shutdown:** `dispose_engines()` runs in a `finally` block, so even
  if startup checks raise or the application crashes during the yield,
  engine pools are still released.

### Transaction boundaries

When you inject `handle.async_session` into a route, the session is
created by an `async_sessionmaker` with `expire_on_commit=False`.
The session's behavior:

- **No auto-commit.** You must call `await session.commit()` after
  writes. DBWarden has no implicit flush or commit logic.
- **Auto-rollback on error.** The FastAPI dependency uses an async
  context manager (`async with factory() as session`). If the route
  raises, the context manager calls `await session.rollback()` and
  then `await session.close()`.
- **`expire_on_commit=False`.** After `session.commit()`, previously
  loaded ORM objects retain their attribute values instead of being
  expired. This avoids the need to re-query after a commit within
  the same request.

### Locking

DBWarden provides two locking mechanisms. They solve different
problems and can be used independently or together.

**Database-level lock** (`engine/lock.py`): A row-level advisory lock
stored in `_dbwarden_lock` table. Used by the `migrate` CLI command
to prevent concurrent migration runs against the same database. It
supports a configurable `timeout` (default 300 seconds) — if the
lock cannot be acquired within the timeout, the command fails.

**Redis lock** (`fastapi/lock.py`): A distributed lock using Redis
`SETNX` + `EXPIRE`. Used by the `POST /migrate` FastAPI endpoint to
serialize migration requests across multiple application instances.
Key details:

- Default key: `dbwarden_migrate`
- Default **TTL: 60 seconds**. If the application crashes while
  holding the lock, Redis automatically releases it after 60 seconds.
  The lock must be re-acquired after the TTL expires, which means
  long-running migrations (>60s) need either a higher TTL or lock
  extension logic.
- Both async (`migration_lock`) and sync (`sync_migration_lock`)
  variants are provided.
- If you configure a custom TTL, set it comfortably above your
  longest expected migration duration.

**Concurrent requests during migration:** The `POST /migrate` endpoint
serializes via the Redis lock, but normal application routes continue
serving against the database while a migration runs. For destructive
operations (column drops, type changes that rewrite the table), live
requests may hit columns or constraints that no longer exist. DBWarden
does not provide a maintenance mode or request drain — handle this at
the infrastructure level (e.g., load-balancer health check removal
before triggering migrations).

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

For PostgreSQL, `generate-models` emits full `class Meta(PGTableMeta)` inner classes with all backend-specific metadata: identity columns, collation, storage, compression, partitioning, check constraints with `NO INHERIT`, deferred unique constraints, exclusion constraints, and index options. The round-trip is verified:

```bash
# Step 1: reverse-engineer a live PostgreSQL database
dbwarden generate-models -d primary --tables users

# Step 2: feed the generated models back in, zero diff
dbwarden make-migrations
# → No changes detected; the generated models match the DB exactly
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
