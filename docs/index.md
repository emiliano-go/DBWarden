---
description: DBWarden is a SQL-first database migration system for Python and SQLAlchemy.
  Generate reviewable SQL migrations from your models, validate them before production,
  and operate multiple databases from one config source.
---

<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-go/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
  <strong style="font-size: 2.5em;">DBWarden</strong>
</p>
<p align="center">
  <em>Your SQLAlchemy models are your migrations.</em>
</p>
<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12.7%2B-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python">
  </a>
  <a href="https://pypi.org/project/dbwarden/">
    <img src="https://img.shields.io/pypi/v/dbwarden?logo=pypi&logoColor=white&style=for-the-badge" alt="PyPI">
  </a>
  <a href="https://github.com/emiliano-go/DBWarden/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-10AC84?style=for-the-badge" alt="License">
  </a>
  <a href="https://deepwiki.com/emiliano-go/DBWarden/">
    <img src="https://img.shields.io/badge/DeepWiki-8A2BE2?logo=readthedocs&logoColor=white&style=for-the-badge" alt="DeepWiki">
  </a>
  <a href="https://codecov.io/gh/emiliano-go/DBWarden">
    <img src="https://img.shields.io/codecov/c/github/emiliano-go/DBWarden?logo=codecov&logoColor=white&style=for-the-badge" alt="Codecov">
  </a>
</p>

<p align="center">
  <strong><a href="https://dbwarden.emiliano-go.com/">Full documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/emiliano-go/DBWarden">Source Code</a></strong>
</p>

---

DBWarden is a database migration and schema management tool for SQLAlchemy. You define your schema in Python (in your SQLAlchemy models) and DBWarden derives everything else: migration SQL, rollbacks, snapshots, safety checks, and seed lifecycle.

There are no migration scripts to write or maintain. There is no migration runtime. Your models are the contract. The database is kept in sync with them.

## At a glance
- Generates migration files as plain SQL, with `-- upgrade` and `-- rollback` sections
- Reads SQLAlchemy models and backend-specific metadata from `class Meta`
- Supports PostgreSQL, MySQL, MariaDB, SQLite, and ClickHouse
- Uses a registry driven PostgreSQL pipeline for diffs and SQL emission
- Manages one or many databases from one typed config source
- Adds safety tooling, schema diffing, seed tracking, status commands, and FastAPI integration

- Migrations generated from your models, not written by hand
- Plain SQL output: reviewable, committable, executable anywhere
- Built-in rollback in every migration file
- Pre-deploy impact analysis: know what breaks before it ships
- Offline migration generation for CI pipelines without a live database
- Schema snapshots for deterministic diffs and rename detection
- Typed `class Meta` system with import-time validation
- Multi-database support: PostgreSQL, MySQL, ClickHouse, MariaDB, SQLite
- Versioned seed lifecycle with checksum drift detection
- Reverse-engineer live databases into models with `generate-models`

## Why DBWarden

Most migration tools ask you to maintain two representations of your schema: your ORM models and your migration files. When they drift, you find out at deploy time.

DBWarden eliminates the second representation. Your SQLAlchemy models are the schema definition. DBWarden reads them, diffs them against the current database state, and generates the SQL to close the gap (including rollback) without you writing a line of migration code.

This also means:

- No migration runtime to install or version
- No generated Python scripts that quietly do the wrong thing
- No schema drift discovered in production: drift is caught at `make-migrations` time
- Migrations that can be generated in CI without a database connection

DBWarden is not a wrapper around Alembic. It is a different approach to the same problem: Alembic asks you to describe *how* to change the database; DBWarden asks you to describe *what* the schema should be.

## From zero to production

Typical adoption path in an existing project:

1. Point DBWarden at your existing SQLAlchemy models
2. Run initial `make-migrations` to generate a baseline schema
3. Commit generated migrations as your source of truth
4. Replace your current migration workflow with the DBWarden CLI
5. Optionally enable:
   - Migration impact analysis for safer deploys
   - Offline mode for CI pipelines without a database service
   - FastAPI integration for startup validation and health checks

## Installation

```bash
uv add dbwarden
uv add "dbwarden[fastapi]"   # FastAPI integration
uv add "dbwarden[metrics]"   # Prometheus metrics
uv add "dbwarden[sandbox]"   # Docker-backed test databases
```

Requirements: Python 3.12+, SQLAlchemy 2.0+.

Optional dependency groups:

