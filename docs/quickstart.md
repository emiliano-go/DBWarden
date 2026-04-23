# Quick Start

This guide takes you from zero to a working migration flow in about 10 minutes.

## 1) Install

```bash
pip install dbwarden
```

## 2) Initialize Project

From your project root:

```bash
dbwarden init
```

This creates `warden.toml` and a `migrations/` directory.

## 3) Configure Databases

Minimal single-database config:

```toml
default = "primary"

[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
migrations_dir = "migrations/primary"
```

Recommended local dev config (separate dev DB):

```toml
default = "primary"

[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
migrations_dir = "migrations/primary"

dev_database_type = "sqlite"
dev_database_url = "sqlite:///./development.db"
```

## 4) Add SQLAlchemy Models

```python
# models/user.py
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base
import datetime as dt

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
```

## 5) Generate Migration

```bash
dbwarden make-migrations "create users table" -d primary
```

DBWarden creates a file like:

```text
migrations/primary/primary__0001_create_users_table.sql
```

## 6) Review Generated SQL

Every migration has explicit `-- upgrade` and `-- rollback` sections.

```sql
-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME
);

-- rollback

DROP TABLE users;
```

## 7) Apply Migration

Production-like target:

```bash
dbwarden migrate -d primary
```

Local dev target:

```bash
dbwarden --dev migrate -d primary
```

## 8) Check State

```bash
dbwarden status -d primary
dbwarden history -d primary
```

## What Happens Internally

On `migrate`, DBWarden:

1. Loads config and resolves target DB
2. Creates migration metadata/lock tables if missing
3. Acquires migration lock
4. Parses pending files and executes statements
5. Stores applied records and checksums
6. Releases lock

This is why migration state stays deterministic across environments.

## Next Steps

- [Configuration](configuration.md)
- [Commands Overview](commands.md)
- [Migration Files](migration-files.md)
- [SQL Translation](sql-translation.md)
