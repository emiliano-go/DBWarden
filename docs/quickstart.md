# Quick Start

This guide walks you through a complete DBWarden workflow, from initial setup to managing database migrations.

## Prerequisites

- Python 3.10+ installed
- A database (PostgreSQL, MySQL, or SQLite)
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

## Step 3: Configure Database Connection

Create a `warden.toml` file:

```toml
sqlalchemy_url = "postgresql://user:password@localhost:5432/myapp"
async = false
```

For SQLite:

```toml
sqlalchemy_url = "sqlite:///./myapp.db"
```

## Step 4: Define Your SQLAlchemy Models

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

## Step 5: Initialize DBWarden

```bash
dbwarden init
```

Output:

```
Created configuration file: /home/user/myproject/warden.toml
DBWarden migrations directory created: /home/user/myproject/migrations

Next steps:
  1. Edit warden.toml with your database connection URL
  2. Run 'dbwarden make-migrations' to generate migrations from your models
```

## Step 6: Generate Migration from Models

```bash
dbwarden make-migrations "create users table"
```

Output:

```
Created migration file: /home/user/myproject/migrations/0001_create_users_table.sql
Tables included: users
```

## Step 7: Review the Migration

Check the generated SQL:

```sql
-- migrations/0001_create_users_table.sql

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
[INFO] Applying migration: 0001_create_users_table.sql
Migrations completed successfully: 1 migrations applied.
```

## Step 9: Check Migration Status

```bash
dbwarden status
```

Output:

```
Migration Status
================
✓ Applied   | 0001_create_users_table

Applied: 1
Pending: 0
Total: 1
```

## Step 10: View Migration History

```bash
dbwarden history
```

Output:

```
Migration History
=================
Version | Order | Description     | Applied At           | Type
-------|-------|-----------------|----------------------|------
0001   | 1     | create users    | 2024-02-15 14:30:15  | versioned
```

## Step 11: Add More Changes

Add a new table to your models:

```python
# models/post.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

Generate a new migration:

```bash
dbwarden make-migrations "create posts table"
dbwarden migrate
```

## Step 12: Rollback (If Needed)

Revert the last migration:

```bash
dbwarden rollback
```

Or rollback to a specific version:

```bash
dbwarden rollback --to-version 0001
```

## Step 13: Check Database Schema

Inspect your current database schema:

```bash
dbwarden check-db --out txt
```

Output:

```
Table: users
----------
  id: INTEGER PRIMARY KEY AUTOINCREMENT
  username: VARCHAR(50) NOT NULL UNIQUE
  email: VARCHAR(255) NOT NULL UNIQUE
  created_at: DATETIME NULL
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

## Next Steps

- Learn about [Migration Files](migration-files.md) structure
- Explore [Commands](commands.md) in detail
- Understand [SQLAlchemy Models](models.md) integration
- Check [Advanced Features](advanced.md) for more options
