# CLI Reference

Complete command-line interface reference for DBWarden.

## Synopsis

```bash
dbwarden [OPTIONS] COMMAND [ARGS]...
```

## Global Options

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help message |
| `--version` | Show version information |
| `--dev` | Use `dev_database_url` / `dev_database_type` for target database |

## Commands Overview

| Command | Description | Flags |
|---------|-------------|-------|
| `init` | Initialize migrations directory | None |
| `database list` | List all databases | None |
| `database add` | Add new database | `-u`, `-t`, `-m` |
| `database remove` | Remove database | `-f` |
| `make-migrations` | Auto-generate SQL from models | `-v`, `-d` |
| `new` | Create manual migration | `--version` |
| `migrate` | Apply pending migrations | `-v`, `-c`, `-t`, `-d`, `--all` |
| `rollback` | Revert migrations | `-v`, `-c`, `-t`, `-d`, `--all` |
| `history` | Show migration history | `-d` |
| `status` | Show applied/pending status | `-d` |
| `check-db` | Inspect database schema | `-o`, `-d` |
| `diff` | Compare models vs database | `-v`, `-d` |
| `squash` | Merge consecutive migrations | `-v` |
| `config` | Display warden.toml config | None |
| `version` | Show DBWarden version | None |
| `lock-status` | Check migration lock | `-d` |
| `unlock` | Release stuck lock | `-d` |

### Development Mode

You can run database commands against the development connection configured under each database:

```bash
dbwarden --dev migrate -d primary
dbwarden --dev status
dbwarden --dev check-db -o json -d analytics
```

---

## Database Management Commands

### database list

List all configured databases.

```bash
dbwarden database list
```

**No arguments or options.**

---

### database add

Add a new database configuration.

```bash
dbwarden database add <name> [OPTIONS]
```

**Arguments:**
- `name`: Database name (required)

**Options:**
- `-u, --url URL`: SQLAlchemy connection URL (required)
- `-t, --type TYPE`: Database type (optional, auto-detected)
- `-m, --migrations-dir DIR`: Migrations directory (optional)

**Examples:**
```bash
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"
dbwarden database add legacy --url "mysql://user:pass@localhost:3306/legacy" --type mysql
```

---

### database remove

Remove a database configuration.

```bash
dbwarden database remove <name> [OPTIONS]
```

**Arguments:**
- `name`: Database name (required)

**Options:**
- `-f, --force`: Skip confirmation

**Examples:**
```bash
dbwarden database remove legacy
dbwarden database remove legacy --force
```

---

## Initialization Commands

### init

Initialize the migrations directory.

```bash
dbwarden init
```

**No arguments or options.**

---

## Migration Generation Commands

### make-migrations

Auto-generate SQL migration from SQLAlchemy models.

```bash
dbwarden make-migrations [DESCRIPTION] [OPTIONS]
```

**Arguments:**
- `DESCRIPTION`: Description for the migration (optional)

**Options:**
- `-v, --verbose`: Enable verbose logging

**Examples:**
```bash
dbwarden make-migrations "create users table"
dbwarden make-migrations "add posts" --verbose
dbwarden make-migrations
```

---

### new

Create a new manual migration file.

```bash
dbwarden new DESCRIPTION [OPTIONS]
```

**Arguments:**
- `DESCRIPTION`: Description of the migration (required)

**Options:**
- `--version VERSION`: Version number for the migration (optional)

**Examples:**
```bash
dbwarden new "add index to users email"
dbwarden new "custom migration" --version 2.0.0
```

---

## Migration Execution Commands

### migrate

Apply pending migrations to the database.

```bash
dbwarden migrate [OPTIONS]
```

**Options:**
- `-c, --count COUNT`: Number of migrations to apply (optional)
- `-t, --to-version VERSION`: Migrate to a specific version (optional)
- `-v, --verbose`: Enable verbose logging (optional)

**Examples:**
```bash
dbwarden migrate
dbwarden migrate --verbose
dbwarden migrate --count 2
dbwarden migrate --to-version 0003
dbwarden migrate -c 1 -t 0002 -v
```

---

### rollback

Rollback the last applied migration.

```bash
dbwarden rollback [OPTIONS]
```

**Options:**
- `-c, --count COUNT`: Number of migrations to rollback (optional)
- `-t, --to-version VERSION`: Rollback to a specific version (optional)
- `-v, --verbose`: Enable verbose logging (optional)

**Examples:**
```bash
dbwarden rollback
dbwarden rollback --verbose
dbwarden rollback --count 2
dbwarden rollback --to-version 0001
dbwarden rollback -c 1 -t 0001 -v
```

---

### squash

Merge multiple consecutive migrations into one.

```bash
dbwarden squash [OPTIONS]
```

**Options:**
- `-v, --verbose`: Enable verbose logging (optional)

**Example:**
```bash
dbwarden squash
dbwarden squash --verbose
```

---

## Status Commands

### history

Show the full migration history.

```bash
dbwarden history
```

**No arguments or options.**

---

### status

Show migration status (applied and pending).

```bash
dbwarden status
```

**No arguments or options.**

---

### version

Display DBWarden version and compatibility information.

```bash
dbwarden version
```

**No arguments or options.**

---

### config

Display configuration without leaking secrets.

```bash
dbwarden config
```

**No arguments or options.**

