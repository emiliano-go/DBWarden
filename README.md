<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
    <em>The SQL-first database toolkit for SQLAlchemy.</em>
</p>
<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python">
  </a>
  <a href="https://pypi.org/project/dbwarden">
    <img src="https://img.shields.io/badge/PyPI-0.9.0-34D058?logo=pypi&logoColor=white&style=for-the-badge" alt="PyPI">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-10AC84?style=for-the-badge" alt="License">
  </a>
  <a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden/">
    <img src="https://img.shields.io/badge/DeepWiki-8A2BE2?logo=readthedocs&logoColor=white&style=for-the-badge" alt="DeepWiki">
  </a>
</p>

<p align="center">
  <strong><a href="https://emiliano-gandini-outeda.me/DBWarden/">→ Full documentation</a></strong>
</p>

---

DBWarden generates plain SQL migrations from SQLAlchemy models. Rollback included. No DSL. No live database required.

```bash
pip install dbwarden
pip install "dbwarden[fastapi]"   # FastAPI integration
pip install "dbwarden[metrics]"   # Prometheus metrics
```

## Quickstart

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

```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base
from dbwarden import TableMeta, PgIndexSpec

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
            PgIndexSpec("ix_posts_created_at", ["created_at"]),
        ]
```

```bash
dbwarden make-migrations    # generates SQL in migrations/primary/
dbwarden migrate            # applies pending migrations
dbwarden status             # shows current schema version
```

Output from `make-migrations`:

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

## Key Features

- **Schema snapshots**: After every migration, a checksummed JSON snapshot is written. Subsequent `make-migrations` runs diff against the snapshot, not the live database. Enables rename detection, column-level diffing, and fully offline generation.
- **Offline migrations**: `dbwarden export-models` writes model state to `.dbwarden/model_state.json`. Then `dbwarden make-migrations --offline` works in CI with no database service.
- **Column-level diffing**: Type, nullable, default, and comment changes produce precise `ALTER COLUMN` statements.
- **PostgreSQL first-class**: generate-models produces `class Meta(PGTableMeta)` with full metadata. Identity columns, generated columns, collation, storage, compression, fillfactor, tablespace, partitioning, inheritance, exclusion constraints, deferrable FKs, and advanced index options via `PgIndexSpec`.
- **ClickHouse first-class**: `ChEngineSpec`, `ChIndexSpec`, `ProjectionSpec`, `CHColumnMeta` for engine options, skip indexes, projections, codecs, LowCardinality/Nullable. Auto-detected by `generate-models`.
- **FastAPI-native sessions**: `session=primary.async_session` as a route annotation. No `Depends()`, no `Annotated`, no `SessionDep`.
- **Health endpoints**: `GET /health/liveness`, `GET /health/readiness`, per-database health. Optional `X-API-Key` auth.
- **Observability**: Prometheus metrics (6 families), JSON logging, query tracing middleware, pool metrics collector.
- **Migration impact analysis**: `dbwarden check-impact` scans your codebase for references to affected schema elements before applying destructive migrations.
- **Auto-generated Pydantic schemas**: `@auto_schema` generates `Schema`, `CreateSchema`, `UpdateSchema`, and `PublicSchema` from your model annotations. Fields with `public=False` or `_` prefix are excluded automatically.
- **In-code seeds**: `@seed_data` decorator defines seed data alongside models. Coexists with file-based seeds (`V0001__*.sql`, `V0001__*.py`).
- **Multi-database**: One project, multiple databases, full isolation.
- **Dev mode**: Run SQLite locally against a PostgreSQL production schema with automatic SQL translation.
- **Sandbox and dry-run**: Test migrations in a temporary database or preview SQL without touching anything.

## PostgreSQL

```python
from dbwarden import PGTableMeta, PGColumnMeta, PgIndexSpec

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    bio = Column(Text)

    class Meta(PGTableMeta):
        pg_fillfactor = 80
        pg_indexes = [
            PgIndexSpec("ix_users_email", ["email"], unique=True),
        ]

        class id(PGColumnMeta):
            pg_identity = "always"

        class bio(PGColumnMeta):
            pg_storage = "EXTENDED"
            pg_compression = "pglz"
```

```bash
dbwarden generate-models -d primary    # reverse-engineer live DB
dbwarden make-migrations                # zero diff with live database
```

## ClickHouse

```python
from dbwarden import CHTableMeta, CHColumnMeta, ChEngineSpec, ChIndexSpec, ProjectionSpec

class Event(Base):
    __tablename__ = "events"
    id = Column(Int64, primary_key=True)
    payload = Column(String)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = ["event_date", "id"]
        ch_partition_by = "toYYYYMM(event_date)"
        ch_ttl = ["event_date + toIntervalYear(1)"]
        ch_settings = {"index_granularity": "8192"}
        ch_indexes = [
            ChIndexSpec("ix_payload", ["payload"], type="bloom_filter", granularity=1),
        ]
        ch_projections = [
            ProjectionSpec("by_date", "SELECT event_date, sum(amount) GROUP BY event_date"),
        ]

        class payload(CHColumnMeta):
            ch_codec = "ZSTD(3)"
```

```bash
dbwarden generate-models -d analytics    # auto-detects ClickHouse
dbwarden make-migrations                 # zero diff
```

## FastAPI

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dbwarden_lifespan, DBWardenHealthRouter

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(app, mode="check", readiness_gate=True):
        yield

app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")

@app.get("/users")
async def list_users(session=primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

## Observability

```python
from dbwarden.fastapi import MetricsRouter, MetricsMiddleware, QueryTracingMiddleware

app.include_router(MetricsRouter())
app.add_middleware(MetricsMiddleware)
app.add_middleware(QueryTracingMiddleware, slow_query_threshold_ms=100)
```

Six Prometheus metric families: migration counters, duration histograms, schema/seed version gauges, pending migration gauge, error counters.

## Auto-Generated Schemas

```python
from dbwarden.schema import auto_schema

@auto_schema
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255))
    password_hash = Column(String(255))

    class Meta(TableMeta):
        class password_hash:
            public = False

# User.CreateSchema, User.UpdateSchema, User.PublicSchema
data = User.CreateSchema(email="a@b.com", password_hash="secret")
api_result = user.to_schema()  # PublicSchema, excludes password_hash
```

## In-Code Seeds

```python
from dbwarden.schema import seed_data, SeedRow

@seed_data(database="primary", version="0001", description="initial countries")
class CountrySeed:
    model = Country
    rows = [SeedRow(code="UY", name="Uruguay")]
```

## Migration Impact Analysis

```bash
dbwarden check-impact 0042 --database primary
# Scans codebase for references to affected columns/tables
# Uses AST analysis (default) with grep fallback
```

## Offline Migrations

```bash
dbwarden export-models --database primary
git add .dbwarden/model_state.json
# On any machine without DB access:
dbwarden make-migrations "add bio column" --offline
```

## Supported Databases

| Database   | `database_type` |
|------------|-----------------|
| PostgreSQL | `postgresql`    |
| MySQL      | `mysql`         |
| MariaDB    | `mariadb`       |
| SQLite     | `sqlite`        |
| ClickHouse | `clickhouse`    |

## License

MIT
