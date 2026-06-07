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


def seed(connection):
    """Populate seed data.

    Args:
        connection: SQLAlchemy connection or ClickHouse client.
    """
    # Programmatic data generation here
    pass
```

The `seed()` function receives a database connection. Use it to insert data programmatically:

```python
import random
from datetime import datetime, timedelta


def seed(connection):
    users = []
    for i in range(100):
        users.append({
            "name": f"user_{i}",
            "email": f"user_{i}@example.com",
            "created_at": datetime.utcnow() - timedelta(days=random.randint(0, 365)),
        })
    for user in users:
        connection.execute(
            "INSERT INTO users (name, email, created_at) VALUES (:name, :email, :created_at)",
            user,
        )
    connection.commit()
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

View which seeds have been applied:

```bash
dbwarden seed list --database primary
```

Output:

```
Seeds for database 'primary':
  V0001  seed_initial_users                   applied  2025-06-01 10:00:00
  V0002  seed_lookup_tables                   applied  2025-06-01 10:01:00
  V0003  generate_sample_data                 pending
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

DBWarden tracks applied seeds in a `_dbwarden_seeds` table:

| Column | Description |
|--------|-------------|
| `version` | 4-digit seed version number |
| `description` | human-readable description from filename |
| `seed_type` | `sql` or `python` |
| `checksum` | SHA-256 of file content |
| `applied_at` | timestamp of application |

The tracking table is created automatically on first seed apply. Seeds are idempotent by tracking -- each version can only be applied once until rolled back.

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


