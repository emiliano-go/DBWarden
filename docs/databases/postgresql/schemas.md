# Schemas

**Handler**: `SchemaHandler` (PREAMBLE phase)

## Config-Level Schema

Set `pg_schema` in `database_config(...)` to set the connection's `search_path`:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/main",
    pg_schema="app",
)
```

All unqualified table references use this schema. The `_dbwarden_seeds` tracking table is created in the schema specified by `search_path`.

## Model-Level Schema

Set `pg_schema` on `PGTableMeta` or `PGViewMeta`:

```python
class Meta(PGTableMeta):
    pg_schema = "app"
```

When a model has `pg_schema`, all DDL references the fully qualified name (`app.users`). This takes precedence over the config-level `search_path`.

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE SCHEMA IF NOT EXISTS name;` |
| Drop | `DROP SCHEMA IF EXISTS name CASCADE;` |

## Extensions

Extensions are created during the PREAMBLE phase via `pg_extensions`:

```python
pg_extensions=["uuid-ossp", "pgcrypto"]
```

Generated DDL: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

## Code Seeds and Schema

Code seeds automatically qualify the table name with the model's `pg_schema`. If `User` has `pg_schema = "app"`, the seed INSERT becomes `INSERT INTO app.users (...) VALUES (...)`.
