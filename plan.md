# Multi-Database Support Plan

## Implementation Status

**Status: ✅ Implemented**

All phases have been completed and all tests pass (75/75).

## Overview

This document outlines the implementation plan for adding multi-database support to DBWarden, allowing users to manage migrations for multiple databases from a single configuration.

## Goals

1. Allow multiple named databases in `warden.toml`
2. Each database has its own `sqlalchemy_url`, `model_paths`, and `migrations_dir`
3. CLI commands support `--database/-d` flag to target specific databases
4. `--all` flag to run operations on all databases
5. Separate migration directories per database
6. Database-specific migration history tracking

## Configuration Format

### New TOML Structure

```toml
# warden.toml
default = "primary"

[database.primary]
sqlalchemy_url = "postgresql://user:pass@localhost:5432/main"
postgres_schema = "public"
model_paths = ["./models/"]
migrations_dir = "migrations/primary"

[database.analytics]
sqlalchemy_url = "postgresql://user:pass@localhost:5432/analytics"
postgres_schema = "analytics_data"
model_paths = ["./analytics/models/"]
migrations_dir = "migrations/analytics"

[database.legacy]
sqlalchemy_url = "mysql://user:pass@localhost:3306/legacy"
model_paths = ["./legacy/models.py"]
migrations_dir = "migrations/legacy"
```

### Config Dataclasses

```python
@dataclass
class DatabaseConfig:
    sqlalchemy_url: str
    model_paths: list[str] | None = None
    migrations_dir: str = "migrations"
    postgres_schema: str | None = None

@dataclass
class MultiDbConfig:
    databases: dict[str, DatabaseConfig]
    default: str = "default"
```

## Implementation Phases

### Phase 1: Config System Refactor

**File:** `dbwarden/config.py`

**Changes:**
1. Replace `DbwardenConfig` with `DatabaseConfig` and `MultiDbConfig`
2. Add `get_database(name: str | None) -> DatabaseConfig` function
   - If `name` is None, return default database
   - If name doesn't exist, raise `ConfigurationError`
3. Add `get_multi_db_config() -> MultiDbConfig` function
4. Add `list_databases() -> list[str]` function
5. Remove legacy single-database format support

**Functions to add:**
```python
def get_database(name: str | None = None) -> DatabaseConfig:
    """Get database config by name or default."""

def get_multi_db_config() -> MultiDbConfig:
    """Get full multi-database config."""

def list_databases() -> list[str]:
    """List all configured database names."""
```

---

### Phase 2: Connection Layer

**Files:**
- `dbwarden/database/connection.py`
- `dbwarden/database/queries.py`
- `dbwarden/repositories/*.py`

**Changes:**

1. **`connection.py`:**
   - Update `get_db_connection(db_name: str | None = None)` to accept database name
   - Cache engines per database name
   - Update `get_engine()` similarly

2. **`queries.py`:**
   - Update `_get_backend_name()` to accept `db_name` parameter
   - Update `_get_queries_for_backend(db_name: str | None)` similarly

3. **Repositories:**
   - Update all repository classes to accept `db_name` parameter
   - Update method signatures in:
     - `repositories/migrations_repo.py`
     - `repositories/lock_repo.py`

---

### Phase 3: CLI Integration

**Files:**
- `dbwarden/cli/main.py`
- `dbwarden/commands/*.py`

**Changes:**

1. **Add `--database/-d` option to all database commands:**
   ```python
   @app.command()
   def migrate(database: str | None = Option(None, "--database", "-d", help="Target database name")):
       ...
   ```

2. **Add `--all` option for batch operations:**
   ```python
   @app.command()
   def migrate(all: bool = Option(False, "--all", help="Run on all databases")):
       ...
   ```

3. **Update commands:**
   - `init.py` - Create database-specific migration directories
   - `migrate.py` - Use database context
   - `make_migrations.py` - Use database-specific model paths
   - `rollback.py` - Use database context
   - `status.py` - Show per-database status
   - `diff.py` - Use database context

4. **New commands:**
   - `dbwarden database list` - List all configured databases

---

### Phase 4: Migration Discovery

**File:** `dbwarden/engine/version.py`

**Changes:**

1. Update `discover_migrations(migrations_dir: str)` to accept directory
2. Update all functions that reference `MIGRATIONS_DIR` constant
3. Migration history is tracked per-database (separate `dbwarden_migrations` table per DB)

---

### Phase 5: Model Discovery

**File:** `dbwarden/engine/model_discovery.py`

**Changes:**

1. Update `_get_backend_name(db_name: str | None)` to accept database name
2. Update `_map_sqlalchemy_type_to_backend(type_str, is_primary_key, db_name)`
3. Update `discover_models_in_directory` to use database-specific paths

---

### Phase 6: Lock Management

**File:** `dbwarden/engine/lock.py`

**Changes:**

1. Update `acquire_lock(db_name: str | None)` to accept database name
2. Lock is per-database (separate `dbwarden_lock` table per DB)

---

