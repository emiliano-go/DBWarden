# Commands Overview

DBWarden commands are organized by workflow: setup, generation, execution, inspection, and operations.

## Global Flags

| Flag | What it does |
|------|---------------|
| `--dev` | Use `dev_database_url` / `dev_database_type` for the selected database |
| `--strict-translation` | In dev SQLite flows, fail instead of fallback on lossy SQL translation |
| `-h`, `--help` | Show command help |

## Command Groups

## Setup

| Command | Purpose |
|---------|---------|
| [init](commands/init.md) | Initialize `warden.toml` and migration folder structure |
| [database](commands/database.md) | Add/list/remove configured databases |

## Migration Authoring

| Command | Purpose |
|---------|---------|
| [make-migrations](commands/make-migrations.md) | Generate SQL from SQLAlchemy models |
| [new](commands/new.md) | Create manual migration template |
| [squash](commands/squash.md) | Merge consecutive migrations |

## Migration Execution

| Command | Purpose |
|---------|---------|
| [migrate](commands/migrate.md) | Apply pending migrations |
| [rollback](commands/rollback.md) | Roll back applied migrations |

## Inspection and Diagnostics

| Command | Purpose |
|---------|---------|
| [status](commands/status.md) | Show applied/pending migration state |
| [history](commands/history.md) | Show execution history |
| [check-db](commands/check-db.md) | Inspect live database schema |
| [diff](commands/diff.md) | Compare models vs current schema |

## Lock Operations

| Command | Purpose |
|---------|---------|
| [lock-status](commands/lock.md) | Inspect migration lock state |
| [unlock](commands/lock.md) | Clear lock in recovery scenarios |

## Recommended Daily Flow

```bash
# 1) Generate migration
dbwarden make-migrations "add billing tables" -d primary

# 2) Review generated SQL file

# 3) Apply migration locally
dbwarden --dev migrate -d primary

# 4) Validate state
dbwarden status -d primary
```

## Multi-Database Execution Patterns

Single database:

```bash
dbwarden migrate -d primary
```

All databases in sequence:

```bash
dbwarden migrate --all
```

Dev mode on selected database:

```bash
dbwarden --dev migrate -d analytics
```

## How Execution Commands Work Internally

For `migrate` and `rollback`, DBWarden follows this algorithm:

```python
def execute_migration_operation(target_db):
    ensure_metadata_tables_exist(target_db)
    acquire_lock(target_db)
    try:
        plan = build_execution_plan(target_db)
        for step in plan:
            run_sql(step.statements)
            record_migration_event(step)
    finally:
        release_lock(target_db)
```

The lock guarantees only one migration process mutates a given database at a time.

## See Also

- [CLI Reference](cli-reference.md)
- [Migration Files](migration-files.md)
- [Advanced Features](advanced.md)
