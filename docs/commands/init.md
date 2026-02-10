# init Command

Initialize the DBWarden migrations directory and configuration.

## Description

The `init` command creates the `migrations/` directory and a `warden.toml` config file. This is the first command you run when setting up DBWarden in a new project.

## Usage

```bash
dbwarden init
```

## What It Does

1. Creates a `warden.toml` configuration file (if it doesn't exist)
2. Creates a `migrations/` directory in the current working directory
3. Sets up the directory structure for storing migration files
4. Does NOT create any database tables or modify the database

## Example

```bash
$ dbwarden init
Created configuration file: /home/user/myproject/warden.toml
DBWarden migrations directory created: /home/user/myproject/migrations

Next steps:
  1. Edit warden.toml with your database connection URL
  2. Run 'dbwarden make-migrations' to generate migrations from your models
```

## Generated warden.toml

The command creates a starter configuration:

```toml
# DBWarden Configuration
sqlalchemy_url = "sqlite:///./mydb.db"

# Enable async mode (set to false for sync connections)
async = false

# Optional: PostgreSQL schema to use
# postgres_schema = "public"

# Optional: Paths to SQLAlchemy model files for automatic migration generation
# model_paths = ["models/"]
```

## Directory Structure

After running `init`, your project structure will look like:

```
myproject/
├── migrations/          # Created by init command
│   └── .gitkeep        # Placeholder file
├── models/
│   └── user.py
├── warden.toml         # Created by init command
└── app.py
```

## Important Notes

- **No database changes**: This command only creates local files
- **Safe to run multiple times**: Running `init` again is safe; it won't overwrite existing migrations or warden.toml
- **Required before other commands**: Most DBWarden commands require the migrations directory to exist

## See Also

- [make-migrations](make-migrations.md): Generate migrations from models
- [new](new.md): Create manual migrations
- [Configuration](../configuration.md): Full configuration guide
