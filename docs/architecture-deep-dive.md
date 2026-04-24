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
4. compare against known schema state (database + migration history)
5. generate upgrade and rollback SQL
6. write migration file

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
