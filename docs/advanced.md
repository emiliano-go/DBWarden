# Advanced Features

This page covers operational behavior and internals for non-trivial migration workflows.

## Migration Locking

DBWarden prevents concurrent migration mutation with a lock table.

Commands that use lock protection:

- `migrate`
- `rollback`

Inspect or recover lock state:

```bash
dbwarden lock-status -d primary
dbwarden unlock -d primary
```

Internal flow:

```python
def migrate_with_lock(db_name):
    create_lock_table_if_missing(db_name)
    lock = acquire_lock(db_name)
    try:
        run_pending_migrations(db_name)
    finally:
        release_lock(lock)
```

## Checksum Integrity

Each migration execution stores a checksum in `dbwarden_migrations`.

Purpose:

- Detect modified migration files
- Support repeatable migration behaviors
- Avoid re-applying equivalent content accidentally

Conceptual checksum code:

```python
import hashlib


def checksum(statements: list[str]) -> str:
    return hashlib.sha256("".join(statements).encode()).hexdigest()
```

## Repeatable Migrations

DBWarden supports three migration classes:

- `NNNN_*.sql`: versioned, run once in order
- `RA__*.sql`: runs always
- `ROC__*.sql`: runs when checksum changed

Use repeatables for views, procedures, policies, and objects that should be refreshed.

## Dependency and Seed Headers

Migration files can include metadata headers parsed before execution.

Dependency example:

```sql
-- depends_on: ["0001", "0002"]

-- upgrade
CREATE TABLE invoices (...);

-- rollback
DROP TABLE invoices;
```

Seed marker example:

```sql
-- seed

-- upgrade
INSERT INTO service_types (name) VALUES ('api');

-- rollback
DELETE FROM service_types WHERE name = 'api';
```

## Dev Mode + Translation Strategy

When you run with `--dev` and target a SQLite dev DB, DBWarden translates unsupported backend-specific SQL model types/defaults to SQLite-compatible output.

Default behavior:

- Convert supported patterns (for example `UUID -> TEXT`)
- Fallback unsupported types to `TEXT`
- Log warning for lossy conversions

Strict behavior:

```bash
dbwarden --dev --strict-translation make-migrations "sync" -d primary
```

With strict mode, unsupported conversions fail fast.

## Safe Deployment Pattern

Recommended release sequence:

```bash
# 1) Preview pending state
dbwarden status -d primary

# 2) Create backup if needed and apply
dbwarden migrate -d primary --with-backup

# 3) Verify migration history
dbwarden history -d primary
```

For multi-database systems:

```bash
dbwarden migrate --all --with-backup
```

## CI/CD Example

```yaml
name: db-migrations
on: [push]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install dbwarden
      - run: dbwarden status -d primary
      - run: dbwarden migrate -d primary
```

## Failure Recovery Checklist

1. Run `dbwarden lock-status -d <name>`
2. If lock is stale, run `dbwarden unlock -d <name>`
3. Check partial state with `dbwarden history -d <name>`
4. Re-run migration with `--verbose`
5. If needed, rollback and re-apply in smaller steps
