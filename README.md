<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
    <em>The SQL-first database toolkit for SQLAlchemy.</em>
</p>
<p align="center">
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/v/dbwarden?color=%2334D058&label=pypi" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/pyversions/dbwarden.svg?color=%2334D058" alt="Python versions"/></a>
  <a href="https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE"><img src="https://img.shields.io/github/license/emiliano-gandini-outeda/DBWarden?color=%2334D058" alt="License"/></a>
</p>

<p align="center">
  <strong><a href="https://emiliano-gandini-outeda.me/DBWarden/">→ Full documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/emiliano-gandini-outeda/DBWarden">Source Code</a></strong>
</p>

---

DBWarden is a SQL-first migration system for SQLAlchemy. It reads your models, generates plain SQL migration files with rollback included, and tracks schema state through checksummed snapshots. No DSL, no live database required to generate migrations. FastAPI integration, async sessions, observability, seed management, and migration impact analysis are built in.

## Key Features

- **SQL-first**: Migrations are plain SQL. No DSL, no generated abstraction layer.
- **Rollback included**: Every migration carries both upgrade and rollback SQL.
- **Schema snapshots**: After every migration, a checksummed JSON snapshot is written. These snapshots power rename detection, offline migration generation, and column-level diffing without querying the live database.
- **Offline migrations**: Export model state to a JSON file with `export-models`, then run `make-migrations --offline` in CI pipelines with no database service.
- **Column-level diffing**: Type, nullable, default, and comment changes generate precise `ALTER COLUMN` statements.
- **Rich index metadata**: Partial indexes (`WHERE`), covering indexes (`INCLUDE`), `USING` methods, `NULLS NOT DISTINCT`, column sort order, storage parameters, and ClickHouse skip indexes via typed `PgIndexSpec` and `ChIndexSpec` dataclasses.
- **PostgreSQL first-class**: Full round-trip fidelity: reverse-engineer a live database, feed into `make-migrations`, zero diff. Identity columns, generated columns, collation, storage, compression, partitioning, exclusion constraints, deferrable FKs.
- **ClickHouse first-class**: `ChEngineSpec`, `ProjectionSpec`, `ChIndexSpec` for table options, replicated engines, dictionaries, materialized views, projections, skip indexes, codecs, LowCardinality/Nullable.
- **FastAPI-native sessions**: `session=primary.async_session` as a route annotation: no `Depends`, no `Annotated`, no `SessionDep`.
- **Single config source**: `database_config(...)` drives migrations, sessions, health checks, and seeds.
- **Multi-database**: One project, multiple databases, full isolation.
- **Dev mode**: Run SQLite locally against a PostgreSQL production schema with automatic SQL translation.
- **Sandbox and dry-run**: Test migrations in a temporary database or preview SQL without touching anything.
- **Migration impact analysis**: `dbwarden check-impact` scans your codebase for references to affected schema elements before applying destructive migrations.
- **Observability**: Prometheus metrics (6 families), JSON logging, FastAPI routers for `/metrics`, `/status`, `/migrate`, `/health/liveness`, `/health/readiness`.
- **Versioned seeds**: SQL and Python seed files with checksummed idempotent application. In-code seeds via `@seed_data` decorate classes alongside models.
- **Auto-generated Pydantic schemas**: `@auto_schema` generates `CreateSchema`, `UpdateSchema`, `PublicSchema` from your model annotations.

## Requirements

- Python 3.12.7+
- SQLAlchemy 2.0+

## Installation

```bash
pip install dbwarden
pip install "dbwarden[fastapi]"   # FastAPI integration
pip install "dbwarden[metrics]"   # Prometheus metrics
pip install "dbwarden[sandbox]"   # Docker-backed test databases
```

## Quickstart

### 1. Configure

```python
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/myapp",
    database_url_async="postgresql+asyncpg://user:pass@localhost:5432/myapp",
)
```

### 2. Define your models

```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base
from dbwarden import TableMeta, index

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    bio = Column(Text, nullable=True)

    class Meta(TableMeta):
        comment = "Core user accounts"


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)

    class Meta(TableMeta):
        indexes = [
            index("ix_posts_created_at", ["created_at"]),
        ]
```