| Group        | Default | Provides                             |
|--------------|---------|--------------------------------------|
| `[postgres]` | Yes     | `psycopg2-binary`                    |
| `[mysql]`    |         | `pymysql`                            |
| `[clickhouse]` |       | `clickhouse-connect`, `aiohttp`      |
| `[fastapi]`  |         | `fastapi`, `pydantic`, `asyncpg`, `aiosqlite` |
| `[sandbox]`  |         | `testcontainers`                     |
| `[metrics]`  |         | `prometheus-client`                  |
| `[dev]`      |         | `pytest`, `zensical`, `seoslug`, `httpx2` |

## Quick start

### 1. Configure

Create a file named `dbwarden.py` in your project root:

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
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.databases import IndexSpec, TableMeta


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    class Meta(TableMeta):
        comment = "Core user accounts"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    class Meta(TableMeta):
        indexes = [
            IndexSpec(name="ix_posts_created_at", columns=["created_at"]),
        ]
```

### 3. Generate a migration

```bash
dbwarden init
dbwarden make-migrations "create initial tables"
```

Output: both upgrade and rollback in the same file.

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

## Typical workflow

1. Define or update your SQLAlchemy models with `class Meta` annotations
2. Run `dbwarden make-migrations` to generate SQL
3. Review the generated `.sql` file and its rollback section
4. Run `dbwarden migrate` to apply
5. Verify with `dbwarden status`

---

## Migration engine

**Model-driven generation**: DBWarden reads your SQLAlchemy models directly. When you change a model, it diffs the new state against the last snapshot and generates the SQL to reconcile them.

**Plain SQL output**: Generated migrations are `.sql` files. No migration runtime, no generated Python. Review them, commit them, execute them directly against any environment.

**Rollback included**: Every migration carries both upgrade and rollback SQL in the same file. Rollback SQL is generated automatically: you do not write it.

**Schema snapshots**: After every migration, a checksummed JSON snapshot is written to `.dbwarden/schemas/`. Snapshots power rename detection, offline diffing, and column-level comparisons without querying the live database.

**Column-level diffing**: Type, nullability, default, and comment changes generate precise `ALTER COLUMN` statements.

**Typed `class Meta`**: The `_MetaValidator` metaclass validates every attribute on `class Meta` at import time. Typos that would have silently produced wrong DDL now raise `DBWardenConfigError` immediately.

```python
class Meta(MyTableMeta):
    my_engin = "InnoDB"  # DBWardenConfigError: unknown attr 'my_engin'
```

Supported index features:

- Partial indexes (`WHERE` clause)
- Covering indexes (`INCLUDE` columns)
- `USING` access methods
- `NULLS NOT DISTINCT` (PostgreSQL 15+)
- Per-column sort order
- Storage parameters (`WITH (fillfactor=...)`)
- ClickHouse skip indexes via `ChIndexSpec`

---

## Pre-deploy impact analysis

Before applying schema changes, DBWarden can scan your codebase to identify what will be affected. It uses AST analysis with a grep fallback, so results reflect actual code structure rather than text matches.

```bash
dbwarden check-impact 0042 --database primary
```

Output:

```
drop_column on users.username
  References: 2
    app/routes/users.py:34  attribute_access
      .username
    app/templates/profile.jinja2:12  grep
      user.username
