---
description: Overview of DBWarden features, with short examples for migrations, safety
  checks, multi-database configs, FastAPI integration, seed management, and more.
seo:
  title: Features - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/features
  robots: index,follow
  og:
    type: website
    title: Features - DBWarden Documentation
    description: Overview of DBWarden features, with short examples for migrations,
      safety checks, multi-database configs, FastAPI integration, seed management,
      and more.
    url: https://dbwarden.emiliano-go.com/features
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Features - DBWarden Documentation
    description: Overview of DBWarden features, with short examples for migrations,
      safety checks, multi-database configs, FastAPI integration, seed management,
      and more.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Overview of DBWarden features, with short examples for migrations,
    safety checks, multi-database configs, FastAPI integration, seed management, and
    more.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Features - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/features
    description: Overview of DBWarden features, with short examples for migrations,
      safety checks, multi-database configs, FastAPI integration, seed management,
      and more.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
      logo: https://dbwarden.emiliano-go.com/assets/images/og-image.png
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Features
      item: https://dbwarden.emiliano-go.com/features
seo_html: "<title>Features - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Overview of DBWarden features, with short examples for migrations, safety\
  \ checks, multi-database configs, FastAPI integration, seed management, and more.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/features\">\n\
  <meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Features - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Overview of DBWarden features, with\
  \ short examples for migrations, safety checks, multi-database configs, FastAPI\
  \ integration, seed management, and more.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/features\">\n<meta property=\"og:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta property=\"\
  og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\" content=\"\
  768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\">\n<meta\
  \ property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Features - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Overview of DBWarden features, with\
  \ short examples for migrations, safety checks, multi-database configs, FastAPI\
  \ integration, seed management, and more.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Features - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/features\",\n    \"description\"\
  : \"Overview of DBWarden features, with short examples for migrations, safety checks,\
  \ multi-database configs, FastAPI integration, seed management, and more.\",\n \
  \   \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n\
  \    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano\
  \ Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Features\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/features\"\n      }\n    ]\n  }\n]\n</script>\n"
---

# Features

This page gives a compact overview of the main DBWarden features, with short examples. Use it to understand the surface area of the tool before diving into the guides and reference pages.

## SQL-First Migrations

DBWarden writes migrations as plain SQL files. Each file contains both an `--upgrade` section and a `--rollback` section.

```sql
-- upgrade
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE
);

-- rollback
DROP TABLE users;
```

This keeps schema changes reviewable in code review and runnable without hidden ORM magic.

## Typed Database Configuration

Configure one or many databases with explicit `database_config(...)` calls.

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app.models"],
    model_tables=["users", "posts", "comments"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="clickhouse://default:@localhost:8123/analytics",
    model_paths=["app.analytics_models"],
    model_tables=["events", "page_views"],
)
```

Each entry is validated before use, including database names, table names, `model_paths`, `model_tables`, and duplicate target detection.

## Model-Driven Migration Generation

DBWarden reads SQLAlchemy models, diffs them against the live schema or an offline model state, and emits SQL.

```text
$ dbwarden make-migrations "add posts table" --database primary
Created migration: migrations/primary/primary__0002_add_posts_table.sql
```

## Backend-Specific Metadata

PostgreSQL, MySQL/MariaDB, and ClickHouse support first-class metadata through `class Meta`.

PostgreSQL tables:

```python
from dbwarden.databases.pgsql import PGTableMeta, PGColumnMeta, pg


class Meta(PGTableMeta):
    pg_fillfactor = 80
    pg_schema = "app"

    class id(PGColumnMeta):
        pg = pg.field(identity="always")
```

PostgreSQL views and materialized views:

```python
from dbwarden.databases.pgsql import PGViewMeta


class Meta(PGViewMeta):
    pg_view_query = "SELECT id, email FROM users WHERE active = true"
    pg_view_materialized = False
    pg_schema = "app"
```

Set `pg_view_auto_refresh = True` for materialized views that need `REFRESH MATERIALIZED VIEW` on every migration cycle.

MySQL

```python
from dbwarden.databases.mysql import MyTableMeta, MyColumnMeta, my


class Meta(MyTableMeta):
    my_engine = "InnoDB"
    my_charset = "utf8mb4"

    class id(MyColumnMeta):
        my = my.field(unsigned=True)
```

ClickHouse example:

```python
from dbwarden.databases.clickhouse import CHTableMeta, ChEngineSpec, ChIndexSpec


class Meta(CHTableMeta):
    ch_engine = ChEngineSpec("MergeTree")
    ch_order_by = ["event_date", "id"]
    ch_indexes = [
        ChIndexSpec("ix_payload", ["payload"], type="bloom_filter", granularity=1),
    ]
```

## Safety Classification

Use `check` to classify changes before generating or applying SQL.

```text
$ dbwarden check --database primary
SAFE      add column users.bio
WARN      shrink varchar users.email
CRITICAL  drop table audit_log
```

Safety levels are `SAFE`, `INFO`, `WARN`, and `CRITICAL`.

## Read-Only Schema Diffing

Use `diff` when you want to inspect differences without writing migration files.

```bash
$ dbwarden diff --database primary
```

This is useful during reviews, debugging, and CI checks.

## Reverse-Engineering Models

Generate SQLAlchemy model code from a live database.

```bash
$ dbwarden generate-models --database primary --tables users,posts
```

This is useful when adopting DBWarden in an existing project, documenting an inherited schema, or recovering model definitions.

## Offline Migrations

DBWarden can generate migrations without connecting to a live database, by diffing current models against an exported model state.

```bash
$ dbwarden export-models --database primary
$ dbwarden make-migrations "offline change" --offline --database primary
```

This is useful for CI pipelines and restricted environments.

## Multi-Database Workflows

Manage multiple backends from one repository, each with its own migration directory and model set.

```bash
$ dbwarden migrate --database primary
$ dbwarden migrate --database analytics
```

You can also show status across all configured databases:

```bash
$ dbwarden status --all
```

## Dev Mode

Use `--dev` to point a configured database at a separate development target.

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

```bash
$ dbwarden --dev make-migrations "test locally" --database primary
$ dbwarden --dev migrate --database primary
```

## Seed Management

DBWarden tracks SQL and Python seed files separately from schema migrations.

```bash
$ dbwarden seed create "load countries" --type sql --database primary
$ dbwarden seed apply --database primary
$ dbwarden seed list --database primary
```

This is useful for reference data, lookup tables, and repeatable environment setup.

## FastAPI Integration

`database_config(...)` returns a `DatabaseHandle` that can be used directly in FastAPI dependencies.

```python
from fastapi import APIRouter
from .dbwarden import primary


router = APIRouter()


@router.get("/users")
async def list_users(session: primary.async_session):
    ...
```

This gives one shared source of truth for migrations, runtime connections, and session injection.

## Sandbox Testing

Apply migrations in a temporary sandbox database before applying them for real.

```bash
$ dbwarden migrate --sandbox --database primary
```

This is useful when validating generated SQL against a throwaway environment.

## Status, History, and Rollback

DBWarden includes built-in commands for operational visibility.

```bash
$ dbwarden status --database primary
$ dbwarden history --database primary
$ dbwarden rollback --count 1 --database primary
```

These commands make the migration lifecycle inspectable and reversible.

## Next Steps

- Follow [Get Started](getting-started/setup.md)
- Explore [Cookbook & Examples](cookbook/index.md)
- Use [CLI Reference](cli-reference.md) for command lookup