### 3. Generate a migration

```bash
dbwarden make-migrations
```

Output:

```sql
-- upgrade
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    bio TEXT
);
COMMENT ON TABLE users IS 'Core user accounts';

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_posts_created_at ON posts (created_at);

-- rollback
DROP TABLE posts;
DROP TABLE users;
```

### 4. Apply

```bash
dbwarden migrate
```

### 5. Check status

```bash
dbwarden status
```

---

## PostgreSQL First-Class

Reverse-engineer a live PostgreSQL database with `generate-models`, feed the output back into `make-migrations`, and get **zero diff**:

```bash
dbwarden generate-models -d primary --tables users
dbwarden make-migrations
# → No changes detected
```

The round-trip is confirmed: your generated models match the database schema exactly. The following PostgreSQL features are fully supported:

- Identity columns with sequence options
- Generated columns (`GENERATED ALWAYS AS (...) STORED`)
- Per-column collation, storage, and compression
- Table fillfactor, tablespace, unlogged tables, and partitioning
- Table inheritance and exclusion constraints
- Deferrable foreign keys and check constraints with `NO INHERIT`
- Deferred unique constraints with `NULLS NOT DISTINCT` and `INCLUDE`
- Index options: `USING`, `WHERE`, `INCLUDE`, `WITH`, `NULLS NOT DISTINCT`, column sort order via `PgIndexSpec`
- Named enum types with `ALTER TYPE ... ADD VALUE`
- Type normalization: `SERIAL`, `TIMESTAMPTZ`, `NUMERIC(p,s)`, `VARCHAR(n)`, `JSONB`, `UUID`, `ARRAY`, `TSTZRANGE`

---

## ClickHouse First-Class

```bash
dbwarden generate-models -d analytics
# Auto-detects ClickHouse, generates CHTableMeta + ChEngineSpec + ChIndexSpec
dbwarden make-migrations
# → Zero diff with live database
```

Metadata is declared in `class Meta(CHTableMeta)` with typed specs:

```python
from dbwarden import CHTableMeta, ChEngineSpec, ChIndexSpec, ProjectionSpec, CHColumnMeta

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    event_date = Column(Date)
    payload = Column(String)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = ["event_date", "id"]
        ch_partition_by = "toYYYYMM(event_date)"
        ch_ttl = ["event_date + toIntervalYear(1)"]
        ch_settings = {"index_granularity": "8192"}
        ch_indexes = [
            ChIndexSpec("ix_payload", ["payload"],
                type="bloom_filter", granularity=1),
        ]
        ch_projections = [
            ProjectionSpec("by_date",
                "SELECT event_date, sum(amount) GROUP BY event_date"),
        ]

        class payload(CHColumnMeta):
            ch_codec = "ZSTD(3)"
```

---

## FastAPI Integration

### Lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dbwarden_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(
        app, mode="check", readiness_gate=True, pool_warmup=True,
    ):
        yield

