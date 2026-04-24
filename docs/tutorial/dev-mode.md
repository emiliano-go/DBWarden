# Dev Mode

Dev mode runs commands against `dev_database_url`/`dev_database_type` instead of production-targeted values.

## What you'll learn

- how `--dev` swaps active database settings
- how to configure dev database fields
- when to use `--strict-translation`

## Prerequisites

- database entry includes `dev_database_url`
- optionally `dev_database_type`

## Configure it

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

## Run it

```bash
dbwarden --dev make-migrations "sync models" --database primary
dbwarden --dev migrate --database primary
```

Strict translation mode:

```bash
dbwarden --dev --strict-translation make-migrations "validate" --database primary
```

## Common failure modes

- `--dev` without `dev_database_url`
- relying on backend-specific SQL features unavailable in SQLite
- ignoring strict translation errors in CI workflows

Reference: [SQL Translation](../sql-translation.md)

## Navigation

- Previous: [Checking Status](checking-status.md)
- Next: [Multi-Database Setup](multi-database-setup.md)
