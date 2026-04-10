# Multi-Database Support

## Summary

This PR adds comprehensive multi-database support to DBWarden, allowing users to manage migrations for multiple databases from a single configuration file.

## Features

### New Configuration Format

```toml
# warden.toml
default = "primary"

[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:pass@localhost:5432/main"
model_paths = ["./models/"]
migrations_dir = "migrations/primary"

[database.analytics]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:pass@localhost:5432/analytics"
migrations_dir = "migrations/analytics"
```

### Supported Database Types

- `sqlite`
- `postgresql`
- `mysql`
- `mariadb`

The `database_type` is automatically inferred from the URL if not specified.

### New CLI Commands

```bash
# Database management
dbwarden database list
dbwarden database add <name> --url "postgresql://..." --type postgresql
dbwarden database remove <name>

# Target specific database
dbwarden migrate -d primary
dbwarden make-migrations -d analytics
dbwarden status -d primary

# Run on all databases (sequentially)
dbwarden migrate --all
dbwarden status --all
```

### Migration File Naming

Each database has its own migration directory with prefixed filenames:

```
migrations/
├── primary/
│   └── primary__0001_create_users.sql
└── analytics/
    └── analytics__0001_create_events.sql
```

## Changes

- **Config**: New `DatabaseConfig` and `MultiDbConfig` dataclasses
- **Connection Layer**: `get_db_connection()` and `get_engine()` accept `db_name` parameter
- **Backend Detection**: Per-database backend type mapping (Postgres SERIAL, TIMESTAMP, etc.)
- **Migration Discovery**: Database-specific migration directories and prefixed filenames
- **Repositories**: Per-database migration history and locking
- **All Commands**: Updated to accept `--database`/`-d` option

## Breaking Changes

The `warden.toml` format has changed. Users must update their config to use the new `[database]` section format.

### Before
```toml
sqlalchemy_url = "postgresql://..."
model_paths = ["./models/"]
```

### After
```toml
default = "primary"
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://..."
model_paths = ["./models/"]
migrations_dir = "migrations/primary"
```

## Testing

All 75 existing tests pass. New tests added for multi-database config parsing.