app = FastAPI(lifespan=lifespan)
```

On startup, `dbwarden_lifespan` validates the schema, checks database readiness, and warms connection pools. On shutdown, it disposes all engine pools.

### Per-Request Sessions

```python
@app.get("/users")
async def list_users(session=primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

The handle from your config becomes a FastAPI dependency annotation. No `Depends()`, no `Annotated`, no `SessionDep` type alias.

### Routers

```python
from dbwarden.fastapi import DBWardenHealthRouter, DBWardenRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
app.include_router(DBWardenRouter(), prefix="/db")
```

Health router exposes `/liveness`, `/readiness`, and per-database health endpoints. DBWardenRouter exposes `GET /status` and `POST /migrate`.

---

## Auto-Generated Pydantic Schemas

Decorate a model with `@auto_schema` to get Pydantic `Schema`, `CreateSchema`, `UpdateSchema`, and `PublicSchema` for request validation and API responses:

```python
from dbwarden.schema import auto_schema

@auto_schema
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)

    class Meta(TableMeta):
        class password_hash:
            public = False
```

```python
# In a route:
data = User.CreateSchema(email="a@b.com", password_hash="secret")
user = User.from_schema(data)
session.add(user)
await session.commit()

api_result = user.to_schema()  # PublicSchema excludes password_hash
```

`CreateSchema` derives required fields from nullable columns. `PublicSchema` omits fields with `public = False` or names starting with `_`. No separate schema definitions to maintain.

---

## Observability

```python
from dbwarden.fastapi import MetricsRouter, MetricsMiddleware, QueryTracingMiddleware

app.include_router(MetricsRouter())
app.add_middleware(MetricsMiddleware)
app.add_middleware(QueryTracingMiddleware, slow_query_threshold_ms=100)
```

| Metric | Type | What it tracks |
|---|---|---|
| `dbwarden_migrations_total` | Counter | Migrations applied, by database and version |
| `dbwarden_migration_duration_seconds` | Histogram | Duration per migration |
| `dbwarden_schema_version` | Gauge | Current schema version per database |
| `dbwarden_seed_version` | Gauge | Current seed version per database |
| `dbwarden_migrations_pending` | Gauge | Pending migration count |
| `dbwarden_migration_errors_total` | Counter | Migration errors by type |

`QueryTracingMiddleware` logs per-request query count, total duration, slowest query, and slow query threshold breaches.

---

## Offline Migrations

Export model state for CI pipelines with no database:

```bash
dbwarden export-models --database primary
git add .dbwarden/model_state.json
```

Then on any machine without database access:

```bash
dbwarden make-migrations "add bio column" --offline
```

The model state file is updated in place after each migration.

---

## Migration Impact Analysis

Before applying a destructive migration, scan your codebase for affected references:

```bash
dbwarden check-impact 0042 --database primary
```

Output:

```
Migration: primary__0042_drop_username
Impact detected: 1 operation(s) affect code

drop_column on users.username
  References: 2
    app/routes/users.py:34  attribute_access
      .username
    app/templates/profile.jinja2:12  grep
      user.username
```

Supports AST analysis (default), grep (fallback), and deep introspection (`--deep`).

---

## In-Code Seeds

Define seeds alongside your models using `@seed_data`:

```python
from dbwarden.schema import seed_data, SeedRow

@seed_data(database="primary", version="0001", description="initial countries")
class CountrySeed:
    model = Country
    rows = [SeedRow(code="UY", name="Uruguay")]
```

Or with programmatic logic:

```python
@seed_data(database="primary", version="0002", description="load permissions")
class PermissionSeed:
    model = Permission

    @staticmethod
    def generate(session):
        for resource in ["users", "orders"]:
            for action in ["read", "write"]:
                session.add(Permission(name=f"{resource}:{action}"))
```

Coexists with file-based seeds and sorts by version at apply time.

---

## Sandbox and Dry-Run

```bash
dbwarden migrate --dry-run          # Preview SQL without execution
dbwarden migrate --sandbox          # Apply in a temporary in-memory SQLite database
dbwarden migrate --sandbox -d pg    # Apply in a Docker-backed PostgreSQL sandbox
```

---

## Versioned Seeds

```bash
dbwarden seed create "Initial Countries"
dbwarden seed apply
dbwarden seed list
dbwarden seed rollback
```

Seeds are tracked in a `_dbwarden_seeds` table with checksums, making them idempotent. Both file seeds (`V0001__*.sql`, `V0001__*.py`) and in-code seeds (`@seed_data`) are supported.

---

## Generate Models

```bash
# One file per table:
dbwarden generate-models -d primary --tables users,orders

# Single file with ClickHouse engine metadata (auto-detected):
dbwarden generate-models -d analytics --single-file
```

---

## Multi-Database

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/main",
    database_url_async="postgresql+asyncpg://user:pass@localhost:5432/main",
    model_paths=["models/primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="clickhouse://user:pass@localhost:8123/analytics",
    model_paths=["models/analytics"],
)
```

```bash
dbwarden migrate --all
```

---

## Dev Mode

```python
primary = database_config(
    ...
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
)
```

```bash
dbwarden --dev migrate
```

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
