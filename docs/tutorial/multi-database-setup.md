# Multi-Database Setup

DBWarden supports multiple databases in one config source.

This is useful when one service owns operational and analytics stores, or when bounded contexts are split by database.

## Example

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
    database_url="clickhouse://user:pass@localhost:8123/analytics",
    model_paths=["app/models/analytics"],
)
```

## Rules to remember

- Exactly one entry must be `default=True`
- `model_paths` is required when more than one database is configured
- URL/target collisions are rejected
- `migrations_dir` defaults to `migrations/<database_name>`

## Why model paths are required in multi-db mode

Without explicit model boundaries, DBWarden cannot safely infer which tables belong to which database.

Use dedicated model path groups per database:

- API models -> `app/models/api`
- Analytics models -> `app/models/analytics`

If overlap is intentional, set `overlap_models=True` explicitly.

## Running commands

```bash
dbwarden migrate --database analytics
dbwarden migrate --all
```

## Operational recommendation

In CI/CD, run migrations for each database explicitly in a known order unless independent ordering is guaranteed.

## Navigation

- Previous: [Dev Mode](dev-mode.md)
- Next: [Migration File Format](../migration-files.md)
