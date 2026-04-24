# Configuration

DBWarden uses Python configuration through `database_config(...)` calls.

This page shows all configuration options. For a step-by-step workflow, see the [Tutorial](tutorial/your-first-migration.md).

## Single database example

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    migrations_dir="migrations/primary",
)
```

## Multi-database example

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    model_paths=["app/models/api"],
)

database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url="clickhouse://user:password@localhost:8123/analytics",
    model_paths=["app/models/metrics"],
)
```

## Dev database example

```python
database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

Use with:

```bash
dbwarden --dev migrate --database primary
```

## Source resolution

DBWarden resolves config source in this order:

1. discovered `dbwarden.py`
2. full scan for files containing `database_config(...)`
3. `DBWARDEN_CONFIG_MODULE` environment variable

If more than one discovered source exists, DBWarden fails fast with an ambiguity error.

## Validation rules

- exactly one `default=True`
- duplicate database names are rejected
- duplicate URL/target collisions are rejected
- if more than one database is configured, `model_paths` is required on each
- overlapping `model_paths` require explicit `overlap_models=True`

## Secure display mode

Set `secure_values=True` when you want display commands to show variable expressions instead of resolved values for non-literal arguments.

```python
DATABASE_URL = "postgresql://..."

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url=DATABASE_URL,
    secure_values=True,
)
```

Reference: [Configuration API](reference/configuration-api.md)

## Next Steps in Your Workflow

Now that your configuration is set up, here's the recommended learning path:

### Generate your first migration

Now that DBWarden knows about your database, the next step is creating your first migration:

- [Your First Migration](tutorial/your-first-migration.md)

### Apply and manage migrations

Once migrations exist, learn how to run them safely:

- [Applying Migrations](tutorial/applying-migrations.md)
- [Rolling Back](tutorial/rolling-back.md)
- [Checking Status](tutorial/checking-status.md)

### Optimize your development loop

Use dev mode for fast local iterations:

- [Dev Mode](tutorial/dev-mode.md)

### Scale to multiple databases

If your project uses more than one database:

- [Multi-Database Setup](tutorial/multi-database-setup.md)

## Navigation

- Previous: [First Steps](getting-started/first-steps.md)
- Next: [Your First Migration](tutorial/your-first-migration.md)
