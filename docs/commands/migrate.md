# migrate Command

Apply pending migrations to the database.

## Description

The `migrate` command executes all pending migration files, updating the database schema to match your current migration state.

## Usage

```bash
dbwarden migrate [OPTIONS]
```

## Options

| Short | Long | Description |
|-------|------|-------------|
| `-c` | `--count COUNT` | Number of migrations to apply |
| `-t` | `--to-version VERSION` | Migrate to a specific version |
| `-v` | `--verbose` | Enable verbose logging with SQL highlighting |
| | `--baseline` | Mark migrations as applied without executing |
| `-b` | `--with-backup` | Create a backup before migrating |
| | `--backup-dir DIRECTORY` | Directory for backup files |

**All options are optional.**

## Examples

### Apply All Pending Migrations

```bash
dbwarden migrate
```

### Apply with Verbose Output (Colored SQL)

```bash
dbwarden migrate --verbose
# or
dbwarden migrate -v
```

### Apply Specific Number of Migrations

```bash
dbwarden migrate --count 2
# or
dbwarden migrate -c 2
```

### Migrate to Specific Version

```bash
dbwarden migrate --to-version 0003
# or
dbwarden migrate -t 0003
```

### Baseline Existing Database

Mark existing database as migrated without executing SQL:

```bash
dbwarden migrate --baseline --to-version 0001
```

This is useful when:
- Starting with an existing database that wasn't tracked by DBWarden
- Integrating DBWarden into an existing project

### Create Backup Before Migrating

```bash
dbwarden migrate --with-backup
# or
dbwarden migrate -b
```

### Backup to Specific Directory

```bash
dbwarden migrate --with-backup --backup-dir /path/to/backups
```

### Combined Options

```bash
dbwarden migrate -c 1 -t 0002 -v -b --backup-dir ./backups
```

## How It Works

1. **Creates migrations tracking table**: Creates `dbwarden_migrations` table if it doesn't exist
2. **Creates lock table**: Creates `dbwarden_lock` table for concurrency control
3. **Finds pending migrations**: Identifies migrations not yet applied
4. **Applies migrations**: Executes each migration in order (versioned, then RA__, then ROC__)
5. **Records execution**: Stores migration metadata in database

## Internal Process

```
┌─────────────────────────────────────────────────────────┐
│  1. Create dbwarden_migrations table (if not exists)  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  2. Create dbwarden_lock table (if not exists)         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  3. Acquire migration lock                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  4. Find pending migrations                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  5. Parse migration files (upgrade statements)          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  6. Execute SQL statements                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  7. Record migration in database                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  8. Release lock                                        │
└─────────────────────────────────────────────────────────┘
```

## Migrations Tracking Table

DBWarden creates a `dbwarden_migrations` table to track applied migrations:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment ID |
| `version` | VARCHAR | Migration version (NULL for repeatables) |
| `description` | VARCHAR | Migration description |
| `filename` | VARCHAR | Migration filename |
| `migration_type` | VARCHAR | Type (versioned, runs_always, runs_on_change) |
| `checksum` | VARCHAR | File checksum for validation |
| `applied_at` | DATETIME | Timestamp of application |

## Migration Execution Order

1. **Versioned migrations** (NNNN_*.sql): In sequential order
2. **Runs-Always migrations** (RA__*.sql): Every execution
3. **Runs-On-Change migrations** (ROC__*.sql): Only when checksum changes

## Locking Mechanism

DBWarden uses a locking mechanism to prevent concurrent migration execution:

- **Automatic lock acquisition**: Lock is acquired before any migration
- **Lock release**: Lock is released after completion or error
- **Lock timeout**: Prevents stale locks

### Checking Lock Status

```bash
dbwarden lock-status
```

### Force Unlock (Emergency)

```bash
dbwarden unlock
```

**Warning**: Only use `unlock` if you're certain no other migration process is running.

## Output Examples

### Successful Migration

```
Pending migrations (1):
  - 0001
Starting migration: 0001_create_users.sql
Completed migration: 0001_create_users.sql in 0.05s
Migrations completed successfully: 1 migrations applied.
```

### Verbose Output

```
Detected execution mode: sync
Pending migrations (1):
  - 0001
Starting migration: 0001_create_users.sql (version: 0001)
CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY,
    username VARCHAR(50) NOT NULL
)
Completed migration: 0001_create_users.sql (version: 0001) in 0.05s
Migrations completed successfully: 1 migrations applied.
```

### No Pending Migrations

```
Migrations are up to date.
```

## Error Handling

### Migration Execution Errors

If a migration fails:

1. The migration is not recorded
2. Database changes are rolled back (if in transaction)
3. Error message is displayed

### Checksum Validation

DBWarden validates migration file checksums to ensure integrity:

- **Before execution**: Verifies file hasn't been modified (for ROC__)
- **Integrity check**: Compares stored checksum with current file

## Best Practices

1. **Always use --verbose in production**: Log all SQL statements
2. **Test migrations first**: Run on staging before production
3. **Backup before migrating**: Especially in production
4. **Don't modify applied migrations**: Create new migrations instead

## Rollback Strategy

Before running migrations, understand your rollback options:

```bash
# Check what will be rolled back
dbwarden history

# Rollback if needed
dbwarden rollback
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Database Migrations

on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install dbwarden

      - name: Run migrations
        run: dbwarden migrate --verbose
        env:
          DBWARDEN_SQLALCHEMY_URL: ${{ secrets.DATABASE_URL }}
```

## Troubleshooting

### "Migrations are up to date" but you expect changes

1. Check migrations directory exists
2. Verify migrations are in correct format
3. Check `dbwarden status` for pending migrations

### Migration fails silently

Run with `--verbose` to see detailed logs.

### Lock held by another process

```bash
dbwarden lock-status
# If locked, wait or use:
dbwarden unlock
```

## See Also

- [rollback](rollback.md): Revert applied migrations
- [status](status.md): Check migration status
- [history](history.md): View migration history
- [Lock Management](lock.md): Understanding migration locks
