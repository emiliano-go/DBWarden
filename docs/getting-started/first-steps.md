---
description: 'Get started with DBWarden: initialize your project, define your database
  configuration, and learn the migration workflow from model changes to applied SQL.'
seo:
  title: First Steps - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/getting-started/first-steps
  robots: index,follow
  og:
    type: website
    title: First Steps - DBWarden Documentation
    description: 'Get started with DBWarden: initialize your project, define your
      database configuration, and learn the migration workflow from model changes
      to applied SQL.'
    url: https://dbwarden.emiliano-go.com/getting-started/first-steps
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: First Steps - DBWarden Documentation
    description: 'Get started with DBWarden: initialize your project, define your
      database configuration, and learn the migration workflow from model changes
      to applied SQL.'
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: 'Get started with DBWarden: initialize your project, define your database
    configuration, and learn the migration workflow from model changes to applied
    SQL.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: First Steps - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/getting-started/first-steps
    description: 'Get started with DBWarden: initialize your project, define your
      database configuration, and learn the migration workflow from model changes
      to applied SQL.'
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Get Started
      item: https://dbwarden.emiliano-go.com/getting-started
    - '@type': ListItem
      position: 2
      name: First Steps
      item: https://dbwarden.emiliano-go.com/getting-started/first-steps
seo_html: "<title>First Steps - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Get started with DBWarden: initialize your project, define your database\
  \ configuration, and learn the migration workflow from model changes to applied\
  \ SQL.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/getting-started/first-steps\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"First Steps - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Get started with DBWarden: initialize\
  \ your project, define your database configuration, and learn the migration workflow\
  \ from model changes to applied SQL.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/getting-started/first-steps\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"First Steps - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Get started with DBWarden: initialize your project, define your database\
  \ configuration, and learn the migration workflow from model changes to applied\
  \ SQL.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"First Steps - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/getting-started/first-steps\"\
  ,\n    \"description\": \"Get started with DBWarden: initialize your project, define\
  \ your database configuration, and learn the migration workflow from model changes\
  \ to applied SQL.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Get\
  \ Started\",\n        \"item\": \"https://dbwarden.emiliano-go.com/getting-started\"\
  \n      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n\
  \        \"name\": \"First Steps\",\n        \"item\": \"https://dbwarden.emiliano-go.com/getting-started/first-steps\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# First Steps

This walkthrough is the foundation of the DBWarden workflow.

The goal is not just to run commands, but to understand why each step exists and how it fits the migration lifecycle.

## Step 1: Initialize the project

```bash
$ dbwarden init
```

This creates:

- a migrations directory structure
- a Python configuration scaffold (`dbwarden.py`)

Why it matters: DBWarden expects a project-local migration layout and config source so migration behavior is deterministic per repository.

## Step 2: Define one explicit database entry

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app.models"],
    model_tables=["users"],
)
```

Why it matters: DBWarden resolves migration targets from explicit typed entries, not inferred environment state.

## Step 3: Add SQLAlchemy models

DBWarden uses model metadata to generate migration SQL. A minimal model example:

```python
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Why it matters: model metadata is the input to `make-migrations`.

## Step 4: Generate migration SQL

```bash
$ dbwarden make-migrations -d "create users table" --database primary
```

DBWarden creates a versioned SQL file under `migrations/primary/`.

Why it matters: this file is now part of your code review process and deployment artifact.

## Step 5: Review the generated migration

Open the file and validate both sections:

```sql
-- upgrade

-- rollback
```

Why it matters: rollback quality determines recovery quality.

## Step 6: Apply migrations

```bash
$ dbwarden migrate --database primary
```

During execution DBWarden:

1. resolves config and target database
2. acquires migration lock
3. executes pending SQL
4. stores migration record and checksum
5. releases lock

## Step 7: Verify the result

```bash
$ dbwarden status --database primary
$ dbwarden history --database primary
```

Use status to confirm pending/applied counts and history to confirm execution order.

## Common first-run issues

- `No configuration found`: ensure your project has one discovered config source with `database_config(...)`
- `Database '<name>' not found`: ensure `--database` matches configured `database_name`
- `No SQLAlchemy models found`: set `model_paths` explicitly in config

## Next Steps

- [Configuration](../configuration/index.md)
- [Your First Migration](first-migration.md)
- [Developing Locally](developing-locally.md)
