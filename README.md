# DBWarden

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
    <img src="https://img.shields.io/badge/PyPI-0.9.2-34D058?logo=pypi&logoColor=white&style=for-the-badge" alt="PyPI">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-10AC84?style=for-the-badge" alt="License">
  </a>
  <a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden/">
    <img src="https://img.shields.io/badge/DeepWiki-8A2BE2?logo=readthedocs&logoColor=white&style=for-the-badge" alt="DeepWiki">
  </a>
</p>

<p align="center">
  <strong><a href="https://emiliano-gandini-outeda.me/DBWarden/">Full documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/emiliano-gandini-outeda/DBWarden">Source Code</a></strong>
</p>

---

DBWarden is a SQL-first migration system for SQLAlchemy that replaces Python-based migration workflows with explicit, reviewable SQL generated directly from your models.

Unlike script-based migration tools, DBWarden does not introduce a migration runtime or require executing generated Python migration code. It produces plain SQL files that can be reviewed, versioned, and executed directly against any environment.

All migrations are generated as plain SQL and can be reviewed before execution.

FastAPI integration, offline generation, and migration safety tooling are built around that core model.

## At a glance

- SQL-first migrations from SQLAlchemy models
- No migration runtime required
- Offline CI migration generation
- Built-in rollback in every migration
- Schema snapshots for deterministic diffing
- Pre-deploy impact analysis for code safety

## Why DBWarden?

Most migration systems rely on one of two approaches:

- Python-based migration scripts generated and executed at runtime
- Manual SQL migrations written and maintained by hand

Both introduce friction: migrations are tied to a runtime, changes are hard to audit in CI without a database, and schema drift is only discovered at deploy time.

DBWarden removes this entire class of problems. It generates plain SQL migrations directly from SQLAlchemy models, with:

- no migration runtime required
- no generated Python migration scripts
- full rollback included in every migration file
- schema snapshots for deterministic diffs over time

This enables:

- CI migration generation without a database
- deterministic schema history via snapshots
- pre-deploy detection of destructive or breaking changes

DBWarden is designed as a drop-in replacement for migration workflows built around Alembic or hand-written SQL, without introducing a migration runtime or script execution layer.

## Installation

```bash
pip install dbwarden
pip install "dbwarden[fastapi]"   # FastAPI integration
pip install "dbwarden[metrics]"   # Prometheus metrics
pip install "dbwarden[sandbox]"   # Docker-backed test databases
```

Requirements: Python 3.12.7+, SQLAlchemy 2.0+.

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
from dbwarden import TableMeta, IndexSpec

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
            IndexSpec(name="ix_posts_created_at", columns=["created_at"]),
        ]
```

### 3. Generate a migration

```bash
dbwarden make-migrations
```

Every migration includes both upgrade and rollback SQL by default.

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

## Typical workflow

1. Define your SQLAlchemy models with `class Meta` annotations
2. Run `dbwarden make-migrations` to generate SQL
3. Review the generated `.sql` file and its rollback section
4. Run `dbwarden migrate` to apply
5. Verify with `dbwarden status`

## From zero to production

Typical adoption path in an existing project:

1. Point DBWarden at your existing SQLAlchemy models
2. Run initial `make-migrations` to generate a baseline schema
3. Commit generated migrations as your source of truth
4. Replace your current migration workflow with the DBWarden CLI
5. Optionally enable:
   - migration impact analysis for safer deploys
   - offline mode for CI pipelines without a database service
   - FastAPI integration for startup validation and health checks

---

## Migration engine

- **SQL-first**: Migrations are plain SQL files. No migration runtime required.
- **Rollback included**: Every migration carries both upgrade and rollback SQL in the same file.
- **Schema snapshots**: After every migration, a checksummed JSON snapshot is written. Snapshots power rename detection, offline diffing, and column-level comparisons without querying the live database.
- **Column-level diffing**: Type, nullability, default, and comment changes generate precise `ALTER COLUMN` statements.
- **Rich index support**: Advanced index features for PostgreSQL and ClickHouse use cases.

<details>
<summary>Supported index features</summary>

- Partial indexes (`WHERE` clause)
- Covering indexes (`INCLUDE` columns)
- `USING` access methods
- `NULLS NOT DISTINCT` (PostgreSQL 15+)
- Per-column sort order
- Storage parameters (`WITH (fillfactor=...)`)
- ClickHouse skip indexes via `ChIndexSpec`

</details>

## What will break if this ships?

Before applying schema changes, DBWarden can scan your codebase to identify what will be affected. It uses AST analysis with a grep fallback, so results reflect actual code structure rather than text matches.

```bash
dbwarden check-impact 0042 --database primary
```

Output:

```
drop_column on users.username
  Affects:
    app/routes/users.py:34 (attribute access)
    app/templates/profile.jinja2:12 (template usage)