```

Run this before any destructive deploy to surface breaking changes before they reach production.

---

## Offline migrations

Export model state once, then generate migrations on any machine without a database connection. Designed for CI pipelines and local development without a running database.

```bash
dbwarden export-models --database primary
git add .dbwarden/model_state.json
```

Then on any machine, with no database required:

```bash
dbwarden make-migrations "add bio column" --offline
```

The model state file is updated in place after each migration.

---

## Reverse-engineer models

Generate SQLAlchemy models from a live database with round-trip support (PostgreSQL, MySQL, ClickHouse, SQLite):

```bash
dbwarden generate-models --database primary --tables users,posts
dbwarden generate-models --database primary --base app.database:Base
```

By default each generated file declares its own `Base = declarative_base()`. Use `--base` to import a custom Base class from your project instead (e.g. `--base app.database:Base` or `--base app.database:DeclarativeBase`). The generated output includes `class Meta` blocks with all detected backend-specific metadata.

---

## Supported databases

| Database   | Round-trip | Notes                                       |
|------------|------------|---------------------------------------------|
| PostgreSQL | Full       | Primary backend, full schema fidelity       |
| MySQL      | Full       | DDL parity focus                            |
| ClickHouse | Full       | Analytics backend, MergeTree engine family  |
| SQLite     | Dev only   | Local development and SQL translation       |
| MariaDB    | No         | Schema layer complete; snapshot gaps remain |

### PostgreSQL

First-class support with full round-trip schema fidelity. Supported features include identity and generated columns, partitioning, table inheritance, exclusion constraints, deferrable constraints, advanced indexes via `PgIndexSpec`, per-column storage and collation, enum type creation, and full type normalization (SERIAL, TIMESTAMPTZ, NUMERIC, JSONB, UUID, ARRAY, TSTZRANGE).

### MySQL

Full round-trip support with `MyTableMeta` / `MyColumnMeta` and `my.field()` spec objects. Engine-level options (`my_engine`, `my_charset`, `my_collate`, `my_row_format`), column-level options (`unsigned`, `charset`, `collate`, `on_update`), and model reverse-engineering via `generate-models`.

```bash
uv add "dbwarden[mysql]"
```

### ClickHouse

First-class analytics backend support. MergeTree engine family via `ChEngineSpec`, replicated engines, projections, dictionaries, materialized views, skip indexes via `ChIndexSpec`, column codecs, `LowCardinality` and `Nullable` type wrappers.

```bash
uv add "dbwarden[clickhouse]"
```

### MariaDB

Schema layer is complete with `MdbTableMeta` / `MdbColumnMeta` and `mdb.field()` spec objects including MariaDB-specific features (`page_compressed`, `invisible`, `without_overlaps`). Snapshot capture and reverse-engineering of MariaDB-specific features are not yet complete.

---

## Seed lifecycle

DBWarden manages versioned database seeds alongside migrations. Seeds are defined as Python classes and applied with checksum drift detection.

```python
from dbwarden import Seed

class CountrySeed(Seed):
    __seed_database__ = "primary"
    rows = [
        Country(code="US", name="United States"),
        Country(code="UY", name="Uruguay"),
    ]
```

Rows take model instances: full IDE autocomplete on every field. Versions are assigned automatically by class order, no manual numbering.

Conflict resolution, auto-apply after `dbwarden migrate`, and SQL export for stateless production deployment are all supported.

```bash
dbwarden seed export   # renders seeds as plain SQL for stateless deploy
dbwarden seed list     # shows applied seeds and checksum status
```

---

## Developer experience

**Dev mode**: Run SQLite locally against a PostgreSQL production schema with automatic SQL translation.

**Sandbox and dry-run**: Test migrations in a temporary database or preview SQL without touching anything.

**Multi-database**: One project, multiple databases, full isolation between them. Use `model_tables` to assign table ownership per database when sharing model paths.

**Observability**: Prometheus metrics (6 families), structured JSON logging, and health/status endpoints.

**Generate models**: Reverse-engineer a live database (PostgreSQL, MySQL, ClickHouse) into SQLAlchemy models with `dbwarden generate-models`.

**`dbwarden diff`**: Read-only comparison tool. Outputs as Rich table, JSON, or raw SQL. Supports `--offline` mode.

**Graceful disconnection**: Automatic retry logic and clear error messages when a database is unreachable.

---

## FastAPI integration

DBWarden includes optional FastAPI integration for projects that use it. It is not required.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.extensions.fastapi import dbwarden_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(app, mode="check"):
        yield

app = FastAPI(lifespan=lifespan)
```

On startup: schema validation or auto-migration, readiness gate, connection pool warmup, optional seed application. On shutdown: engine pools and ClickHouse clients disposed.

Sessions are exposed directly from the configuration object:

```python
@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

Health and management routers:

```python
from dbwarden.extensions.fastapi import DBWardenHealthRouter, DBWardenRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
app.include_router(DBWardenRouter(), prefix="/db")
```

`DBWardenHealthRouter` exposes `/liveness`, `/readiness`, and per-database status. `DBWardenRouter` exposes `GET /status` and `POST /migrate`.

### Auto-generated Pydantic schemas

`@auto_schema` generates `CreateSchema`, `UpdateSchema`, and `PublicSchema` from model annotations, eliminating duplicated definitions between your ORM layer and your API layer.

```python
from dbwarden.databases import auto_schema

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
user = User.CreateSchema(email="a@b.com", password_hash="secret")
user.to_schema()  # PublicSchema excludes password_hash automatically
```

---

## License

MIT

---

DBWarden is built for teams that want explicit, reviewable, reproducible database changes, derived from the models they already maintain, not from migration scripts they have to write.

## Next Steps

- Start with [Features](features.md)
- Follow the guides in [Get Started](getting-started/setup.md)
- Explore [Cookbook & Examples](cookbook/index.md)
- Use [CLI Reference](cli-reference.md) as command lookup
