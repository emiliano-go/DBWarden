---
seo:
  title: Multi-Database Setup - DBWarden Documentation
  description: MultiDatabase Setup DBWarden supports multiple databases from one config
    source. What you'll learn how to register more than one database required rules
    for model paths and defaults command patterns...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/multi-database-setup/
  robots: index,follow
  og:
    type: website
    title: Multi-Database Setup - DBWarden Documentation
    description: MultiDatabase Setup DBWarden supports multiple databases from one
      config source. What you'll learn how to register more than one database required
      rules for model paths and defaults command patterns...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/multi-database-setup/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Multi-Database Setup - DBWarden Documentation
    description: MultiDatabase Setup DBWarden supports multiple databases from one
      config source. What you'll learn how to register more than one database required
      rules for model paths and defaults command patterns...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Multi-Database Setup - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/multi-database-setup/
    description: MultiDatabase Setup DBWarden supports multiple databases from one
      config source. What you'll learn how to register more than one database required
      rules for model paths and defaults command patterns...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Multi-Database Setup

DBWarden supports multiple databases from one config source.

## What you'll learn

- how to register more than one database
- required rules for model paths and defaults
- command patterns for one database vs all databases

## Example configuration

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/main",
    model_paths=["app.models.api"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="http://user:pass@localhost:8123/analytics",
    model_paths=["app.models.analytics"],
)
```

## Rules

- exactly one entry must set `default=True`
- if more than one database exists, each must define `model_paths`
- URL/physical target collisions are rejected
- `migrations_dir` defaults to `migrations/<database_name>`

## Run it

```bash
dbwarden migrate --database analytics
dbwarden migrate --all
dbwarden status --all
```

## Operational guidance

- run per-database migrations in explicit order if dependencies exist
- keep model boundaries clear per database
- use `overlap_models=True` only when overlap is intentional

See also: [Cookbook: Multi-Database](../cookbook/08-multi-database.md)

