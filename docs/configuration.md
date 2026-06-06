# Configuration

DBWarden uses Python configuration through `database_config()` calls.
Each call registers a database and returns a `DatabaseHandle` whose
`.async_session` and `.sync_session` properties are FastAPI dependency
annotations.

## Single database

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

## Multiple databases

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

## Dev database

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

Use with the `--dev` flag:

```bash
dbwarden --dev migrate --database primary
```

## Config source resolution

DBWarden resolves the config source in this order:

1. discovered `dbwarden.py` in the project root
2. full scan for files containing `database_config(...)` calls
3. `DBWARDEN_CONFIG_MODULE` environment variable

If more than one source is found, DBWarden fails with an ambiguity error.

## Validation rules

- exactly one database must have `default=True`
- duplicate database names are rejected
- duplicate URL or target collisions are rejected
- `model_paths` is required when more than one database is configured
- overlapping `model_paths` requires explicit `overlap_models=True`

## Secure display mode

Set `secure_values=True` to show variable expressions instead of resolved
values in CLI display commands:

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

## Guides

- [Configuration overview](configuration/index.md) - landing page with links to all configuration topics
- [Quick start](configuration/quick-start.md)
- [Concepts](configuration/concepts.md)
- [Connection URLs](configuration/connection-urls.md)
- [Model discovery](configuration/model-discovery.md)
- [Dev mode](configuration/dev-mode.md)
- [Multi-database](configuration/multi-database.md)
- [Production patterns](configuration/production-patterns.md)
- [Troubleshooting](configuration/troubleshooting.md)
- [API reference](reference/configuration-api.md)
