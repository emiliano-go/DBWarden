# Configuration

DBWarden reads settings from `warden.toml` in the current directory or parent directories.

## Minimal Config

```toml
default = "primary"

[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
migrations_dir = "migrations/primary"
```

## Multi-Database Config

```toml
default = "primary"

[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
migrations_dir = "migrations/primary"

[database.analytics]
database_type = "clickhouse"
sqlalchemy_url = "clickhouse://user:password@localhost:8123/analytics"
migrations_dir = "migrations/analytics"
```

## Development Database Config

Recommended setup:

```toml
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
migrations_dir = "migrations/primary"

dev_database_type = "sqlite"
dev_database_url = "sqlite:///./development.db"
```

Use with:

```bash
dbwarden --dev migrate -d primary
```

## Field Reference

| Field | Required | Description |
|------|----------|-------------|
| `default` | yes | Default database name used when `-d` is omitted |
| `database.<name>.sqlalchemy_url` | yes | Primary DB URL |
| `database.<name>.database_type` | no | Explicit backend type, inferred from URL if omitted |
| `database.<name>.migrations_dir` | no | Migration folder, defaults to `migrations/<name>` |
| `database.<name>.model_paths` | no | List of model paths for auto-generation |
| `database.<name>.postgres_schema` | no | PostgreSQL search path override |
| `database.<name>.dev_database_url` | no | Dev DB URL used with `--dev` |
| `database.<name>.dev_database_type` | no | Dev backend type, inferred if omitted |

## Internal Loading Rules

DBWarden config loading pipeline:

```python
def get_database(name=None):
    cfg = get_multi_db_config()
    selected = cfg.databases[name or cfg.default]
    if is_dev_mode():
        return with_dev_url_and_type(selected)
    return selected
```

This means the same command code path works for production and dev mode; only active connection values switch.

## Validation Rules

DBWarden validates config aggressively to prevent dangerous mistakes.

1. `default` must exist in `[database.*]`
2. Every DB entry must have `sqlalchemy_url`
3. `dev_database_type` requires `dev_database_url`
4. URLs must be unique across primary and dev URLs
5. Physical DB targets must be unique (even if URLs differ by credentials)

Example invalid setup (same target DB):

```toml
[database.primary]
sqlalchemy_url = "postgresql://user1:pass1@localhost:5432/main"

[database.reporting]
sqlalchemy_url = "postgresql://user2:pass2@localhost:5432/main"
```

## SQL Translation Settings

When using `--dev` with SQLite, translation is enabled for backend-specific model SQL.

- Non-strict mode: unsupported conversions fallback to `TEXT` with warning
- Strict mode: fail on unsupported conversion

```bash
dbwarden --dev --strict-translation make-migrations "sync" -d primary
```

## Troubleshooting

`Database '<name>' not found`:

- Verify database key exists in `warden.toml`
- Verify `default` references an existing key

`has no dev_database_url configured` in `--dev` mode:

- Add `dev_database_url` for target database

Duplicate URL/target errors:

- Ensure each configured primary/dev DB points to a distinct physical target
