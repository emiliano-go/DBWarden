---
description: Define your first SQLAlchemy models, generate a migration, review the generated SQL, apply it, verify the result, and roll it back.
seo:
  title: Your First Migration - DBWarden Documentation
  description: Define your first SQLAlchemy models, generate a migration, review the generated SQL, apply it, verify the result, and roll it back.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/getting-started/first-migration/
  robots: index,follow
  og:
    type: website
    title: Your First Migration - DBWarden Documentation
    description: Define your first SQLAlchemy models, generate a migration, review the generated SQL, apply it, verify the result, and roll it back.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/getting-started/first-migration/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Your First Migration - DBWarden Documentation
    description: Define your first SQLAlchemy models, generate a migration, review the generated SQL, apply it, verify the result, and roll it back.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Your First Migration - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/getting-started/first-migration/
    description: Define your first SQLAlchemy models, generate a migration, review the generated SQL, apply it, verify the result, and roll it back.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Your First Migration

This guide walks through the core DBWarden workflow: define models, generate SQL, apply the migration, inspect the result, and roll it back.

## Create the Models

Create `app/models.py`:

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase
from dbwarden import IndexSpec, TableMeta


class Base(DeclarativeBase):
    pass


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

## Generate the Migration

Run:

```text
$ dbwarden make-migrations "create core tables" --database primary
Created migration: migrations/primary/primary__0001_create_core_tables.sql
```

DBWarden compares your current models against the live schema, or snapshot state, and writes a new SQL migration file.

## Review the Generated SQL

Open the new file. It will look roughly like this:

```sql
-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    bio TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_posts_created_at ON posts (created_at);

-- rollback

DROP INDEX IF EXISTS ix_posts_created_at;
DROP TABLE posts;
DROP TABLE users;
```

The exact SQL depends on the backend, but the structure is always the same:

- `-- upgrade` contains the forward change
- `-- rollback` contains the reverse change

## Apply the Migration

Run:

```text
$ dbwarden migrate --database primary
Applying migration: primary__0001_create_core_tables.sql
Migration applied successfully
```

Internally, DBWarden resolves the config, acquires the migration lock, executes the upgrade SQL, records the checksum, and releases the lock.

## Verify the Result

Run:

```text
$ dbwarden status --database primary
Database: primary
Applied migrations: 1
Pending migrations: 0
$ dbwarden history --database primary
1  primary__0001_create_core_tables.sql  applied
```

Use `status` to see the current state of the migration queue. Use `history` to see what has been applied and in what order.

You can also inspect the live schema directly:

```bash
dbwarden check-db --database primary
```

This is useful when you want a read-only view of what the database currently contains.

## Roll Back the Migration

Run:

```text
$ dbwarden rollback --count 1 --database primary
Rolling back migration: primary__0001_create_core_tables.sql
Rollback completed successfully
```

After that, the database is back to its previous schema state.

## Step by Step

### Step 1: Define the Base Class

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

DBWarden does not export a shared `Base`. You define a local SQLAlchemy declarative base in your project.

### Step 2: Define the Models

```python
class User(Base):
    __tablename__ = "users"
```

Every model maps to a table. Columns come from normal SQLAlchemy field declarations. Table-level migration metadata lives in `class Meta`.

### Step 3: Add Table Metadata

```python
class Meta(TableMeta):
    comment = "Core user accounts"
```

`TableMeta` is the cross-database surface for comments, indexes, checks, and unique constraints.

### Step 4: Generate SQL

```bash
dbwarden make-migrations "create core tables" --database primary
```

This command inspects the configured models, compares them with the current schema, and emits a SQL file. The file becomes part of your normal code review and deployment workflow.

### Step 5: Review Upgrade and Rollback

Every migration file contains both directions. This is one of DBWarden's core design choices: a migration is not complete until the rollback exists.

### Step 6: Apply the Migration

```bash
dbwarden migrate --database primary
```

This executes pending migrations in order and records them in the migration table.

### Step 7: Verify the State

```bash
dbwarden status --database primary
dbwarden history --database primary
```

Verification is part of the workflow, not optional cleanup.

### Step 8: Roll It Back

```bash
dbwarden rollback --count 1 --database primary
```

Rolling back the first migration confirms that the file contains valid reverse SQL, not just valid forward SQL.

## Manual Migrations

Not every schema or data change should be auto-generated. When the change is not model-driven, create a manual migration file:

```bash
dbwarden new "manual hotfix" --database primary
```

Use manual migrations for cases like:

- data backfills
- type changes that require custom `USING` expressions
- backend-specific operations that need hand-written SQL

DBWarden will track these files the same way it tracks generated migrations.

## Recap

You have:

- defined SQLAlchemy models
- generated a SQL migration file
- reviewed its upgrade and rollback sections
- applied the migration
- verified the result
- rolled it back successfully

Next, continue with [Developing Locally](developing-locally.md).
