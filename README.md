DBWarden is a SQL-first migration system for SQLAlchemy. It reads your models, generates plain SQL with rollback included, and tracks schema state through checksummed snapshots. No DSL. No live database needed to generate migrations. FastAPI integration, async sessions, observability, seeds, and impact analysis are all built in.

<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python">
  </a>
  <a href="https://pypi.org/project/dbwarden">
    <img src="https://img.shields.io/badge/PyPI-0.9.1-34D058?logo=pypi&logoColor=white&style=for-the-badge" alt="PyPI">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-10AC84?style=for-the-badge" alt="License">
  </a>
  <a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden/">
    <img src="https://img.shields.io/badge/DeepWiki-8A2BE2?logo=readthedocs&logoColor=white&style=for-the-badge" alt="DeepWiki">
  </a>
</p>

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
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from dbwarden import TableMeta, PgIndexSpec

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)

    class Meta(TableMeta):
        comment = "Core user accounts"
        indexes = [PgIndexSpec("ix_users_email", ["email"], unique=True)]
```

```bash
dbwarden make-migrations
dbwarden migrate
```

```sql
-- Generated SQL:
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE
);
CREATE UNIQUE INDEX ix_users_email ON users (email);
COMMENT ON TABLE users IS 'Core user accounts';
```

## PostgreSQL First-Class

```bash
dbwarden generate-models -d primary --tables users
dbwarden make-migrations
# Zero diff with live database
```

Identity columns, generated columns, collation, storage, compression, partitioning, exclusion constraints, deferrable FKs, and index options (`USING`, `WHERE`, `INCLUDE`, `NULLS NOT DISTINCT`, column sorting) via `PgIndexSpec`.

## ClickHouse First-Class

```bash
dbwarden generate-models -d analytics
dbwarden make-migrations
# Zero diff with live database
```

```python
from dbwarden import CHTableMeta, ChEngineSpec, ChIndexSpec

class Meta(CHTableMeta):
    ch_engine = ChEngineSpec("MergeTree")
    ch_order_by = ["event_date", "id"]
    ch_partition_by = "toYYYYMM(event_date)"
    ch_indexes = [ChIndexSpec("ix_payload", ["payload"], type="bloom_filter")]
```

ChEngineSpec, ProjectionSpec, ChIndexSpec for replicated engines, dictionaries, materialized views, projections, skip indexes, and codecs.

## FastAPI Integration

```python
from dbwarden.fastapi import dbwarden_lifespan, DBWardenHealthRouter

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(app, mode="check"):
        yield

app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Per-request sessions: `session=primary.async_session` on route params. No `Depends()`, no `Annotated`. Health router exposes `/liveness`, `/readiness`, and per-database health.

## Auto-Generated Pydantic Schemas

```python
from dbwarden.schema import auto_schema

@auto_schema
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255))
    password_hash = Column(String(255))

    class Meta:
        class password_hash:
            public = False

# User.CreateSchema, User.PublicSchema generated automatically.
# PublicSchema excludes password_hash and _prefixed fields.
```

## More

- **Offline migrations**: `export-models` then `make-migrations --offline` for CI with no database.
- **Impact analysis**: `dbwarden check-impact 0042` scans your codebase for affected references.
- **In-code seeds**: `@seed_data` decorator defines seeds alongside your models.
- **Observability**: Prometheus metrics, JSON logging, `QueryTracingMiddleware`, `PoolMetricsCollector`.
- **Multi-database**: One project with PostgreSQL, ClickHouse, MySQL, MariaDB, SQLite.
- **Dev mode**: `dbwarden --dev migrate` runs SQLite against a PostgreSQL schema with automatic translation.
- **Sandbox**: `dbwarden migrate --sandbox` applies in a temporary database.

## Documentation

Full docs at [emiliano-gandini-outeda.me/DBWarden/](https://emiliano-gandini-outeda.me/DBWarden/)

## License

MIT
