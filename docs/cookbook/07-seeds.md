# 7. Seeds

## What You'll Learn

- How to create and apply SQL seed files
- How to create Python seed files with programmatic logic
- How to list, apply, and roll back seeds
- How `@seed_data` works for in-code seed definitions

## Prerequisites

- Completed [Section 3](03-apply-and-inspect.md) (migrations applied, tables exist)
- `examples/core/` project

## Step 1: Create a SQL Seed

```bash
cd examples/core
bash scripts/07-seeds.sh
```

The key command:

```bash
dbwarden seed create "initial admin users" --database primary
```

This creates `seeds/V0001__initial_admin_users.sql` with a template:

```sql
-- Seed: initial admin users
-- Database: primary
-- Applied once and tracked in _dbwarden_seeds

-- INSERT statements go here
```

We fill it in with actual data:

```sql
INSERT INTO users (email, username, full_name, is_active, created_at)
VALUES ('admin@example.com', 'admin', 'Admin User', 1, CURRENT_TIMESTAMP);

INSERT INTO users (email, username, full_name, is_active, created_at)
VALUES ('moderator@example.com', 'moderator', 'Moderator User', 1, CURRENT_TIMESTAMP);
```

## Step 2: Apply Seeds

```bash
dbwarden seed apply --database primary
```

Output:

```
[DBWarden] Applying seed V0001__initial_admin_users...
[DBWarden] Seed applied
```

Seeds are tracked in the `_dbwarden_seeds` table. Each seed version can only be applied once.

## Step 3: List Applied Seeds

```bash
dbwarden seed list --database primary
```

Output:

```
Seeds for database 'primary':
  V0001  initial_admin_users             applied  2025-01-15 10:30:00
```

## Step 4: Create and Apply a Second Seed

```bash
dbwarden seed create "demo products" --database primary
```

Populate with product data:

```sql
INSERT INTO products (name, price, description, in_stock, created_at)
VALUES ('Widget', 9.99, 'A standard widget', 1, CURRENT_TIMESTAMP);

INSERT INTO products (name, price, description, in_stock, created_at)
VALUES ('Gadget', 24.99, 'A fancy gadget', 1, CURRENT_TIMESTAMP);

INSERT INTO products (name, price, description, in_stock, created_at)
VALUES ('Doohickey', 4.99, 'A small doohickey', 1, CURRENT_TIMESTAMP);
```

```bash
dbwarden seed apply --database primary
dbwarden seed list --database primary
```

```
Seeds for database 'primary':
  V0001  initial_admin_users             applied  2025-01-15 10:30:00
  V0002  demo_products                   applied  2025-01-15 10:31:00
```

## Step 5: Roll Back a Seed

```bash
dbwarden seed rollback --database primary --count 1
```

Seed rollback removes the tracking record, allowing the seed to be re-applied. It does NOT reverse the data changes — that's your responsibility if needed.

After rollback:

```
Seeds for database 'primary':
  V0001  initial_admin_users             applied  2025-01-15 10:30:00
  V0002  demo_products                   pending
```

## Step 6: Python Seeds

Seeds can also be Python files:

```bash
dbwarden seed create "generate sample data" --database primary --type python
```

Creates `seeds/V0003__generate_sample_data.py`:

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
```

The `seed()` function receives both a raw connection and an ORM session. Use whichever fits:

```python
# Using raw connection
def seed(connection, session):
    for i in range(10):
        connection.execute(
            "INSERT INTO tags (name) VALUES (:name)",
            {"name": f"tag_{i}"},
        )

# Using ORM session
def seed(connection, session):
    for i in range(10):
        session.add(Tag(name=f"tag_{i}"))
    session.flush()
```

## Bonus: In-Code Seeds with `@seed_data`

Seeds can also live alongside your models using the `@seed_data` decorator:

```python
from dbwarden.schema import seed_data, SeedRow

@seed_data(
    database="primary",
    version="0004",
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

These are discovered through the same `model_paths` scan as models and interleave with file seeds by version number.

## Key Takeaways

- Seeds are versioned data files stored in `seeds/` alongside migrations
- SQL seeds are plain `.sql` files; Python seeds have a `seed(connection, session)` function
- `seed apply` tracks each version — it can only run once
- `seed rollback` removes the tracking record to allow re-application
- `seed list` shows applied and pending seeds
- `@seed_data` keeps seed logic close to the model it populates
- Seeds and migrations are independent — you can use one without the other

## Related Documentation

- [Seeds Reference](../seeds.md)
- [`seed` command](../commands/seed.md)
- [CLI Reference: Seed Management](../cli-reference.md#seed-management)

## Next

[Section 8: Multi-Database](08-multi-database.md)
