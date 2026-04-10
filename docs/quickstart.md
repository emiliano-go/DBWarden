# Quick Start

This guide walks you through a complete DBWarden workflow, from initial setup to managing database migrations.

## Prerequisites

- Python 3.10+ installed
- A database (PostgreSQL, MySQL, SQLite, or ClickHouse)
- Basic familiarity with SQL and SQLAlchemy

## Step 1: Install DBWarden

```bash
pip install dbwarden
```

## Step 2: Create Your Project Structure

```
myproject/
├── warden.toml
├── models/
│   └── __init__.py
├── migrations/
└── app.py
```

## Step 3: Initialize DBWarden

```bash
dbwarden init
```

Output:

```
Created configuration file: /home/user/myproject/warden.toml
DBWarden migrations directory created: /home/user/myproject/migrations/default
```

## Step 4: Configure Database Connection

Edit the generated `warden.toml`:

```toml
default = "primary"

[database]
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/myapp"
migrations_dir = "migrations/primary"
```

For SQLite:

```toml
default = "primary"

[database]
[database.primary]
database_type = "sqlite"
sqlalchemy_url = "sqlite:///./myapp.db"
migrations_dir = "migrations/primary"
```

For ClickHouse:

```toml
default = "analytics"

[database]
[database.analytics]
database_type = "clickhouse"
sqlalchemy_url = "clickhouse://user:password@localhost:8123/analytics"
migrations_dir = "migrations/analytics"
```

## Step 5: Define Your SQLAlchemy Models

Create your models in the `models/` directory:

```python
# models/user.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

## Step 6: Generate Migration from Models

```bash
dbwarden make-migrations "create users table"
```

Output:

```
Created migration file: /home/user/myproject/migrations/primary/primary__0001_create_users.sql
Tables included: users
```

## Step 7: Review the Migration

Check the generated SQL:

```sql
-- migrations/primary/primary__0001_create_users.sql

-- upgrade

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME
)

-- rollback

DROP TABLE users
```

## Step 8: Apply the Migration

```bash
dbwarden migrate --verbose
```

Output:

```
[INFO] Applying migration: primary__0001_create_users.sql (version: 0001)
Migrations completed successfully: 1 migrations applied.
```

## Step 9: Check Migration Status

```bash
dbwarden status
```

Output:

```
 Migration Status - primary              
┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Status  ┃ Version ┃ Filename                   ┃
┡━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Applied │ 0001    │ primary__0001_create_users.sql │
└─────────┴─────────┴────────────────────────────────┘

Applied: 1
Pending: 0
Total: 1
```

## Multi-Database Support

### Adding More Databases

```bash
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"
dbwarden database list
```

Output:

```
Databases:
  primary (default) - postgresql://user:***@localhost:5432/myapp
    type: postgresql
    migrations: migrations/primary
  analytics - postgresql://user:***@localhost:5432/analytics
    type: postgresql
    migrations: migrations/analytics
```

### Migrating Specific Database

```bash
dbwarden migrate -d analytics
dbwarden status -d analytics
```

### Migrating All Databases

```bash
dbwarden migrate --all
```

## Common Workflows

### Daily Development

```bash
# 1. Make changes to your models
# 2. Generate migration
dbwarden make-migrations "describe your changes"

# 3. Apply migration
dbwarden migrate --verbose

# 4. Check status
dbwarden status
```

### Deploying to Production

```bash
# 1. Review pending migrations
dbwarden status

# 2. Apply with verbose to monitor
dbwarden migrate --verbose

# 3. Verify
dbwarden history
```

### Rolling Back a Bad Migration

```bash
# 1. Check history
dbwarden history

# 2. Rollback the last migration
dbwarden rollback

# 3. Or rollback to specific version
dbwarden rollback --to-version 0001
```

## Supported Databases

| Database | Type Value | Notes |
|----------|------------|-------|
| PostgreSQL | `postgresql` | SERIAL, TIMESTAMP, BYTEA |
| MySQL | `mysql` | AUTO_INCREMENT, ENUM |
| SQLite | `sqlite` | Built-in, no drivers |
| ClickHouse | `clickhouse` | Analytics, MergeTree |
| MariaDB | `mariadb` | MySQL-compatible |

## Next Steps

- Learn about [Migration Files](migration-files.md) structure
- Explore [Commands](commands.md) in detail
- Understand [SQLAlchemy Models](models.md) integration
- Check [Configuration](configuration.md) for all options
- Read [Supported Databases](databases.md) for database-specific features
