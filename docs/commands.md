# Commands Overview

DBWarden provides a comprehensive set of commands for managing database migrations.

## Command Categories

### Initialization Commands

| Command | Description |
|---------|-------------|
| [init](commands/init.md) | Initialize the migrations directory |

### Migration Management

| Command | Description |
|---------|-------------|
| [make-migrations](commands/make-migrations.md) | Auto-generate SQL migrations from SQLAlchemy models |
| [new](commands/new.md) | Create a manual migration file |
| [migrate](commands/migrate.md) | Apply pending migrations |
| [rollback](commands/rollback.md) | Rollback applied migrations |
| [squash](commands/squash.md) | Merge multiple migrations into one |

### Status and Information

| Command | Description |
|---------|-------------|
| [history](commands/history.md) | Show migration history |
| [status](commands/status.md) | Show migration status |
| [mode](commands/mode.md) | Display sync/async mode |
| [version](commands/version.md) | Display DBWarden version |
| [env](commands/env.md) | Display environment configuration |

### Database Inspection

| Command | Description |
|---------|-------------|
| [check-db](commands/check-db.md) | Inspect database schema |
| [diff](commands/diff.md) | Compare models vs database |

### Lock Management

| Command | Description |
|---------|-------------|
| [lock-status](commands/lock.md) | Check migration lock status |
| [unlock](commands/lock.md) | Release the migration lock |

---

## Global Options

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help message |

## Command Flags Reference

### Commands with `-v, --verbose`

Enable verbose logging:
- `make-migrations`
- `migrate`
- `rollback`
- `squash`
- `diff`

### Commands with `-c, --count`

Limit number of migrations:
- `migrate`
- `rollback`

### Commands with `-t, --to-version`

Target specific version:
- `migrate`
- `rollback`

### Commands with `-o, --out`

Output format selection:
- `check-db` (formats: json, yaml, sql, txt)

### Commands with `--version`

Set migration version number:
- `new`

---

## Usage Patterns

### Apply Migrations

```bash
# Apply all pending migrations
dbwarden migrate

# Apply with verbose output
dbwarden migrate --verbose

# Apply specific number of migrations
dbwarden migrate --count 2

# Migrate to a specific version
dbwarden migrate --to-version 0003
```

### Generate Migrations

```bash
# Generate from models with description
dbwarden make-migrations "create users table"

# Generate with verbose logging
dbwarden make-migrations "add posts table" --verbose
```

### Manual Migration

```bash
# Create manual migration with auto version
dbwarden new "add index to users email"

# Create with specific version
dbwarden new "custom migration" --version 0005
```

### Rollback Migrations

```bash
# Rollback the last migration
dbwarden rollback

# Rollback 2 migrations
dbwarden rollback --count 2

# Rollback to specific version
dbwarden rollback --to-version 0001
```

### Check Status

```bash
# View all migrations and their status
dbwarden status

# View migration history
dbwarden history

# Check database schema (various formats)
dbwarden check-db
dbwarden check-db --out json
dbwarden check-db --out yaml
```

---

## Migration File Types

| Prefix | Type | Behavior |
|--------|------|----------|
| `NNNN_*.sql` | Versioned | Run once, in sequential order |
| `RA__*.sql` | Runs Always | Run on every migrate execution |
| `ROC__*.sql` | Runs On Change | Run when file checksum changes |

### Versioned Migrations (NNNN_*.sql)

Sequential migrations that run once in order:
- `0001_create_users.sql`
- `0002_add_posts.sql`
- `0003_create_comments.sql`

### Runs-Always Migrations (RA__*.sql)

Repeatable migrations that run every execution:
- `RA__create_audit_views.sql`
- `RA__seed_reference_data.sql`

### Runs-On-Change Migrations (ROC__*.sql)

Migrations that only run when their checksum changes:
- `ROC__update_config.sql`
- `ROC__add_triggers.sql`

---

## Migration Headers

### Dependencies

Specify dependencies on other migrations:

```sql
-- depends_on: ["0001", "0002"]

-- upgrade

CREATE TABLE posts (...);

-- rollback

DROP TABLE posts;
```

### Seed Migrations

Mark migrations as seed data:

```sql
-- seed

-- upgrade

INSERT INTO service_types (name, kind) VALUES
('Web Service', 'api'),
('Database', 'db');

-- rollback

DELETE FROM service_types WHERE name IN ('Web Service', 'Database');
```

---

## New Command Options

### Baseline Migrations

Mark existing database as migrated without executing SQL:

```bash
dbwarden migrate --baseline --to-version 0001
```

Use when:
- Starting with an existing database
- Integrating DBWarden into an existing project

### Backup Before Migration

Create automatic backups:

```bash
dbwarden migrate --with-backup
dbwarden migrate --with-backup --backup-dir /path/to/backups
```

---

## Command Execution Flow

```
┌─────────────────────────────────────────────────┐
│  dbwarden <command>                             │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  1. Load Configuration (warden.toml)           │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  2. Validate Environment                        │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  3. Execute Command Logic                       │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  4. Display Results                             │
└─────────────────────────────────────────────────┘
```

---

## Error Handling

DBWarden provides clear error messages for common issues:

- **Missing warden.toml file**: "sqlalchemy_url is required in warden.toml"
- **Migrations directory not found**: "Please run 'dbwarden init' first"
- **Lock active**: "Migration is currently locked"
- **Duplicate SQL**: Skips tables already in existing migrations

---

## Output Formats

| Command | Formats |
|---------|---------|
| `check-db` | txt (default), json, yaml, sql |

Example:

```bash
dbwarden check-db --out json
dbwarden check-db --out yaml
dbwarden check-db --out sql
```

---

## Getting Help

Get help for any command:

```bash
# General help
dbwarden --help

# Command-specific help
dbwarden migrate --help
dbwarden make-migrations --help
dbwarden rollback --help
```
