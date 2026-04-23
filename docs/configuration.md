# Configuration

DBWarden is configured through a `warden.toml` file. This guide covers all configuration options.

## Configuration File

DBWarden looks for a `warden.toml` file in the current working directory or any parent directory.

### Creating the warden.toml File

Run `dbwarden init` to create a starter configuration:

```bash
dbwarden init
```

This creates both the `migrations/` directory and a `warden.toml` file.

### warden.toml File Location

DBWarden searches for `warden.toml` in the following order:

1. Current working directory
2. Parent directories (up to the filesystem root)

This allows you to have a single `warden.toml` file at your project root that applies to all subdirectories.

## Multi-Database Configuration

DBWarden supports managing multiple databases from a single configuration file.

### Basic Structure

```toml
default = "primary"

[database]
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/main"
migrations_dir = "migrations/primary"
dev_database_type = "sqlite"
dev_database_url = "sqlite:///./development.db"

[database.analytics]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/analytics"
migrations_dir = "migrations/analytics"
```

### default

The default database to use when no `--database` flag is specified.

```toml
default = "primary"
```

## Database Configuration

### database_type

The database type determines SQL dialect and features. Supported types:

| Type | Description | Example URL Prefix |
|------|-------------|-------------------|
| `sqlite` | SQLite database | `sqlite:///` |
| `postgresql` | PostgreSQL | `postgresql://` or `postgres://` |
| `mysql` | MySQL | `mysql://` |
| `mariadb` | MariaDB | `mariadb://` |
| `clickhouse` | ClickHouse | `clickhouse://` |

```toml
database_type = "postgresql"
```

**Note:** The `database_type` is automatically inferred from the URL if not specified. You can override it for explicit control.

### sqlalchemy_url

The SQLAlchemy database connection URL.

**Format:**

```toml
sqlalchemy_url = "dialect+driver://username:password@host:port/database"
```

**Examples:**

```toml
# PostgreSQL
sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"

# MySQL
sqlalchemy_url = "mysql://user:password@localhost:3306/mydb"

# SQLite
sqlalchemy_url = "sqlite:///./mydb.db"

# SQLite in memory
sqlalchemy_url = "sqlite:///:memory:"

# ClickHouse
sqlalchemy_url = "clickhouse://user:password@localhost:8123/analytics"
```

## Optional Configuration

### model_paths

List of paths to directories containing SQLAlchemy models.

```toml
model_paths = ["models/", "app/models/"]
```

If not specified, DBWarden will automatically discover models by:
- Scanning all subdirectories of the current directory
- Looking for `models/` or `model/` folders inside each subdirectory
- Searching up to 5 parent directories from current working directory
- Ignoring common library folders (`.venv`, `node_modules`, `__pycache__`, etc.)

### migrations_dir

Directory for migration files. Defaults to `migrations/<database_name>`.

```toml
migrations_dir = "migrations/primary"
```

### postgres_schema

PostgreSQL schema to use (PostgreSQL only).

```toml
postgres_schema = "public"
```

### dev_database_url

Optional development database URL used when running commands with `--dev`.

```toml
dev_database_url = "sqlite:///./development.db"
```

### dev_database_type

Optional type for the development database.

```toml
dev_database_type = "sqlite"
```

If omitted, DBWarden infers it from `dev_database_url`.

## Complete warden.toml Example

```toml
# Default database
default = "primary"

# Database configurations
[database]

[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://myuser:mypassword@localhost:5432/myapp"
dev_database_type = "sqlite"
dev_database_url = "sqlite:///./development.db"
model_paths = ["app/models/"]
migrations_dir = "migrations/primary"
postgres_schema = "public"

[database.analytics]
database_type = "postgresql"
sqlalchemy_url = "postgresql://myuser:mypassword@localhost:5432/analytics"
migrations_dir = "migrations/analytics"

[database.legacy]
database_type = "mysql"
sqlalchemy_url = "mysql://myuser:mypassword@localhost:3306/legacy"
migrations_dir = "migrations/legacy"
```

## Development Mode

Use the `--dev` global CLI flag to run commands against `dev_database_url` for the selected database.

