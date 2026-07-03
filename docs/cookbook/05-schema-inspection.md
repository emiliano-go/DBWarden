---
seo:
  title: 5. Schema Inspection - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection
  robots: index,follow
  og:
    type: website
    title: 5. Schema Inspection - DBWarden Documentation
    description: Schema inspection allows you to compare your SQLAlchemy model definitions
      against the live database, capture DDL snapshots of individual tables, and...
    url: https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: 5. Schema Inspection - DBWarden Documentation
    description: Schema inspection allows you to compare your SQLAlchemy model definitions
      against the live database, capture DDL snapshots of individual tables, and...
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Schema inspection allows you to compare your SQLAlchemy model definitions
    against the live database, capture DDL snapshots of individual tables, and...
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: 5. Schema Inspection - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection
    description: Schema inspection allows you to compare your SQLAlchemy model definitions
      against the live database, capture DDL snapshots of individual tables, and...
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Cookbook & Examples
      item: https://dbwarden.emiliano-go.com/cookbook
    - '@type': ListItem
      position: 2
      name: 05 Schema Inspection
      item: https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection
seo_html: "<title>5. Schema Inspection - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Schema inspection allows you to compare your SQLAlchemy\
  \ model definitions against the live database, capture DDL snapshots of individual\
  \ tables, and...\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"5. Schema Inspection - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Schema inspection\
  \ allows you to compare your SQLAlchemy model definitions against the live database,\
  \ capture DDL snapshots of individual tables, and...\">\n<meta property=\"og:url\"\
  \ content=\"https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection\">\n\
  <meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"5. Schema Inspection - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Schema inspection allows you to compare your SQLAlchemy model definitions\
  \ against the live database, capture DDL snapshots of individual tables, and...\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"5. Schema Inspection - DBWarden\
  \ Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection\"\
  ,\n    \"description\": \"Schema inspection allows you to compare your SQLAlchemy\
  \ model definitions against the live database, capture DDL snapshots of individual\
  \ tables, and...\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Cookbook\
  \ & Examples\",\n        \"item\": \"https://dbwarden.emiliano-go.com/cookbook\"\
  \n      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n\
  \        \"name\": \"05 Schema Inspection\",\n        \"item\": \"https://dbwarden.emiliano-go.com/cookbook/05-schema-inspection\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# 5. Schema Inspection

Schema inspection allows you to compare your SQLAlchemy model definitions against the live database, capture DDL snapshots of individual tables, and reverse-engineer models from an existing database.

For complete documentation see the [`diff`](../commands/diff.md), [`snapshot`](../commands/snapshot.md), and [`generate-models`](../commands/generate-models.md) command references.

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
$ dbwarden diff --database primary
```

`diff` compares your SQLAlchemy model definitions against the current database schema and reports any discrepancies:

```
No differences found between models and database.
```

If you add a column to a model without running `make-migrations`, `diff` would report a schema diff table:

```
Schema Diff
┌───────────┬───────┬────────┬──────────┐
│ Operation │ Table │ Target │ Severity │
├───────────┼───────┼────────┼──────────┤
│ add_column│ users │  bio   │ INFO     │
└───────────┴───────┴────────┴──────────┘
Total changes: 1
```

This is useful for catching drift before deployments.

## Step 2: Capture a DDL Snapshot

```bash
$ dbwarden snapshot users --database primary
```

The `snapshot` command captures the DDL for a specific table:

```sql
CREATE TABLE users (
    id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (email),
    UNIQUE (username)
);

-- Indexes:
CREATE INDEX ix_users_created_at ON users (created_at);
```

Useful for:
- Documenting schema for code reviews
- Comparing schemas across environments
- Debugging migration issues

## Step 3: Reverse-Engineer Models

```bash
$ dbwarden generate-models -d primary --tables users,posts
```

This connects to the live database and generates SQLAlchemy model code:

```python
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

This is the fastest way to bootstrap models from an existing database. You can review and annotate the output with `class Meta` afterward.

Options:
- `--tables users,posts`: limit to specific tables
- `--exclude-tables`: exclude tables by pattern
- `--single-file`: output all models in one file
- `--output ./models/`: write to a directory instead of stdout

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