Shows:
- `sqlalchemy_url` (masked)
- `model_paths`
- `postgres_schema`

---

## Database Inspection Commands

### check-db

Inspect the live database schema.

```bash
dbwarden check-db [OPTIONS]
```

**Options:**
- `-o, --out FORMAT`: Output format (json, yaml, sql, txt) (optional, default: txt)

**Examples:**
```bash
dbwarden check-db
dbwarden check-db --out json
dbwarden check-db --out yaml
dbwarden check-db -o sql
```

---

### diff

Show structural differences between models and database.

```bash
dbwarden diff [TYPE] [OPTIONS]
```

**Arguments:**
- `TYPE`: Type of diff - one of: models, migrations, all (optional, default: all)

**Options:**
- `-v, --verbose`: Enable verbose logging (optional)

**Examples:**
```bash
dbwarden diff
dbwarden diff --verbose
dbwarden diff models
dbwarden diff migrations -v
```

---

## Lock Management Commands

### lock-status

Check if migration is currently locked.

```bash
dbwarden lock-status
```

**No arguments or options.**

---

### unlock

Release the migration lock.

```bash
dbwarden unlock
```

**No arguments or options.**

---

## Flag Reference

### `-d, --database`

Target a specific database by name. Available on:
- `migrate`
- `rollback`
- `status`
- `history`
- `make-migrations`
- `check-db`
- `diff`
- `lock-status`
- `unlock`

### `--all`

Operate on all configured databases. Available on:
- `migrate`
- `rollback`

### `-v, --verbose`

Enable verbose logging with SQL syntax highlighting. Available on:
- `make-migrations`
- `migrate`
- `rollback`
- `squash`
- `diff`

### `-c, --count`

Limit number of migrations. Available on:
- `migrate`
- `rollback`

### `-t, --to-version`

Target specific version. Available on:
- `migrate`
- `rollback`

### `-o, --out`

Output format selection. Available on:
- `check-db`

### `--version`

Set migration version number. Available on:
- `new`

### `--baseline`

Mark migrations as applied without executing them. Available on:
- `migrate`

### `-b, --with-backup`

Create a backup before running migrations. Available on:
- `migrate`

### `--backup-dir`

Specify backup directory for `--with-backup`. Available on:
- `migrate`

### `-u, --url`

Specify database connection URL. Available on:
- `database add`

### `-t, --type`

Specify database type. Available on:
- `database add`

### `-m, --migrations-dir`

Specify migrations directory. Available on:
- `database add`

### `-f, --force`

Skip confirmation prompt. Available on:
- `database remove`

---

## New Features

### Colored Output

DBWarden now displays colored output for better readability:

- `[PENDING]` - Yellow status for pending migrations
- `[APPLIED]` - Green status for successfully applied migrations
- `[ROLLED_BACK]` - Red status for rolled back migrations
- SQL keywords are highlighted in magenta
- SQL strings are highlighted in green
- SQL comments are highlighted in cyan

### Migration Dependencies

Specify dependencies between migrations using the header:

```sql
-- depends_on: ["0001", "0002"]

-- upgrade

CREATE TABLE posts (...);

-- rollback

DROP TABLE posts;
```

DBWarden will resolve dependencies and execute migrations in the correct order.

### Seed Data Migrations

Mark migrations as seed data using the `-- seed` marker:

```sql
-- seed

-- upgrade

INSERT INTO service_types (name, kind) VALUES
('Web Service', 'api'),
('Database', 'db');

-- rollback

DELETE FROM service_types WHERE name IN ('Web Service', 'Database');
```

Seed migrations run after all versioned migrations.

### Baseline Migrations

Mark an existing database as already migrated without executing SQL:

```bash
dbwarden migrate --baseline --to-version 0001
```

This is useful when:
- Starting with an existing database
- Integrating DBWarden into an existing project
- Recovering from migration tracking issues

### Backup Before Migration

Automatically create a backup before running migrations:

```bash
dbwarden migrate --with-backup
dbwarden migrate --with-backup --backup-dir /path/to/backups
```

Backups are stored in the `backups/` directory by default.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Migration error |

## Configuration

DBWarden uses `warden.toml` file for configuration:

```toml
default = "primary"

[database]
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:pass@localhost:5432/db"
model_paths = ["models/"]
postgres_schema = "public"
migrations_dir = "migrations/primary"
```

Run `dbwarden init` to create a starter configuration file.

## Tab Completion

Enable tab completion for bash:

```bash
eval "$(dbwarden --print-completion bash)"
```

For zsh:

```bash
eval "$(dbwarden --print-completion zsh)"
```

## Logging Levels

| Level | Description |
|-------|-------------|
| INFO | General information |
| WARNING | Potential issues |
| ERROR | Errors |
| DEBUG | Detailed debugging (with --verbose) |

## Troubleshooting

### Command Not Found

```bash
# Check installation
pip show dbwarden

# Reinstall
pip install --upgrade dbwarden
```

### Permission Denied

```bash
# Make sure scripts are executable
chmod +x /path/to/dbwarden
```

### Invalid Configuration

```bash
# Validate warden.toml file
dbwarden config

# Check file exists
ls -la warden.toml
```

## See Also

- [Commands Overview](commands.md): Command categories and usage patterns
- [Configuration](configuration.md): warden.toml configuration guide
- [Installation](installation.md): Installation troubleshooting
