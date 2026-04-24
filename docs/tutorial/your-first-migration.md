# Your First Migration

Create your first migration from SQLAlchemy models.

## What you'll learn

- how to generate a versioned migration file
- how to review upgrade/rollback sections
- when to create manual migrations

## Prerequisites

- configuration loads successfully (`dbwarden settings show --all`)
- target database has model paths configured
- model metadata reflects intended change

## Generate migration

```bash
dbwarden make-migrations "create users table" --database primary
```

Typical output file:

```text
migrations/primary/primary__0001_create_users_table.sql
```

## Review the file

Every migration must include both sections:

```sql
-- upgrade

-- rollback
```

## Manual migration option

When change is not model-driven:

```bash
dbwarden new "manual hotfix" --database primary
```

## Validate migration quality

```bash
dbwarden migrate --database primary
dbwarden rollback --database primary --count 1
dbwarden migrate --database primary
```

## Navigation

- Previous: [Configuration](../configuration.md)
- Next: [Applying Migrations](applying-migrations.md)
