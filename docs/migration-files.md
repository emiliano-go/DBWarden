# Migration Files

Migration files are executable SQL units with explicit upgrade and rollback behavior.

## Naming Convention

```text
{database_name}__{version}_{description}.sql
```

Examples:

```text
primary__0001_initial_schema.sql
primary__0002_add_users_table.sql
analytics__0001_create_events.sql
```

## File Anatomy

Every migration file must include two sections:

```sql
-- upgrade

-- SQL applied during migrate

-- rollback

-- SQL applied during rollback
```

## Migration Types

| Prefix | Type | Behavior |
|--------|------|----------|
| `NNNN_` | Versioned | Runs once in version order |
| `RA__` | Runs always | Runs each `migrate` execution |
| `ROC__` | Runs on change | Runs only when checksum changed |

## Internal Execution Model

When `migrate` runs, DBWarden builds an execution plan from migration files:

```python
def build_plan(directory, applied_versions):
    versioned = parse_versioned_files(directory)
    repeatable = parse_repeatable_files(directory)

    pending_versioned = [m for m in versioned if m.version not in applied_versions]
    pending_ra = repeatable.runs_always
    pending_roc = changed_only(repeatable.runs_on_change)

    return pending_versioned + pending_ra + pending_roc
```

Then each migration:

1. Parses `-- upgrade` statements
2. Executes statements in order
3. Stores execution metadata/checksum

## Example: Versioned Migration

```sql
-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME
);

-- rollback

DROP TABLE users;
```

## Example: Runs-Always Migration

```sql
-- upgrade

CREATE OR REPLACE VIEW active_users AS
SELECT id, email FROM users WHERE is_active = TRUE;

-- rollback

DROP VIEW IF EXISTS active_users;
```

Filename example: `primary__RA__refresh_active_users_view.sql`

## Example: Runs-On-Change Migration

```sql
-- upgrade

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- rollback

DROP FUNCTION IF EXISTS update_updated_at();
```

Filename example: `primary__ROC__update_timestamp_trigger.sql`

## Metadata Headers

Dependency header:

```sql
-- depends_on: ["0004", "0005"]
```

Seed header:

```sql
-- seed
```

Headers are parsed before SQL execution and used by ordering logic.

## Best Practices

- Keep one logical change per migration file
- Always write rollback SQL that actually restores previous state
- Prefer explicit SQL over side effects in application code
- Review generated SQL before running `migrate`
- For complex data moves, use transactional blocks where backend supports it

## Validation Checklist Before Commit

```bash
dbwarden status -d primary
dbwarden migrate -d primary
dbwarden rollback --count 1 -d primary
dbwarden migrate -d primary
```
