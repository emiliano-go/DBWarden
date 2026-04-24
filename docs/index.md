# DBWarden

DBWarden is a SQL-first migration system for Python + SQLAlchemy projects.

It is built for teams that want migration changes to be explicit, reviewable, and safe in development and production.

## What DBWarden Gives You

- Migration files you can read and review before execution
- Explicit upgrade and rollback sections in the same file
- Support for one database or many databases in the same project
- Safe execution with lock protection and checksum tracking
- Dev mode (`--dev`) to run workflows against a development database

## Requirements

- Python 3.10+
- SQLAlchemy-based project (for model-driven generation)
- A supported target database (PostgreSQL, MySQL, MariaDB, SQLite, ClickHouse)

## Installation

```bash
pip install dbwarden
```

Then initialize your project:

```bash
dbwarden init
```

## Why This Approach

Many migration workflows either hide SQL behind abstractions or encourage generated output that teams never review.

DBWarden is intentionally different:

- you own the SQL
- you ship the SQL
- you can rollback with the SQL you reviewed

That keeps migration behavior deterministic and auditable.

## 60-Second Workflow

```bash
# 1) Initialize project and config scaffold
dbwarden init

# 2) Generate SQL migration from models
dbwarden make-migrations -d "create users table" --database primary

# 3) Apply pending migrations
dbwarden migrate --database primary

# 4) Check current state
dbwarden status --database primary
```

## Full Example

### Create config

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    model_paths=["app/models"],
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

### Generate migration

```bash
dbwarden make-migrations -d "create users table" --database primary
```

### Apply migration

```bash
dbwarden migrate --database primary
```

### Check migration state

```bash
dbwarden status --database primary
dbwarden history --database primary
```

### Run local dev mode

```bash
dbwarden --dev migrate --database primary
```

## What You Get from One Config Definition

With one `database_config(...)` definition, you get:

- typed config validation
- explicit migration directory ownership
- deterministic target resolution
- optional secure display of variable-based values (`secure_values=True`)

## Performance and Safety Model

DBWarden is optimized for operational correctness in real deployment pipelines:

- lock protection for migration commands
- checksum tracking for migration integrity
- repeatable migration classes (`RA__`, `ROC__`)
- status/history observability for audits and incident recovery

## Typical Team Workflow

1. Model update in feature branch
2. Generate migration SQL
3. Review SQL (upgrade + rollback)
4. Merge and apply in CI/CD
5. Verify with status/history
6. Rollback or forward-fix if needed

## The Core Model

DBWarden works as a predictable pipeline:

1. Load Python config (`database_config(...)`)
2. Resolve target database (`--database`, default, or `--all`)
3. Read migration files and determine pending plan
4. Acquire migration lock
5. Execute SQL and store migration records + checksums
6. Release lock and print execution status

## Design Principles

- SQL is the source of truth
- Rollback is required, not optional
- Multi-database support is first-class
- Local dev should stay fast and safe

## Quick Example

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

Run with:

```bash
dbwarden --dev migrate --database primary
```

## Where to Go Next

- New here: [Getting Started](getting-started/introduction.md)
- Build fundamentals: [First Steps](getting-started/first-steps.md)
- Daily usage: [Tutorial - User Guide](tutorial/your-first-migration.md)
- Internals and command lookup: [Reference](cli-reference.md)
