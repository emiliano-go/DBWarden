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

## Commands Overview

| Command | Description | Flags |
|---------|-------------|-------|
| `init` | Initialize migrations directory | None |
| `make-migrations` | Auto-generate SQL from models | `-v` |
| `new` | Create manual migration | `--version` |
| `migrate` | Apply pending migrations | `-v`, `-c`, `-t` |
| `rollback` | Revert migrations | `-v`, `-c`, `-t` |
| `history` | Show migration history | None |
| `status` | Show applied/pending status | None |
| `check-db` | Inspect database schema | `-o` |
| `diff` | Compare models vs database | `-v` |
| `squash` | Merge consecutive migrations | `-v` |
| `mode` | Show sync/async mode | None |
| `env` | Display config (masked) | None |
| `version` | Show DBWarden version | None |
| `lock-status` | Check migration lock | None |
| `unlock` | Release stuck lock | None |

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
- `--version VERSION`, `-v VERSION`: Version number for the migration (optional)

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

### mode

Display whether execution is sync or async.

```bash
dbwarden mode
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

### env

Display relevant environment variables without leaking secrets.

```bash
dbwarden env
```

**No arguments or options.**

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

### `-v, --verbose`

Enable verbose logging. Available on:
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

### `--version, -v`

Set migration version number. Available on:
- `new`

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Migration error |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DBWARDEN_SQLALCHEMY_URL` | Yes | Database connection URL |
| `DBWARDEN_ASYNC` | No | Enable async mode (true/false) |
| `DBWARDEN_MODEL_PATHS` | No | Paths to SQLAlchemy models |
| `DBWARDEN_POSTGRES_SCHEMA` | No | PostgreSQL schema |

## Configuration File

DBWarden uses `.env` file for configuration:

```env
DBWARDEN_SQLALCHEMY_URL=postgresql://user:pass@localhost:5432/db
DBWARDEN_ASYNC=false
DBWARDEN_MODEL_PATHS=models/
DBWARDEN_POSTGRES_SCHEMA=public
```

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
# Validate .env file
dbwarden env

# Check file exists
ls -la .env
```

## See Also

- [Commands Overview](commands.md): Command categories and usage patterns
- [Configuration](configuration.md): Environment variable details
- [Installation](installation.md): Installation troubleshooting
