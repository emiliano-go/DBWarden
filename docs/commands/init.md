# init Command

Initialize the DBWarden migrations directory and configuration.

## Description

The `init` command creates the `migrations/` directory and a `warden.toml` config file. This is the first command you run when setting up DBWarden in a new project.

## Usage

```bash
dbwarden init
dbwarden init --database primary
```

## Options

| Option | Description |
|--------|-------------|
| `--database`, `-d` | Database name to create migration directory for |

## What It Does

1. Creates a `warden.toml` configuration file (if it doesn't exist)
2. Creates a `migrations/<name>/` directory for the default database
3. Sets up the directory structure for storing migration files
4. Does NOT create any database tables or modify the database

## Example

```bash
$ dbwarden init
Created configuration file: /home/user/myproject/warden.toml
DBWarden migrations directory created: /home/user/myproject/migrations/default

Next steps:
  1. Edit warden.toml with your database connection URLs
  2. Run 'dbwarden make-migrations -d <name>' to generate migrations
```

## Generated warden.toml

The command creates a starter configuration with the new multi-database format:

```toml
# DBWarden Configuration
# See documentation: https://emiliano-gandini-outeda.me/DBWarden/

# Default database
default = "default"

# Database configurations
[database]
[database.default]
# Database type: sqlite, postgresql, mysql, mariadb, clickhouse
database_type = "sqlite"
# Database connection URL (required)
sqlalchemy_url = "sqlite:///./development.db"

# PostgreSQL schema (optional, only for postgresql)
# postgres_schema = "public"

# Paths to SQLAlchemy models for auto-migration (optional)
# model_paths = ["app/models/"]

# Migration directory (optional, defaults to "migrations/<name>")
# migrations_dir = "migrations/default"
```

## Directory Structure

After running `init`, your project structure will look like:

```
myproject/
├── migrations/
│   └── default/           # Created by init command
├── models/
│   └── user.py
├── warden.toml            # Created by init command
└── app.py
```

## Adding Multiple Databases

After init, use `dbwarden database add` to add more databases:

```bash
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"
dbwarden database add legacy --url "mysql://user:pass@localhost:3306/legacy"
```

## Important Notes

- **No database changes**: This command only creates local files
- **Safe to run multiple times**: Running `init` again is safe; it won't overwrite existing migrations or warden.toml
- **Required before other commands**: Most DBWarden commands require the migrations directory to exist
- **Creates default database**: The first database created is named "default" and uses SQLite

## See Also

- [make-migrations](make-migrations.md): Generate migrations from models
- [new](new.md): Create manual migrations
- [Configuration](../configuration.md): Full configuration guide
- [Databases](../databases.md): Supported databases
