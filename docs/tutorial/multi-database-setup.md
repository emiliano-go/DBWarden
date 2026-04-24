# Multi-Database Setup

DBWarden supports multiple databases from one config source.

## What you'll learn

- how to register more than one database
- required rules for model paths and defaults
- command patterns for one database vs all databases

## Example configuration

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:pass@localhost:5432/main",
    model_paths=["app/models/api"],
)

database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url="http://user:pass@localhost:8123/analytics",
    model_paths=["app/models/analytics"],
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

## Navigation

- Previous: [Dev Mode](dev-mode.md)
- Next: [Migration File Format](../migration-files.md)
