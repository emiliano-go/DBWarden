# DBWarden

DBWarden is a SQL-first migration system for Python + SQLAlchemy projects.

It is built for teams that want migration changes to stay explicit, reviewable, and safe from local development to production.

## What DBWarden Is

- A migration workflow centered on SQL files you can review
- A CLI for generating, applying, rolling back, and auditing migrations
- A multi-database migration tool with lock and checksum safety built in

## What DBWarden Is Not

- An ORM replacement
- A hidden auto-migration engine that mutates schema silently
- A deployment platform

## Key Features

- Explicit `--upgrade` and `--rollback` SQL sections in every migration
- Multi-database support from one config source
- Dev mode (`--dev`) with optional SQLite translation workflow
- Locking and checksum integrity checks
- Status/history visibility for release and incident workflows
- Seed data management with SQL and Python seed files
- Prometheus metrics and structured JSON logging
- FastAPI integration: session dependencies, health endpoints, migration/status routes, metrics endpoint
- Distributed migration locking via Redis
- Sandbox mode for safe migration testing
- Dry-run mode to preview changes without applying
- Sync and async URL split for CLI and FastAPI sessions
- Schema snapshots for offline migration generation and intelligent column rename detection

## Requirements

- Python 3.10+
- SQLAlchemy models for model-driven migration generation
- A supported database backend (PostgreSQL, MySQL, MariaDB, SQLite, ClickHouse)

## Installation

```bash
pip install dbwarden
dbwarden init
```

## 60-Second Workflow

```bash
# 1) Initialize project
dbwarden init

# 2) Generate SQL migration from models
dbwarden make-migrations "create users table" --database primary

# 3) Apply migrations
dbwarden migrate --database primary

# 4) Verify state
dbwarden status --database primary
```

## Minimal Config Example

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app/models"],
)
```

## Example Upgrade (Dev Loop)

```bash
# Generate and apply against dev database
dbwarden --dev make-migrations "add indexes" --database primary
dbwarden --dev migrate --database primary

# Validate status/history
dbwarden --dev status --database primary
dbwarden --dev history --database primary
```

## Why Teams Choose This Model

- SQL is the source of truth
- Rollback is mandatory, not optional
- One migration flow works for one DB or many DBs
- Operational safety is first-class (locks, checksums, auditable history)

## Recap

With one `database_config(...)` definition and one migration command loop, you get:

- typed config validation
- deterministic migration plans
- explicit SQL artifacts in version control
- safe execution with recovery-oriented tooling

## Where to Go Next

- Start here: [Getting Started](getting-started/introduction.md)
- Learn the workflow: [User Guide](tutorial/your-first-migration.md)
- Go deeper: [Advanced User Guide](migration-files.md)
- Lookup details: [Reference](cli-reference.md)
