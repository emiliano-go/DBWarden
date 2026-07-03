---
description: DBWarden is a SQL-first database migration system for Python and SQLAlchemy.
  Generate reviewable SQL migrations, validate them before production, and operate
  multiple databases from one config source.
---

<p align="center">
  <img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
  <strong style="font-size: 2.5em;">DBWarden</strong>
</p>
<p align="center">
  <em>The SQL-first database toolkit for SQLAlchemy.</em>
</p>
<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python">
  </a>
  <a href="https://pypi.org/project/dbwarden">
    <img src="https://img.shields.io/badge/PyPI-0.12.3-34D058?logo=pypi&logoColor=white&style=for-the-badge" alt="PyPI">
  </a>
  <a href="https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-10AC84?style=for-the-badge" alt="License">
  </a>
  <a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden/">
    <img src="https://img.shields.io/badge/DeepWiki-8A2BE2?logo=readthedocs&logoColor=white&style=for-the-badge" alt="DeepWiki">
  </a>
</p>

<p align="center">
  <strong><a href="https://dbwarden.emiliano-go.com/">Full documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/emiliano-gandini-outeda/DBWarden">Source Code</a></strong>
</p>

DBWarden is a SQL-first migration system for Python and SQLAlchemy projects.

It is built for teams that want schema changes to remain explicit, reviewable, and operationally safe, from local development to production.

## What DBWarden Does

- Generates migration files as plain SQL, with `-- upgrade` and `-- rollback` sections
- Reads SQLAlchemy models and backend-specific metadata from `class Meta`
- Supports PostgreSQL, MySQL, MariaDB, SQLite, and ClickHouse
- Manages one or many databases from one typed config source
- Adds safety tooling, schema diffing, seed tracking, status commands, and FastAPI integration

## The Core Workflow

DBWarden keeps the migration lifecycle simple:

1. Define your models.
2. Generate SQL from the model diff.
3. Review the SQL file.
4. Apply it with the CLI.
5. Verify the result with status and history commands.
6. Roll it back when you need to validate recovery.

## Install

```bash
uv add dbwarden
```

Optional groups:

```bash
uv add "dbwarden[fastapi,metrics,sandbox]"
```

## Quick Start

### Step 1: Configure a database

Create `dbwarden.py`:

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app.models"],
    model_tables=["users", "posts"],
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

### Step 2: Define your models

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

### Step 3: Generate a migration

```text
$ dbwarden make-migrations "create core tables" --database primary
Created migration: migrations/primary/primary__0001_create_core_tables.sql
```

### Step 4: Apply it

```text
$ dbwarden migrate --database primary
Applying migration: primary__0001_create_core_tables.sql
Migration applied successfully
```

### Step 5: Verify the state

```text
$ dbwarden status --database primary
Database: primary
Applied migrations: 1
Pending migrations: 0
```

## Why Teams Use It

- SQL remains the source of truth
- Rollback SQL is part of the workflow, not an afterthought
- Multi-database projects stay under one migration tool
- Safety tooling is built in, not bolted on later
- FastAPI projects can use the same config for sessions, health checks, and migration endpoints

## Requirements

- Python 3.12 or higher
- SQLAlchemy models for model-driven migration generation
- A supported backend: PostgreSQL, MySQL, MariaDB, SQLite, or ClickHouse

## Next Steps

- Start with [Features](features.md)
- Follow the guides in [Get Started](getting-started/setup.md)
- Explore [Cookbook & Examples](cookbook/index.md)
- Use [CLI Reference](cli-reference.md) as command lookup
