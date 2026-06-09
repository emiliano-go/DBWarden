# Seed Management

DBWarden provides built-in seed data management for populating databases with initial or reference data. Seeds complement migrations by handling data that belongs in version control.

## Overview

Seeds are versioned data files stored in a `seeds/` directory alongside your migrations. Each seed file is tracked in the database so it can be applied once and re-applied if rolled back.

- **SQL seeds**: plain SQL files for INSERT/UPDATE statements
- **Python seeds**: Python files with a `seed()` function for programmatic data generation

## Seed directory structure

Seeds live in a `seeds/` directory at your project root (or next to your migration directories):

```
seeds/
  V0001__seed_initial_users.sql
  V0002__seed_lookup_tables.sql
  V0003__seed_sample_data.py
```

Each file follows the naming convention:

```
V<4-digit-version>__<description>.<sql|py>
```

## Creating seeds

### SQL seed

```bash
dbwarden seed create "seed initial users" --database primary
```

This creates a new file like `seeds/V0001__seed_initial_users.sql` containing a template:

```sql
-- Seed: seed initial users
-- Database: primary
-- Applied once and tracked in _dbwarden_seeds

-- INSERT statements go here
```

### Python seed

```bash
dbwarden seed create "generate sample data" --database primary --type python
```

Creates `seeds/V0001__generate_sample_data.py`:

```python
"""Seed: generate sample data for database: primary."""


def seed(connection, session):
    """Populate seed data.

    Args:
        connection: SQLAlchemy raw DB-API connection.
        session: SQLAlchemy ORM Session.
    """
    # Use session for ORM access:
    # session.add(MyModel(...))
    # session.flush()

    # Or use connection for raw SQL:
    # connection.execute("INSERT INTO ...")
```

The `seed()` function receives **two** arguments: a raw SQLAlchemy `Connection` and an ORM `Session` bound to the same transaction. Use the one that fits your style:

```python
# Using raw connection
def seed(connection, session):
    for i in range(100):
        connection.execute(
            "INSERT INTO users (name) VALUES (:name)",
            {"name": f"user_{i}"},
        )

# Using ORM session
def seed(connection, session):
    for i in range(100):
        session.add(User(name=f"user_{i}"))
    session.flush()
```

## In-Code Seed Definitions

DBWarden also supports seeds defined directly in your Python code alongside your models, using the `@seed_data` decorator. This keeps seed logic close to the model it populates.

### Row-Based Seeds

Define static rows with `SeedRow`:

```python
from dbwarden.schema import seed_data, SeedRow

@seed_data(
    database="primary",
    version="0001",
    description="initial countries",
    on_conflict="update",
    conflict_columns=["code"],
)
class CountrySeed:
    model = Country
    rows = [
        SeedRow(code="UY", name="Uruguay"),
        SeedRow(code="AR", name="Argentina"),
    ]
```

`on_conflict` controls behavior when a row with matching `conflict_columns` already exists:

| Value | Behavior |
|-------|----------|
| `"ignore"` (default) | Skips existing rows silently |
| `"update"` | Updates existing rows with new values |
| `"error"` | Raises an error on conflict |

### Logic-Based Seeds

Define a `generate(session)` static method for programmatic data:

```python
@seed_data(database="primary", version="0002", description="load permissions")
class PermissionSeed:
    model = Permission

    @staticmethod
    def generate(session):
        for resource in ["users", "orders"]:
            for action in ["read", "write", "delete"]:
                session.add(Permission(name=f"{resource}:{action}"))
```

### Discovery and Tracking

Code seeds are discovered through the same `model_paths` scan as models. They coexist with file-based seeds and are sorted together by `version` at apply time.

| Aspect | Behavior |
|--------|----------|
| Discovery | Scanned via `model_paths` alongside models |
| Versioning | Same `V0001__...` scheme as file seeds |
| Ordering | Code seeds and file seeds interleave by version |
| Duplicate versions | Raises error at `seed apply` |
| Source hash | Computed from class source; hash change warns at apply time |

### Mixing File and Code Seeds

File seeds and code seeds are compatible. You can migrate gradually:

```text
seeds/
  V0001__seed_initial_users.sql       # existing file seed
  V0002__seed_lookup_tables.sql       # existing file seed

# app/models/seeds.py                  # new code seeds
# @seed_data(version="0003", ...)     # sorted after V0002
```

## Applying seeds

Apply all pending seeds:

```bash
dbwarden seed apply --database primary
```

Apply a specific version:

```bash
dbwarden seed apply --database primary --version 0003
```

Apply to all databases:

```bash
dbwarden seed apply --all
```

### Dry run

Preview what would be applied without executing:

```bash
dbwarden seed apply --database primary --dry-run
```

## Listing seeds

View which seeds have been applied (includes both file and code seeds):

```bash
dbwarden seed list --database primary
```

Output:

```
Seeds for database 'primary':
  V0001  seed_initial_users                   applied  2025-06-01 10:00:00
  V0002  seed_lookup_tables                   applied  2025-06-01 10:01:00
  V0003  generate_sample_data                 pending
  V0004  initial countries                    pending   (code seed)
```

List across all databases:

```bash
dbwarden seed list --all
```

## Rolling back seeds

Rollback removes the applied tracking record, allowing the seed to be re-applied. It does not reverse the data changes.

```bash
# Rollback the most recent seed
dbwarden seed rollback --database primary

# Rollback a specific number
dbwarden seed rollback --database primary --count 2

# Rollback to a specific version
dbwarden seed rollback --database primary --to-version 0002
```

## Seed tracking

DBWarden tracks applied seeds in a database table (default: `_dbwarden_seeds`). The table name is configurable per-database via the `seed_table` parameter in `database_config(...)`:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
    seed_table="custom_seeds",
)
```

| Column | Description |
|--------|-------------|
| `version` | 4-digit seed version number |
| `description` | human-readable description from filename |
| `seed_type` | `sql` or `python` |
| `checksum` | SHA-256 of file content |
| `applied_at` | timestamp of application |

The tracking table is created automatically on first seed apply. Seeds are idempotent by tracking: each version can only be applied once until rolled back.

## Seeds and migrations

Seeds are independent from migrations. You can:

- Apply migrations without seeds
- Apply seeds without migrations
- Mix both in your workflow

The `dbwarden status` command and the FastAPI `GET /status` endpoint report both pending migrations and pending seeds.

## Seeds in FastAPI

The `DBWardenRouter` includes seed status in its `GET /status` response:

```json
{
  "databases": {
    "primary": {
      "status": "ok",
      "connected": true,
      "pending_migrations": 0,
      "applied_migrations": 5,
      "pending_seeds": 2,
      "applied_seeds": 1,
      "lock_active": false,
      "error": null
    }
  }
}
```

See [FastAPI Reference](fastapi/reference.md) for details.


