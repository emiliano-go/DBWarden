---
seo:
  title: 8. Multi-Database & Configuration - DBWarden Documentation
  description: 8. MultiDatabase & Configuration What You'll Learn How to configure
    multiple databases in one project How to target specific databases with CLI flags
    How to manage PostgreSQL + ClickHouse in the same...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/08-multi-database/
  robots: index,follow
  og:
    type: website
    title: 8. Multi-Database & Configuration - DBWarden Documentation
    description: 8. MultiDatabase & Configuration What You'll Learn How to configure
      multiple databases in one project How to target specific databases with CLI
      flags How to manage PostgreSQL + ClickHouse in the same...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/08-multi-database/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: 8. Multi-Database & Configuration - DBWarden Documentation
    description: 8. MultiDatabase & Configuration What You'll Learn How to configure
      multiple databases in one project How to target specific databases with CLI
      flags How to manage PostgreSQL + ClickHouse in the same...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: 8. Multi-Database & Configuration - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/08-multi-database/
    description: 8. MultiDatabase & Configuration What You'll Learn How to configure
      multiple databases in one project How to target specific databases with CLI
      flags How to manage PostgreSQL + ClickHouse in the same...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# 8. Multi-Database & Configuration

## What You'll Learn

- How to configure multiple databases in one project
- How to target specific databases with CLI flags
- How to manage PostgreSQL + ClickHouse in the same codebase
- How to use `dbwarden settings` for runtime configuration changes

## Prerequisites

- Docker (for PostgreSQL and ClickHouse containers)
- `examples/multi-database/` directory

## Scenario

A project with two databases:

- **primary** (PostgreSQL) — transactional user data
- **analytics** (ClickHouse) — page view events for analysis

## Step 1: The Configuration

```python
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/primary",
    database_url_async="postgresql+asyncpg://user:password@localhost:5432/primary",
    model_paths=["app.models.primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="http://localhost:8123/analytics",
    model_paths=["app.models.analytics"],
)
```

Key rules:
- Exactly one database must have `default=True` (used when `--database` is omitted)
- Each database must have separate `model_paths` (no overlap by default)
- Each database gets its own migration directory under `migrations/`

## Step 2: Start the Databases

```bash
cd examples/multi-database
docker compose up -d
```

## Step 3: Initialize and Migrate

```bash
dbwarden init
dbwarden migrate --all
```

This applies migrations to both databases in sequence. Each has its own lock, its own tracking table, and its own migration history.

## Step 4: Target a Specific Database

```bash
# Generate migrations for primary only
dbwarden make-migrations "add user table" --database primary

# Apply to analytics only
dbwarden migrate --database analytics

# Check status of one database
dbwarden status --database primary
```

## Step 5: Check Status of All Databases

```bash
dbwarden status --all
```

Output:

```
Database: primary
  Applied:  1
  Pending:  0
  Status:   up-to-date

Database: analytics
  Applied:  1
  Pending:  0
  Status:   up-to-date
```

## Step 6: Using `dbwarden settings`

The settings commands allow runtime configuration changes without editing `dbwarden.py` directly:

```bash
# View current configuration
dbwarden settings show --all

# Set a default database
dbwarden settings default-database primary

# Add a new database entry
dbwarden settings database-add reporting postgresql://localhost:5432/reporting \
    --type postgresql \
    --model-path app.models.reporting

# Remove a database
dbwarden settings database-remove reporting

# Rename a database
dbwarden settings database-rename analytics analytics_v2
```

Settings commands modify the `dbwarden.py` file directly using AST-based mutation. The changes are permanent and committed to version control.

## Step 7: Dev Mode with Multiple Databases

Each database can independently configure dev mode:

```python
primary = database_config(
    database_name="primary",
    database_type="postgresql",
    database_url_sync="postgresql://localhost/primary",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev_primary.db",
    model_paths=["app.models.primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="http://localhost:8123/analytics",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev_analytics.db",
    model_paths=["app.models.analytics"],
)
```

```bash
# Dev mode for all databases
dbwarden --dev migrate --all

# Dev mode for a specific database
dbwarden --dev migrate --database analytics
```

## Key Takeaways

- Multiple `database_config()` calls create independent database targets
- Each database has its own migration directory, lock, and history
- `--database` targets a specific database; `--all` targets every database
- `default=True` controls which database is used when `--database` is omitted
- `settings` commands modify `dbwarden.py` at runtime without manual editing
- Dev mode can be configured independently per database

## Related Documentation

- [Multi-Database Configuration](../configuration/multi-database.md)
- [Dev Mode](../configuration/dev-mode.md)
- [Settings Command](../commands/settings.md)

## Next

[Section 9: FastAPI Integration](09-fastapi-integration.md)
