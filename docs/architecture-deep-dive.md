# Architecture Deep Dive

This page explains how DBWarden works internally across config loading, migration planning, SQL execution, and state tracking.

## Layered Architecture

```text
CLI (Typer)
  -> Commands layer
    -> Engine layer (planning/parsing/version/checksum/model discovery)
      -> Repository layer (migration + lock records)
        -> Database layer (SQLAlchemy connections + SQL execution)
```

Responsibilities:

- CLI: argument parsing and global flags (`--dev`, `--strict-translation`)
- Commands: orchestrate use cases (`migrate`, `rollback`, `make-migrations`)
- Engine: read migration files, resolve order, compute checksums, discover models
- Repositories: write/read migration and lock metadata
- Database: establish backend connection and execute SQL statements

## Config Resolution Pipeline

When a command needs a database config:

1. Locate `warden.toml` from current directory upward
2. Parse multi-database config
3. Select database (`-d` or default)
4. If `--dev` is enabled, swap active URL/type to dev fields
5. Validate uniqueness and consistency rules

Conceptual flow:

```python
def resolve_database(name=None):
    cfg = get_multi_db_config()
    selected = cfg.databases[name or cfg.default]
    if is_dev_mode():
        selected = apply_dev_overrides(selected)
    return selected
```

## Migration Execution Lifecycle

For `migrate`:

```text
1. Ensure metadata tables exist
2. Ensure lock table exists
3. Acquire lock
4. Read migration directory
5. Build pending plan (versioned + repeatable)
6. Execute SQL statements
7. Insert migration records/checksums
8. Release lock
```

Conceptual pseudocode:

```python
def migrate(db):
    create_migrations_table_if_not_exists(db)
    create_lock_table_if_not_exists(db)
    acquire_lock(db)
    try:
        plan = build_execution_plan(db)
        for migration in plan:
            run_sql(migration.upgrade_statements, db)
            record_execution(migration, db)
    finally:
        release_lock(db)
```

## Rollback Lifecycle

Rollback follows the same lock discipline as migrate, but executes rollback SQL from selected migration files in reverse order.

```python
def rollback(db, target):
    acquire_lock(db)
    try:
        applied = get_applied_migrations(db)
        to_rollback = select_target(applied, target)
        for migration in to_rollback:
            run_sql(migration.rollback_statements, db)
            remove_execution_record(migration, db)
    finally:
        release_lock(db)
```

## Model-to-SQL Generation Pipeline

`make-migrations` pipeline:

```text
1. Discover model paths
2. Import model modules
3. Extract table/column metadata
4. Detect existing schema (db + migration files)
5. Generate CREATE/ALTER SQL
6. Add rollback SQL
7. Write migration file
```

Conceptual pseudocode:

```python
def generate_migration(description, db):
    model_tables = discover_model_tables(db)
    known_schema = load_known_schema(db)
    diff = compare(model_tables, known_schema)
    upgrade, rollback = render_sql(diff, db)
    write_migration_file(description, upgrade, rollback, db)
```

## Repeatable Migration Logic

DBWarden supports:

- Versioned (`NNNN_`): run once by version ordering
- Runs always (`RA__`): run every migration execution
- Runs on change (`ROC__`): run only if checksum changed

For `ROC__`, DBWarden compares current file checksum with stored checksum to decide whether execution is needed.

## Checksum and Integrity

DBWarden computes checksums from SQL statements and stores them in `dbwarden_migrations`.

This enables:

- idempotent detection behavior
- repeatable migration update logic
- corruption/modification signals

## Concurrency Model

Migration mutating commands are serialized per database using lock state stored in DB tables.

If lock is stale:

- inspect via `dbwarden lock-status`
- recover via `dbwarden unlock`

## SQL Translation Path (Dev SQLite)

When using `--dev` and the target database resolves to SQLite:

1. Model column type/default is extracted
2. Translation attempts backend-compatible mapping
3. Unsupported conversions fallback to `TEXT` (default behavior) with warnings
4. If `--strict-translation` is enabled, fallback becomes an error

This behavior is used during SQL generation, not by rewriting migration files after generation.

## Error Propagation Strategy

- Validation errors are raised early at config/load phases
- Execution errors abort migration run and preserve failure context
- Lock release occurs in `finally` blocks to reduce deadlocks

## Extension Points

Current architecture naturally supports future additions such as:

- config providers from Python code (`set_config`, `--settings`)
- additional migration planners
- backend-specific SQL rendering modules
- observability hooks for command lifecycle events