## CLI Commands Reference

### New Command Syntax

```bash
# Database management
dbwarden database add <name> --url "postgresql://..."
dbwarden database list
dbwarden database remove <name>

# Init - creates database-specific migration directories
dbwarden init --database primary

# Make migrations - generates SQL for specific database
dbwarden make-migrations -d primary
dbwarden make-migrations --database analytics

# Migrate - applies migrations to specific database
dbwarden migrate -d primary
dbwarden migrate --database analytics

# Migrate all databases sequentially
dbwarden migrate --all

# Rollback
dbwarden rollback -d primary --steps 1

# Status - shows status for specific database
dbwarden status -d primary
dbwarden status --all   # shows all databases

# Diff
dbwarden diff -d primary
```

---

## File Changes Summary

| File | Changes | Priority |
|------|---------|----------|
| `config.py` | New config structure, `get_database()`, `MultiDbConfig` | High |
| `database/connection.py` | Accept `db_name` parameter | High |
| `database/queries.py` | Pass db context to backend detection | High |
| `cli/main.py` | `--database` and `--all` options, database subcommand | High |
| `commands/init.py` | Create per-db migration dirs | High |
| `commands/migrate.py` | Database context | High |
| `commands/make_migrations.py` | Database-specific model paths, filename prefix | High |
| `commands/rollback.py` | Database context | Medium |
| `commands/status.py` | Per-db status | Medium |
| `commands/diff.py` | Database context | Medium |
| `commands/database.py` | New command for database management (add/list/remove) | High |
| `engine/version.py` | Database-specific migration dirs, filename prefix | High |
| `engine/model_discovery.py` | Per-db backend detection | High |
| `engine/lock.py` | Per-db locking | Medium |
| `repositories/migrations_repo.py` | Accept db_name | High |
| `repositories/lock_repo.py` | Accept db_name | Medium |

---

## Migration Guide

### Upgrading from Single-Database Config

Users with existing `warden.toml` must migrate to the new format:

**Before:**
```toml
sqlalchemy_url = "postgresql://..."
model_paths = ["./models/"]
```

**After:**
```toml
default = "default"

[database.default]
sqlalchemy_url = "postgresql://..."
model_paths = ["./models/"]
migrations_dir = "migrations"
```

### Directory Structure After Migration

```
project/
├── warden.toml
├── models/
│   └── ...
├── migrations/
│   ├── default/      # Default database migrations
│   │   ├── 0001_*.sql
│   │   └── 0002_*.sql
│   ├── analytics/    # Analytics database migrations
│   │   └── 0001_*.sql
│   └── legacy/       # Legacy database migrations
│       └── 0001_*.sql
```

---

## Backward Compatibility

- **NOT** maintaining backward compatibility
- Users must update their `warden.toml` to the new format
- Provide clear error messages for old format

---

## Testing Strategy

1. **Unit tests** for config parsing (multiple databases)
2. **Integration tests** for each command with `--database` flag
3. **End-to-end tests** for full migration workflow per database
4. **Sequential migration tests** for `--all` flag

---

## Implementation Order

1. `config.py` - New config structure
2. `database/connection.py` - Connection per database
3. `database/queries.py` - Backend detection per database
4. `engine/version.py` - Migration discovery per directory, filename prefix
5. `engine/model_discovery.py` - Per-db backend detection
6. `engine/lock.py` - Per-db locking
7. `repositories/*.py` - Repository updates
8. `commands/database.py` - Database management command (add/list/remove)
9. `commands/*.py` - CLI command updates
10. `cli/main.py` - Main CLI integration
11. Tests and documentation

---

## Open Questions

- [x] Should `--all` run migrations sequentially or in parallel? → **Sequentially**
- [x] Should we add a `dbwarden database add <name>` command? → **Yes**
- [x] Should migration filenames include database name prefix? → **Yes** (e.g., `primary__0001_create_users.sql`)
- [x] How to handle cross-database foreign keys? → **Not supported** - dbwarden manages one database at a time; users must handle cross-database relationships outside dbwarden

---

## Migration Filename Format

Migrations use database name prefix to avoid conflicts:

```
migrations/
├── primary/
│   ├── primary__0001_create_users.sql
│   └── primary__0002_add_email.sql
├── analytics/
│   └── analytics__0001_create_events.sql
└── legacy/
    └── legacy__0001_initial.sql
```

---

## New CLI Commands

### `dbwarden database add`

Add a new database to the configuration:

```bash
dbwarden database add <name> --url "postgresql://..." --migrations-dir "migrations/name"
```

Options:
- `--url` / `-u`: SQLAlchemy URL (required)
- `--model-paths` / `-m`: Model paths (optional)
- `--migrations-dir` / `-d`: Migration directory (optional, defaults to `migrations/<name>`)
- `--default`: Set as default database

### `dbwarden database list`

List all configured databases:

```bash
dbwarden database list
```

### `dbwarden database remove`

Remove a database from configuration:

```bash
dbwarden database remove <name>
```