```

Run this before any destructive deploy to surface breaking changes before they reach production.

## Offline migrations

Export model state once, then generate migrations on any machine without a database connection. Useful for CI pipelines and local development without a running database.

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

## PostgreSQL (primary backend)

First-class support with full round-trip schema fidelity. Reverse-engineer a live database, feed the output back into `make-migrations`, and get zero diff.

```bash
dbwarden generate-models -d primary --tables users
dbwarden make-migrations
# No changes detected
```

Supported features:

- Identity columns and generated columns
- Partitioning and table inheritance
- Exclusion constraints and deferrable constraints
- Advanced indexes via `PgIndexSpec` (INCLUDE, WHERE, USING, NULLS NOT DISTINCT, column sort order)
- Per-column storage, compression, and collation
- Enum type creation and value addition
- Full type normalization: SERIAL, TIMESTAMPTZ, NUMERIC, VARCHAR, JSONB, UUID, ARRAY, TSTZRANGE

## ClickHouse (analytics backend)

First-class support for ClickHouse analytics workloads, including schema generation and round-trip validation for supported features.

```bash
dbwarden generate-models -d analytics
dbwarden make-migrations
# No changes detected
```

Supported features:

- MergeTree engine family via `ChEngineSpec`
- Replicated engines with ZooKeeper path configuration
- Projections via `ProjectionSpec`
- Dictionaries and materialized views
- Skip indexes via `ChIndexSpec`
- Column codecs
- `LowCardinality` and `Nullable` type wrappers

---

## FastAPI integration

### Sessions

DBWarden exposes database sessions directly from the configuration object, keeping route handlers declarative while avoiding dependency boilerplate.

```python
@app.get("/users")
async def list_users(session=primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

### Lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dbwarden_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(app, mode="check"):
        yield

app = FastAPI(lifespan=lifespan)
```

On startup: schema validation or auto-migration, readiness gate, connection pool warmup, and optional seed application. On shutdown: all engine pools and ClickHouse clients disposed.

### Routers

```python
from dbwarden.fastapi import DBWardenHealthRouter, DBWardenRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
app.include_router(DBWardenRouter(), prefix="/db")
```

`DBWardenHealthRouter` exposes `/liveness`, `/readiness`, and per-database status endpoints. `DBWardenRouter` exposes `GET /status` and `POST /migrate`.

## Auto-generated Pydantic schemas

DBWarden can generate request and response schemas directly from model annotations, eliminating duplicated definitions between your ORM layer and your API layer. This keeps API schemas and ORM models in sync without duplication.

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
user = User.CreateSchema(email="a@b.com", password_hash="secret")
user.to_schema()  # PublicSchema excludes password_hash automatically
```

`@auto_schema` generates `CreateSchema`, `UpdateSchema`, and `PublicSchema` from model annotations. Fields marked `public = False` are excluded from `PublicSchema` without any additional filtering logic in your routes.

Optional but powerful: derive your entire API schema layer directly from your SQLAlchemy models.

---

## Developer experience

- **Dev mode**: Run SQLite locally against a PostgreSQL production schema with automatic SQL translation.
- **Sandbox and dry-run**: Test migrations in a temporary database or preview SQL without touching anything.
- **Multi-database**: One project, multiple databases, full isolation between them.
- **Versioned seeds**: SQL, Python, and in-code seeds with checksummed idempotent application via `@seed_data`.
- **Observability**: Prometheus metrics (6 families), structured JSON logging, FastAPI routers for `/metrics`, `/status`, `/migrate`, `/health/liveness`, `/health/readiness`.
- **Generate models**: Reverse-engineer a live database into SQLAlchemy models with `dbwarden generate-models`.

---

## Supported databases

| Database   | Role                          | Notes                            |
|------------|-------------------------------|----------------------------------|
| PostgreSQL | Primary transactional backend | Full round-trip fidelity         |
| ClickHouse | Analytics backend             | Full schema support              |
| MySQL      | General support               | DDL parity focus                 |
| MariaDB    | General support               | MySQL-compatible mode            |
| SQLite     | Dev and testing               | Used in dev mode SQL translation |

---

## License

MIT

---

DBWarden is designed for teams that want explicit, reviewable, and reproducible database changes without relying on a migration runtime.
