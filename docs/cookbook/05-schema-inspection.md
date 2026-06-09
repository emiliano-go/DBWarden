---
seo:
  title: 5. Schema Inspection - DBWarden Documentation
  description: 5. Schema Inspection What You'll Learn How to diff models against the
    live database How to capture DDL snapshots of individual tables How to reverseengineer
    models from a live database Prerequisites...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/05-schema-inspection/
  robots: index,follow
  og:
    type: website
    title: 5. Schema Inspection - DBWarden Documentation
    description: 5. Schema Inspection What You'll Learn How to diff models against
      the live database How to capture DDL snapshots of individual tables How to reverseengineer
      models from a live database Prerequisites...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/05-schema-inspection/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: 5. Schema Inspection - DBWarden Documentation
    description: 5. Schema Inspection What You'll Learn How to diff models against
      the live database How to capture DDL snapshots of individual tables How to reverseengineer
      models from a live database Prerequisites...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: 5. Schema Inspection - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/05-schema-inspection/
    description: 5. Schema Inspection What You'll Learn How to diff models against
      the live database How to capture DDL snapshots of individual tables How to reverseengineer
      models from a live database Prerequisites...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# 5. Schema Inspection

## What You'll Learn

- How to diff models against the live database
- How to capture DDL snapshots of individual tables
- How to reverse-engineer models from a live database

## Prerequisites

- Completed [Section 3](03-apply-and-inspect.md) (migrations applied)
- `examples/core/` project

## Step 1: Diff Models vs Database

```bash
cd examples/core
bash scripts/05-schema-inspection.sh
```

The key command:

```bash
dbwarden diff --database primary
```

`diff` compares your SQLAlchemy model definitions against the current database schema and reports any discrepancies:

```
Diff for 'primary':
  No differences found. Models and database are in sync.
```

If you add a column to a model without running `make-migrations`, `diff` would report:

```
Diff for 'primary':
  Table 'users':
    + bio (TEXT, nullable=True)    -- in model only
```

This is useful for catching drift before deployments.

## Step 2: Capture a DDL Snapshot

```bash
dbwarden snapshot users --database primary
```

The `snapshot` command captures the DDL for a specific table:

```sql
-- Snapshot of users at 2025-01-15 10:30:00
CREATE TABLE users (
    id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    UNIQUE (email),
    UNIQUE (username)
);
CREATE INDEX ix_users_created_at ON users (created_at);
```

Useful for:
- Documenting schema for code reviews
- Comparing schemas across environments
- Debugging migration issues

## Step 3: Reverse-Engineer Models

```bash
dbwarden generate-models -d primary --tables users,posts
```

This connects to the live database and generates SQLAlchemy model code:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=False, unique=True)
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(UTC))


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
```

This is the fastest way to bootstrap models from an existing database. You can review and annotate the output with `class Meta` afterward.

Options:
- `--tables users,posts` — limit to specific tables
- `--exclude-tables` — exclude tables by pattern
- `--single-file` — output all models in one file
- `--output ./models/` — write to a directory instead of stdout

## Key Takeaways

- `diff` detects drift between models and the live database
- `snapshot` captures table DDL for documentation or debugging
- `generate-models` reverse-engineers live tables into SQLAlchemy model code
- These three commands form your schema inspection toolkit

## Related Documentation

- [`diff` command](../commands/diff.md)
- [`snapshot` command](../commands/snapshot.md)
- [`generate-models` command](../commands/generate-models.md)
- [SQLAlchemy Models Reference](../models.md)

## Next

[Section 6: Safety & Impact Analysis](06-safety-impact.md)
