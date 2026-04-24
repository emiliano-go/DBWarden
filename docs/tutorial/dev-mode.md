# Dev Mode

Dev mode lets you run migration workflows against `dev_database_url` instead of the primary URL.

This gives fast local feedback while keeping production-targeted config in the same source.

## Run commands in dev mode

```bash
dbwarden --dev migrate --database primary
dbwarden --dev make-migrations -d "sync models" --database primary
```

When `--dev` is enabled, DBWarden swaps active connection values to `dev_database_url` and `dev_database_type` for the selected database.

## Configure dev database

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:pass@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

If `--dev` is used without `dev_database_url`, DBWarden fails fast.

## Strict translation mode

```bash
dbwarden --dev --strict-translation make-migrations -d "validate" --database primary
```

Use strict mode in CI or release-prep checks to catch lossy translation early.

## Typical team pattern

1. local iterations with `--dev` (SQLite)
2. pre-merge validation on production-like database
3. deploy with standard `migrate --database <name>`

Reference: [SQL Translation](../sql-translation.md)

## Navigation

- Previous: [Checking Status](checking-status.md)
- Next: [Multi-Database Setup](multi-database-setup.md)
