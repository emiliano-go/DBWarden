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

## Required Configuration

### sqlalchemy_url

The SQLAlchemy database connection URL. This is the only required configuration option.

**Format:**

```toml
sqlalchemy_url = "dialect+driver://username:password@host:port/database"
```

**Examples:**

```toml
# PostgreSQL
sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"

# PostgreSQL with async
sqlalchemy_url = "postgresql+asyncpg://user:password@localhost:5432/mydb"

# MySQL
sqlalchemy_url = "mysql://user:password@localhost:3306/mydb"

# SQLite
sqlalchemy_url = "sqlite:///./mydb.db"

# SQLite in memory
sqlalchemy_url = "sqlite:///:memory:"

# SQLite async
sqlalchemy_url = "sqlite+aiosqlite:///./mydb.db"
```

## Optional Configuration

### async

Enable or disable asynchronous database operations.

```toml
async = true
```

| Value | Mode |
|-------|------|
| `true`, `1`, `yes` | Asynchronous |
| `false`, `0`, `no` | Synchronous (default) |

**Example:**

```toml
async = true
sqlalchemy_url = "postgresql+asyncpg://user:password@localhost:5432/mydb"
```

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

### postgres_schema

PostgreSQL schema to use (PostgreSQL only).

```toml
postgres_schema = "public"
```

## Complete warden.toml Example

```toml
# Database Connection
sqlalchemy_url = "postgresql://myuser:mypassword@localhost:5432/myapp"
async = true

# Model Discovery
model_paths = ["app/models/", "models/"]

# PostgreSQL Schema
postgres_schema = "public"
```

## Configuration in Different Environments

### Development Environment

```toml
sqlalchemy_url = "postgresql://dev:dev123@localhost:5432/dev_db"
async = false
```

### Staging Environment

```toml
sqlalchemy_url = "postgresql://staging:staging123@staging.example.com:5432/staging_db"
async = true
```

### Production Environment

```toml
sqlalchemy_url = "postgresql://prod:securepass@prod.example.com:5432/prod_db"
async = true
```

## Configuration Validation

Use the `dbwarden env` command to verify your configuration without exposing sensitive information:

```bash
dbwarden env
```

Output:

```
sqlalchemy_url: ***
async: true
model_paths: models/
postgres_schema: public
```

## Special Characters in Passwords

If your database password contains special characters, URL-encode them:

```toml
# Password: p@ss:word/123
sqlalchemy_url = "postgresql://user:p%40ss%3Aword%2F123@localhost:5432/mydb"
```

## Troubleshooting Configuration

### Missing sqlalchemy_url

```
Error: sqlalchemy_url is required in warden.toml.
```

Make sure your `warden.toml` file exists and contains the required option.

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
2. **Use different configurations per environment**: Create environment-specific configuration files
3. **Secure your credentials**: Use secrets management in production
4. **Validate configuration**: Run `dbwarden env` before applying migrations
