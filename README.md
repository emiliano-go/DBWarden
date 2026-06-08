<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
    <em>Migrations for FastAPI, without the DSL.</em>
</p>
<p align="center">
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/v/dbwarden?style=for-the-badge&logo=python&logoColor=white&label=PyPI&color=3776AB" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/pyversions/dbwarden?style=for-the-badge&logo=python&logoColor=white&label=Python&color=3776AB" alt="Python versions"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-10AC84?style=for-the-badge" alt="License"/></a>
  <a href="https://deepwiki.com/emiliano-gandini-outeda/dbwarden/"><img src="https://img.shields.io/badge/DeepWiki-8A2BE2?logo=readthedocs&logoColor=white&style=for-the-badge" alt="DeepWiki"/></a>
</p>

<p align="center">
  <strong><a href="https://emiliano-gandini-outeda.me/DBWarden/">→ Full documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/emiliano-gandini-outeda/DBWarden">Source Code</a></strong>
</p>

---

DBWarden is a drop-in alternative to Alembic built for FastAPI: SQL-first migration files, async sessions wired directly into routes, and PostgreSQL round-trip fidelity out of the box.

## Key Features

- **SQL-first**: Migrations are plain SQL. No DSL, no generated abstraction layer.
- **Rollback included**: Every migration carries both upgrade and rollback SQL.
- **Schema snapshots**: After every migration, a checksummed JSON snapshot is written. These snapshots power rename detection, offline migration generation, and column-level diffing without querying the live database.
- **Column-level diffing**: Type, nullable, default, and comment changes generate precise `ALTER COLUMN` statements.
- **Rich index metadata**: Partial indexes (`WHERE`), covering indexes (`INCLUDE`), `USING` methods, `NULLS NOT DISTINCT`, column sort order, storage parameters, and ClickHouse skip indexes.
- **FastAPI-native sessions**: `session=primary.async_session` as a route annotation: no `Depends`, no `Annotated`, no `SessionDep`.
- **Single config source**: `database_config(...)` drives migrations, sessions, health checks, and seeds.
- **Dev mode**: Run SQLite locally against a PostgreSQL production schema with automatic SQL translation.
- **Multi-database**: One project, multiple databases, full isolation.
- **Sandbox & dry-run**: Test migrations in a temporary database or preview SQL without touching anything.
- **Observability**: Prometheus metrics (6 families), JSON logging, FastAPI routers for `/metrics`, `/status`, `/migrate`.
- **Versioned seeds**: SQL and Python seed files with checksummed idempotent application.
- **PostgreSQL first-class**: Reverse-engineer a live database with `generate-models`, feed into `make-migrations`: zero diff.
- **ClickHouse first-class**: Table options, replicated engines, dictionaries, materialized views, projections, skip indexes.

## Requirements

- Python 3.10+
- SQLAlchemy

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
from dbwarden import TableMeta
from dbwarden.schema import IndexSpec

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

## FastAPI Integration

### Lifespan

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

On startup, `dbwarden_lifespan` validates the schema (or auto-applies migrations). On shutdown, it disposes all engine pools.

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

Health router exposes readiness and liveness endpoints. DBWardenRouter exposes `GET /status` and `POST /migrate`.

---

## Auto-Generated Schemas

Decorate a model with `@auto_schema` to get Pydantic `CreateSchema` and `PublicSchema` for request validation and API responses:

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from dbwarden import TableMeta
from dbwarden.schema import auto_schema

Base = declarative_base()

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

api_result = user.to_schema()  # PublicSchema: excludes password_hash
```

`CreateSchema` derives required fields from nullable columns. `PublicSchema` omits fields with `public = False`. No separate schema definitions to maintain.

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
- Index options: `USING`, `WHERE`, `INCLUDE`, `WITH`, `NULLS NOT DISTINCT`, column sort order
- Named enum types with `ALTER TYPE ... ADD VALUE`
- Type normalization: `SERIAL`, `TIMESTAMPTZ`, `NUMERIC(p,s)`, `VARCHAR(n)`, `JSONB`, `UUID`, `ARRAY`, `TSTZRANGE`

---

## Observability

```python
from dbwarden.fastapi import MetricsRouter, MetricsMiddleware

app.include_router(MetricsRouter())
app.add_middleware(MetricsMiddleware)
```

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

Seeds are tracked in a `_dbwarden_seeds` table with checksums, making them idempotent.

---

## Generate Models

```bash
# One file per table:
dbwarden generate-models -d primary --tables users,orders

# Single file with ClickHouse engine metadata:
dbwarden generate-models -d clickhouse-db --clickhouse-engines --single-file
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
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/analytics",
    database_url_async="postgresql+asyncpg://user:pass@localhost:5432/analytics",
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