```bash
dbwarden migrate --dev -d primary
dbwarden status --dev
```

If `--dev` is enabled and the target database has no `dev_database_url`, DBWarden raises a configuration error.

### SQLite Recommendation for Development

We recommend using SQLite for `dev_database_url`:

```toml
dev_database_type = "sqlite"
dev_database_url = "sqlite:///./development.db"
```

When using `--dev` with a SQLite dev database, DBWarden translates backend-specific model types/defaults (PostgreSQL, MySQL, MariaDB, ClickHouse) to SQLite-compatible SQL.

If a type cannot be converted safely, DBWarden falls back to `TEXT` and emits warnings.

For strict behavior, use:

```bash
dbwarden --dev --strict-translation make-migrations -d primary
```

In strict translation mode, unsupported conversions fail instead of falling back.

## Uniqueness Constraints

DBWarden validates that configured database targets are unique:

1. No duplicate `sqlalchemy_url` values.
2. No duplicate `dev_database_url` values.
3. No overlap between primary and dev URLs.
4. No two entries can resolve to the same physical database target (for example, same host/port/database with different credentials).

Examples of invalid configurations:

```toml
[database.primary]
sqlalchemy_url = "postgresql://user1:pass1@localhost:5432/main"

[database.analytics]
sqlalchemy_url = "postgresql://user2:pass2@localhost:5432/main"
```

```toml
[database.primary]
sqlalchemy_url = "sqlite:///./main.db"

[database.analytics]
dev_database_url = "sqlite:///./main.db"
```

## Configuration in Different Environments

### Development Environment

```toml
default = "dev"

[database]

[database.dev]
database_type = "sqlite"
sqlalchemy_url = "sqlite:///./dev.db"
migrations_dir = "migrations/dev"
```

### Staging Environment

```toml
default = "staging"

[database]

[database.staging]
database_type = "postgresql"
sqlalchemy_url = "postgresql://staging:staging123@staging.example.com:5432/staging_db"
postgres_schema = "public"
migrations_dir = "migrations/staging"
```

### Production Environment

```toml
default = "prod"

[database]

[database.prod]
database_type = "postgresql"
sqlalchemy_url = "postgresql://prod:securepass@prod.example.com:5432/prod_db"
postgres_schema = "public"
migrations_dir = "migrations/prod"
```

## Configuration Validation

Use the `dbwarden config` command to verify your configuration without exposing sensitive information:

```bash
dbwarden config
```

Output:

```
Database: primary
database_type: postgresql
sqlalchemy_url: ***
migrations_dir: migrations/primary
postgres_schema: public
```

## Special Characters in Passwords

If your database password contains special characters, URL-encode them:

```toml
# Password: p@ss:word/123
sqlalchemy_url = "postgresql://user:p%40ss%3Aword%2F123@localhost:5432/mydb"
```

## Troubleshooting Configuration

### Missing database section

```
Error: No [database] section found in warden.toml.
```

Make sure your `warden.toml` includes a `[database]` section with at least one database configuration.

### Missing sqlalchemy_url

```
Error: sqlalchemy_url is required for database 'primary'.
```

Make sure each database configuration includes a valid `sqlalchemy_url`.

### Invalid database_type

```
Error: Invalid database_type 'oracle'. Must be one of: sqlite, postgresql, mysql, mariadb, clickhouse
```

Use one of the supported database types.

### Invalid URL Format

```
Error: Could not parse SQLAlchemy URL
```

Check that your URL follows the correct format: `dialect+driver://username:password@host:port/database`

### Database Connection Failed

```
Error: could not connect to server
```

Verify that:
1. The database server is running
2. The host and port are correct
3. The username and password are valid
4. The database exists

## Best Practices

1. **Never commit `warden.toml` to version control with secrets**: Add `warden.toml` to your `.gitignore` file if it contains credentials, or use a separate `warden.toml.example` as a template
2. **Use different configurations per environment**: Create environment-specific database configurations
3. **Secure your credentials**: Use secrets management in production
4. **Validate configuration**: Run `dbwarden config` before applying migrations
5. **Use descriptive database names**: Names like `primary`, `analytics`, `legacy` are clearer than `db1`, `db2`
