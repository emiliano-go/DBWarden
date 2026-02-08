# rollback Command

Revert applied migrations to a previous state.

## Description

The `rollback` command undoes migrations that have been applied to the database, reverting schema changes.

## Usage

```bash
dbwarden rollback
```

## Options

| Option | Description |
|--------|-------------|
| `--count`, `-c` | Number of migrations to rollback |
| `--to-version`, `-t` | Rollback to a specific version |
| `--verbose`, `-v` | Enable verbose logging |

## Examples

### Rollback Last Migration

```bash
dbwarden rollback
```

### Rollback Multiple Migrations

```bash
# Rollback last 3 migrations
dbwarden rollback --count 3
```

### Rollback to Specific Version

```bash
dbwarden rollback --to-version 20240215_143000
```

## How It Works

1. **Finds applied migrations**: Identifies the most recent applied migrations
2. **Acquires lock**: Prevents concurrent migration operations
3. **Parses rollback statements**: Extracts SQL from `-- rollback` section
4. **Executes rollback SQL**: Reverts the schema changes
5. **Records rollback**: Removes migration record from tracking table

## Internal Process

```
┌─────────────────────────────────────────────────────────┐
│  1. Acquire migration lock                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  2. Get last applied migration(s)                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  3. Parse rollback statements from migration file       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  4. Execute rollback SQL statements                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  5. Remove migration record from database               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  6. Release lock                                         │
└─────────────────────────────────────────────────────────┘
```

## Understanding Rollback Behavior

### With --count

```bash
dbwarden rollback --count 2
```

Rolls back the last 2 migrations in reverse order.

### With --to-version

```bash
dbwarden rollback --to-version 20240215_143000
```

Rolls back all migrations after and including the specified version.

### Default Behavior

Without options, rolls back exactly 1 migration.

## Output Examples

### Successful Rollback

```
Rolling back migration: V20240215_143002__create_posts.sql (version: 20240215_143002)
Rollback completed: V20240215_143002__create_posts.sql in 0.03s
Rollback completed successfully: 1 migrations reverted.
```

### Verbose Output

```
[INFO] Mode: sync
[INFO] Rolling back migration: V20240215_143002__create_posts.sql
[INFO] SQL Statement: DROP TABLE posts
Rollback completed successfully: 1 migrations reverted.
```

### Nothing to Rollback

```
Nothing to rollback.
```

This occurs when:
- No migrations have been applied
- Database is at initial state

## Rollback Considerations

### Data Loss Warning

Rollback operations can result in data loss:

```sql
-- Example: Rollback drops tables
-- rollback
DROP TABLE posts;

-- Data in posts table WILL be lost!
```

### Irreversible Operations

Some operations cannot be rolled back:

- **DROP TABLE**: Data is deleted
- **TRUNCATE**: Data is deleted
- **ALTER TABLE** (some cases): Changes cannot be undone

### Safe Rollbacks

Operations that can be safely rolled back:

- **CREATE INDEX**: Just drop the index
- **ALTER TABLE ADD COLUMN**: Drop the column
- **CREATE TABLE**: Drop the table

## Best Practices

### 1. Always Have a Backup

```bash
# Before rollback in production
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### 2. Test Rollbacks

```bash
# Test on staging first
dbwarden rollback --to-version X
# Verify application still works
# If issues, re-apply:
dbwarden migrate --to-version X
```

### 3. Document Rollbacks

Note which migrations were rolled back and why:

```bash
# Document in commit or ticket
git commit -m "Rollback posts table - bug in post creation"
```

### 4. Use Version Control

Always have migrations committed before rolling back:

```bash
git add migrations/
git commit -m "Apply migrations"
# ... issues found ...
git log --oneline -n 5
```

## Rollback Scenarios

### Scenario 1: Bug in Migration

```bash
# Bug discovered after migration applied
dbwarden history
# V20240215_143002__create_posts.sql - has bug

# Rollback the buggy migration
dbwarden rollback --to-version 20240215_143002

# Fix the migration file
# Re-apply
dbwarden migrate
```

### Scenario 2: Wrong Version Applied

```bash
# Wrong migration applied
dbwarden status
# Shows: V2.0.0__breaking_change applied (should be V1.9.0)

# Rollback to correct version
dbwarden rollback --to-version 1.9.0
# Correct migrations now at V1.9.0
```

### Scenario 3: Complete Reset

```bash
# Rollback all migrations
dbwarden rollback --count $(dbwarden status | grep "Applied" | wc -l)
# All migrations reverted to clean state
```

## Troubleshooting

### "Nothing to rollback"

Check if migrations were applied:

```bash
dbwarden history
dbwarden status
```

### Rollback Fails

1. Check migration file has `-- rollback` section
2. Verify rollback SQL is correct
3. Run with `--verbose` for details

### Lock Held

```bash
dbwarden lock-status
# If locked, wait or:
dbwarden unlock
```

## Rollback and Migrate Together

You can rollback and reapply in one operation:

```bash
# Rollback and reapply
dbwarden rollback --to-version X
# Fix migration files
dbwarden migrate --to-version X
```

## CI/CD Rollback

### GitHub Actions Rollback

```yaml
name: Emergency Rollback

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to rollback to'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Rollback
        run: dbwarden rollback --to-version ${{ github.event.inputs.version }}
        env:
          STRATA_SQLALCHEMY_URL: ${{ secrets.DATABASE_URL }}
```

## See Also

- [migrate](migrate.md): Apply migrations forward
- [history](history.md): View migration history
- [status](status.md): Check current status
- [Migration Files](../migration-files.md): Understanding rollback SQL
