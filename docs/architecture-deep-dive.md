# Architecture

This page explains DBWarden internals for contributors and advanced debugging.

## Layered architecture

```text
CLI (Typer)
  -> Commands layer
    -> Engine layer (planning/parsing/version/checksum/model discovery)
      -> Repository layer (migration + lock records)
        -> Database layer (SQLAlchemy connection + SQL execution)
```

## Responsibilities

- CLI: parse args, global flags (`--dev`, `--strict-translation`)
- Commands: orchestrate workflows (`migrate`, `rollback`, `make-migrations`)
- Engine: parse files, resolve ordering, checksums, model discovery
- Repositories: read/write migration and lock metadata
- Database: execute SQL with backend-aware connections

## Configuration resolution pipeline

When runtime config is requested:

1. discover one config source (`dbwarden.py` or single callsite)
2. fallback to `DBWARDEN_CONFIG_MODULE` when configured
3. import source and execute `database_config(...)` calls
4. validate uniqueness/default/model-path rules
5. resolve selected database and apply `--dev` swap when enabled

Ambiguous sources fail fast.

## Migration execution lifecycle

For `migrate`:

1. ensure migrations metadata table exists
2. ensure lock table exists
3. acquire lock
4. build pending execution plan
5. execute SQL statements
6. record migration metadata/checksums
7. release lock

## Rollback lifecycle

Rollback uses the same lock discipline, selecting rollback SQL from applied files in reverse order.

## Model-to-SQL generation lifecycle

`make-migrations` pipeline:

1. discover model paths
2. import model modules
3. extract table/column metadata
4. load latest schema snapshot (`dbwarden/schemas/*.schema.json`) if one exists
5. if snapshot exists: **snapshot-diff path**
   - diff model tables against snapshot tables
   - auto-detect column renames from dropped↔added pairs of the same type
   - apply user `--rename` flags and/or interactive prompts to confirm renames
   - emit `RENAME COLUMN` (confirmed) or `DROP` + `ADD` (not confirmed)
   - generate upgrade and rollback SQL from the ops
6. if no snapshot: **live-DB fallback path**
   - extract known columns from database + existing migration files
   - compare model columns against known columns
   - emit `CREATE TABLE` / `ADD COLUMN` only (no rename detection)
7. deduplicate against existing migration statements
8. write migration file
9. write companion `.plan.json` metadata file (with `resolved_from` on rename ops)

### Snapshot write lifecycle (in `migrate`)

After applying versioned migrations, `migrate` calls `_write_migration_snapshot()`:

1. connect to database (respecting sandbox override)
2. extract full schema: tables, columns, types, indexes, constraints, enums
3. compute SHA-256 checksum
4. write `<migration_id>.schema.json` to `dbwarden/schemas/`
5. on failure: log warning (non-blocking)

Snapshots are not written during `--dry-run`, `--sandbox`, or for repeatable migrations.

## Repeatable migration model

Supported classes:

- versioned (`NNNN_`): run once in ordered sequence
- runs always (`RA__`): run each migrate execution
- runs on change (`ROC__`): run only when checksum changes

## Integrity model

Checksums are recorded for migration content and used for:

- repeatable migration change detection
- migration consistency checks
- audit/debug confidence

## Concurrency model

Migration-mutating commands are serialized by lock state stored in database tables.

Recovery commands:

- `dbwarden lock-status`
- `dbwarden unlock`

## Dev translation path

With `--dev` and SQLite target:

1. extract model types/defaults
2. translate backend-specific constructs
3. fallback behavior in non-strict mode
4. fail-fast behavior with `--strict-translation`

Translation happens during SQL generation, not by mutating existing migration files.

## Error propagation strategy

- config/load validation errors fail early
- execution errors abort current run with context
- lock release is guarded in cleanup paths
