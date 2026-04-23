# database Command

Manage multiple database configurations in warden.toml.

## Description

The `database` command group provides subcommands for managing multiple database configurations from a single warden.toml file.

## Usage

```bash
dbwarden database <subcommand> [OPTIONS]
```

## Subcommands

### list

List all configured databases.

```bash
dbwarden database list
```

**Output:**

```
Databases:
  primary (default) - sqlite:///./development.db
    type: sqlite
    migrations: migrations/primary
  analytics - postgresql://user:***@localhost:5432/analytics
    type: postgresql
    migrations: migrations/analytics
```

### add

Add a new database configuration.

```bash
dbwarden database add <name> [OPTIONS]
```

**Arguments:**
- `name`: Database name (e.g., `analytics`, `legacy`)

**Options:**

| Short | Long | Description |
|-------|------|-------------|
| `-u` | `--url URL` | SQLAlchemy connection URL (required) |
| `-t` | `--type TYPE` | Database type (sqlite, postgresql, mysql, mariadb, clickhouse) |
| `-m` | `--migrations-dir DIR` | Migrations directory |

**Examples:**

```bash
# Add with URL (type auto-detected from URL)
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"

# Add with explicit type
dbwarden database add legacy --url "mysql://user:pass@localhost:3306/legacy" --type mysql

# Add with custom migrations directory
dbwarden database add warehouse --url "postgresql://user:pass@localhost:5432/warehouse" --migrations-dir "migrations/warehouse"
```

`database add` validates uniqueness and rejects:
- Duplicate URLs (including duplicates against any `dev_database_url`)
- Different URLs that still resolve to the same physical database target

### remove

Remove a database configuration.

```bash
dbwarden database remove <name> [OPTIONS]
```

**Arguments:**
- `name`: Database name to remove

**Options:**

| Short | Long | Description |
|-------|------|-------------|
| `-f` | `--force` | Skip confirmation prompt |

**Examples:**

```bash
# Remove with confirmation
dbwarden database remove legacy

# Remove without confirmation
dbwarden database remove legacy --force
```

## Multi-Database Workflow

### Adding a New Database

```bash
# 1. Add the database configuration
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"

# 2. Verify it was added
dbwarden database list

# 3. Generate migrations for the new database
dbwarden make-migrations "create analytics tables" -d analytics

# 4. Apply migrations
dbwarden migrate -d analytics
```

### Switching Between Databases

```bash
# Work with primary database (default)
dbwarden status

# Work with analytics database
dbwarden status -d analytics

# Generate migrations for specific database
dbwarden make-migrations "add report table" -d analytics

# Apply migrations to specific database
dbwarden migrate -d analytics
```

### Migrating All Databases

```bash
# Apply pending migrations to all configured databases
dbwarden migrate --all

# Rollback migrations on all databases
dbwarden rollback --all
```

## Database Context in Logging

When working with multiple databases, DBWarden displays color-coded database context:

- **Cyan**: Database name
- **Magenta**: Database type
- **Green**: Success status
- **Yellow**: Pending status
- **Red**: Error status

Example output:

```
[INFO] Database: primary (postgresql)
[INFO] Applying migration: 0001_create_users.sql
[PENDING] 0001_create_users.sql
[APPLIED] 0001_create_users.sql
```

## Configuration

Databases are configured in `warden.toml`:

```toml
default = "primary"

[database]
[database.primary]
database_type = "sqlite"
sqlalchemy_url = "sqlite:///./development.db"
migrations_dir = "migrations/primary"

[database.analytics]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/analytics"
migrations_dir = "migrations/analytics"
```

## Supported Database Types

| Type | Value | Notes |
|------|-------|-------|
| SQLite | `sqlite` | Built-in, no drivers needed |
| PostgreSQL | `postgresql` | Requires `psycopg2-binary` |
| MySQL | `mysql` | Requires `mysql-connector-python` |
| MariaDB | `mariadb` | Requires `mysql-connector-python` |
| ClickHouse | `clickhouse` | Requires `clickhouse-connect` |

## Troubleshooting

### Database Not Found

```
Error: Database 'analytics' not found in warden.toml
```

Make sure the database is configured in warden.toml or add it first:

```bash
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"
```

### Missing sqlalchemy_url

```
Error: sqlalchemy_url is required for database 'analytics'
```

When adding a database, you must provide a connection URL:

```bash
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"
```

## See Also

- [Configuration](../configuration.md): Multi-database configuration
- [migrate](migrate.md): Apply migrations with `-d` flag
- [status](status.md): Check status for specific database
- [Databases](../databases.md): Supported database types
