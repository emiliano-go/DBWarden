<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
    <em>The database toolkit for FastAPI. Lightweight, explicit, and built to stay out of your way.</em>
</p>
<p align="center">
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/v/dbwarden?color=%2334D058&label=pypi" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/dbwarden"><img src="https://img.shields.io/pypi/pyversions/dbwarden.svg?color=%2334D058" alt="Python versions"/></a>
  <a href="https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE"><img src="https://img.shields.io/github/license/emiliano-gandini-outeda/DBWarden?color=%2334D058" alt="License"/></a>
</p>

---

**Documentation**: [https://dbwarden.readthedocs.io](https://dbwarden.readthedocs.io)

**Source Code**: [https://github.com/emiliano-gandini-outeda/DBWarden](https://github.com/emiliano-gandini-outeda/DBWarden)

---

DBWarden is a database toolkit for FastAPI and SQLAlchemy projects.
It handles migrations, async sessions, startup validation, and health
checks — all from a single configuration source.

> **Experimental**: DBWarden is under active development.
> Breaking changes may occur between versions.

## Key Features

- **SQL-first**: Migrations are plain SQL. What you write is exactly what
  runs against your database. No DSL, no surprises.
- **Rollback included**: Every migration carries both upgrade and rollback
  SQL. Rolling back is a first-class operation, not an afterthought.
- **FastAPI-native**: Async session dependency, lifespan helpers, and a
  mountable health router designed around FastAPI's patterns.
- **One config, everything**: The same `database_config(...)` call that
  defines your migrations also drives your sessions and health checks.
  No split configs.
- **Dev mode**: Run SQLite locally against a PostgreSQL production schema.
  DBWarden translates the SQL automatically.
- **Multi-database**: Configure and migrate multiple databases from a
  single project, with full isolation and uniqueness guarantees.
- **Safe by default**: Migration locking, checksum integrity, collision
  detection, and schema drift checks before you deploy. DBWarden protects
  your database — from accidents and from itself.

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

## Quickstart

### 1. Configure

Run `dbwarden init` to scaffold your config file, then edit `dbwarden.py`:

```python
from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/myapp",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
)
```

### 2. Define your models

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
```

### 3. Generate a migration

```bash
dbwarden make-migrations "create users table"
```

DBWarden creates a versioned SQL file with both upgrade and rollback:

```sql
-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE
);

-- rollback

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

That's it. Your schema is versioned, reviewable, and reversible.

---

## FastAPI Integration

```python
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbwarden.fastapi import DBWardenHealthRouter, get_session, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")

SessionDep = Annotated[AsyncSession, Depends(get_session())]


@app.get("/users")
async def list_users(session: SessionDep):
    result = await session.execute(select(User))
    return result.scalars().all()
```

One config source. Sessions, health checks, and startup validation — handled.

---

## Multi-Database

```python
from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    model_paths=["models/primary"],
)

database_config(
    database_name="analytics",
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/analytics",
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
