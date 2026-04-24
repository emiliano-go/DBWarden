# Your First Migration

This page focuses on authoring your first migration file from models.

## Prerequisites

Before generating a migration, confirm:

- config is loaded (`dbwarden settings show --all`)
- target database has model paths configured
- model metadata reflects the intended schema change

## Generate from models

```bash
dbwarden make-migrations -d "create users table" --database primary
```

DBWarden creates a versioned SQL file under `migrations/<database_name>/`.

Typical filename:

```text
primary__0001_create_users_table.sql
```

The numeric version is used for deterministic ordering.

## Review file structure

Every migration includes both sections:

```sql
-- upgrade

-- rollback
```

Treat this file as the contract for the schema change.

### Upgrade section guidance

- include exactly the DDL/DML needed for the new state
- keep statements explicit and readable
- avoid hidden side effects

### Rollback section guidance

- return schema/data to the previous valid state
- avoid partial rollback logic
- test rollback locally before merge

## Optional: create a manual migration

```bash
dbwarden new -d "manual hotfix" --database primary
```

Use manual migrations when the change is not model-driven.

Common cases:

- custom index strategy
- backfill data movement
- vendor-specific SQL objects

## Verify migration quality

Recommended local loop:

```bash
dbwarden migrate --database primary
dbwarden rollback --database primary --count 1
dbwarden migrate --database primary
```

This confirms both upgrade and rollback paths behave as expected.

## Next Steps

- [Applying Migrations](applying-migrations.md)
- [Migration File Format](../migration-files.md)

## Navigation

- Previous: [Configuration](../configuration.md)
- Next: [Applying Migrations](applying-migrations.md)
