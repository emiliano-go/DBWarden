# Configuration

!!! note "Documentation Reorganized"
    The configuration documentation has been reorganized into a comprehensive guide. This page now redirects to the new structure.

##  New Documentation Structure

The configuration documentation is now organized into:

- **[Getting Started](configuration/index.md)** - Landing page with overview
- **[Quick Start](configuration/quick-start.md)** - Your first configuration in 2 minutes
- **[Concepts](configuration/concepts.md)** - How configuration works
- **[Connection URLs](configuration/connection-urls.md)** - Database URL formats
- **[Model Discovery](configuration/model-discovery.md)** - How `model_paths` works
- **[Dev Mode](configuration/dev-mode.md)** - Local development patterns
- **[Multi-Database](configuration/multi-database.md)** - Multiple databases
- **[Production Patterns](configuration/production-patterns.md)** - Real-world examples
- **[Troubleshooting](configuration/troubleshooting.md)** - Common issues
- **[API Reference](reference/configuration-api.md)** - Complete function signature

##  Quick Links

### New to DBWarden Configuration?
Start here: **[Quick Start](configuration/quick-start.md)**

### Looking for Specific Information?

| Need | Go To |
|------|-------|
| First configuration | **[Quick Start](configuration/quick-start.md)** |
| Understand how it works | **[Concepts](configuration/concepts.md)** |
| Database URL formats | **[Connection URLs](configuration/connection-urls.md)** |
| Model discovery | **[Model Discovery](configuration/model-discovery.md)** |
| Dev mode setup | **[Dev Mode](configuration/dev-mode.md)** |
| Multiple databases | **[Multi-Database](configuration/multi-database.md)** |
| Production examples | **[Production Patterns](configuration/production-patterns.md)** |
| Fix configuration errors | **[Troubleshooting](configuration/troubleshooting.md)** |
| Complete parameter list | **[API Reference](reference/configuration-api.md)** |

---

**[ Go to Configuration Home](configuration/index.md)**

---

## Quick Reference (Legacy)

DBWarden uses Python configuration through `database_config(...)` calls.

For complete documentation, see the [Configuration Guide](configuration/index.md).

## Single database example

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    migrations_dir="migrations/primary",
)
```

## Multi-database example

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app/models/api"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="clickhouse://user:password@localhost:8123/analytics",
    model_paths=["app/models/metrics"],
)
```

## Dev database example

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

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=DATABASE_URL,
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
