# 6. Safety & Impact Analysis

## What You'll Learn

- How `dbwarden check` classifies operations by danger level
- How `dbwarden check-impact` finds code references affected by a migration
- How to detect destructive changes before they reach production

## Prerequisites

- Completed [Section 3](03-apply-and-inspect.md) (migrations applied)
- `examples/core/` project

## The Problem

Schema changes are the highest-risk operation in most deployments. Dropping a column that application code still references causes runtime errors. Changing a column type can break queries. DBWarden provides two tools to detect these issues before deploy.

## Step 1: Safety Check

```bash
cd examples/core
bash scripts/06-safety-impact.sh
```

The key command:

```bash
dbwarden check --database primary
```

This scans every migration file and classifies each SQL operation by safety level:

| Level | Color | Meaning |
|-------|-------|---------|
| **SAFE** | Green | No data loss risk (add table, add nullable column, create index) |
| **INFO** | Blue | Metadata changes (comments, renames) |
| **WARN** | Yellow | Potential impact (change column type, drop default) |
| **CRITICAL** | Red | Destructive (drop table, drop column, remove NOT NULL) |

Output for our baseline migrations:

```
Checking migrations for 'primary'...
  primary__0001_create_core_tables:
    CREATE TABLE users           SAFE
    CREATE TABLE posts           SAFE
    CREATE TABLE products        SAFE
    CREATE TABLE tags            SAFE
    CREATE INDEX                 SAFE
    COMMENT ON TABLE             INFO
  Result: 5 SAFE, 1 INFO, 0 WARN, 0 CRITICAL
```

A migration with a destructive change would show:

```
  primary__0002_drop_username:
    ALTER TABLE users DROP COLUMN username  CRITICAL
```

This gives you a quick visual signal during code review: if a migration contains CRITICAL operations, it needs extra scrutiny.

## Step 2: Code Impact Analysis

```bash
dbwarden check-impact 0001 --database primary
```

`check-impact` scans your application code (not just migration files) for references that would be affected by a migration. It uses AST analysis with a grep fallback:

```
Impact analysis for migration 0001 (create_core_tables):
  No impacts found in scanned paths.
```

A more realistic scenario with a destructive change:

```
Impact analysis for migration 0002 (drop_username):
  drop_column on users.username
    References: 2
      app/routes/users.py:34  attribute_access
        .username
      app/templates/profile.jinja2:12  grep
        user.username
```

The scan finds each reference, identifies the access pattern (attribute access in Python, grep match in templates), and reports the file and line number.

### How It Works

1. Reads the migration file and parses the `-- upgrade` SQL
2. Identifies schema changes (DROP COLUMN, ALTER COLUMN TYPE, etc.)
3. Scans `.py` files using Python's `ast` module for attribute access patterns
4. Falls back to grep for non-Python files (templates, configs, etc.)
5. Reports all references grouped by change type

### Flags

- `--scan-path app/` — limit scanning to a specific directory (default: project root)
- `--deep` — also scan dependencies (imported packages)
- `--out json` — output as JSON for CI processing
- `--verbose` — show scan progress

## Pre-Deploy Workflow

Combine both tools for a safe deploy sequence:

```bash
# 1. Check migration safety
dbwarden check --database primary

# 2. Check code impact
dbwarden check-impact 0042 --database primary

# 3. Only proceed if no unexpected CRITICAL or WARN items
dbwarden migrate --database primary
```

In CI:

```yaml
- name: Safety check
  run: dbwarden check --database primary
- name: Impact analysis
  run: dbwarden check-impact 0042 --database primary
- name: Apply (only if previous steps succeeded)
  run: dbwarden migrate --database primary
```

## Key Takeaways

- `check` classifies every migration operation by safety level
- `check-impact` finds code references affected by a migration using AST + grep
- Together they catch breaking changes before deploy
- CRITICAL operations aren't blocked — they're flagged for human review
- Use `--out json` for CI integration

## Related Documentation

- [`check` command](../commands/check.md)
- [`check-impact` command](../cli-reference.md) (see CLI reference)
- [Safe Deployment](../advanced/safe-deployment.md)

## Next

[Section 7: Seeds](07-seeds.md)
