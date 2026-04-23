# DBWarden

DBWarden is a SQL-first migration system for Python projects using SQLAlchemy.

It helps teams keep schema changes explicit, reviewable, and safe across development, staging, and production.

## Why Teams Use It

- Generate migration files from SQLAlchemy models
- Keep upgrade and rollback SQL in the same file
- Run migrations per database or across all configured databases
- Use migration locking to avoid concurrent execution issues
- Compare model schema and live database schema before deploying
- Use `--dev` mode to run local workflows on a separate development database

## 60-Second Workflow

```bash
# 1) Initialize project and config
dbwarden init

# 2) Generate SQL migration from models
dbwarden make-migrations "create users table"

# 3) Apply pending migrations
dbwarden migrate

# 4) Check current state
dbwarden status
```

## How It Works Internally

DBWarden executes a predictable pipeline:

1. Load database config from `warden.toml`
2. Resolve target database (`--database`, default, or `--all`)
3. Parse migration files and model metadata
4. Build SQL execution plan (versioned + repeatables)
5. Acquire migration lock
6. Execute SQL and write records in `dbwarden_migrations`
7. Release lock and print summary

High-level architecture:

```text
CLI (Typer)
  -> Commands
    -> Engine (parser/version/ordering/checksum/model discovery)
      -> Repositories (migration records + lock records)
        -> Database layer (SQLAlchemy connection + SQL execution)
```

## Learn by Path

- New users: [Installation](installation.md) -> [Quick Start](quickstart.md)
- Project setup: [Configuration](configuration.md)
- Daily usage: [Commands Overview](commands.md) and [CLI Reference](cli-reference.md)
- SQL behavior: [Migration Files](migration-files.md)
- Model behavior: [SQLAlchemy Models](models.md)
- Cross-dialect dev support: [SQL Translation](sql-translation.md)
- Operations and edge cases: [Advanced Features](advanced.md)

## Design Principles

- SQL is the source of truth
- Rollback is mandatory, not optional
- Multi-database support is first-class
- Local dev should be simple (`--dev` + SQLite recommended)
