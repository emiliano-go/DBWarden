# make-migrations Command

Automatically generate SQL migration files from SQLAlchemy models.

## Description

The `make-migrations` command analyzes your SQLAlchemy models and generates corresponding SQL migration files. This is the primary way to create migrations when working with ORM models.

## Usage

```bash
dbwarden make-migrations "description of changes"
```

## Arguments

| Argument | Description |
|----------|-------------|
| `description` | A descriptive name for the migration (optional) |

## Options

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Enable verbose logging |

## Examples

### Basic Usage

```bash
dbwarden make-migrations "create users table"
```

### With Verbose Output

```bash
dbwarden make-migrations "add posts and comments" --verbose
```

### Without Description

```bash
dbwarden make-migrations
```

If no description is provided, "auto_generated" will be used.

## How It Works

1. **Model Discovery**: Automatically discovers SQLAlchemy models by:
   - Scanning all subdirectories of the current directory
   - Looking for `models/` or `model/` folders inside each subdirectory
   - Searching parent directories (up to 5 levels)
   - Ignoring common library folders (`.venv`, `node_modules`, etc.)

2. **Table Extraction**: Reads table definitions from discovered models:
   - Column names and types
   - Constraints (primary key, foreign key, unique)
   - Default values
   - Nullable status

3. **SQL Generation**: Creates two sections in the migration file:
   - **Upgrade SQL**: Creates the tables/structures
   - **Rollback SQL**: Drops the tables/structures

4. **File Creation**: Saves the migration with naming pattern:
   ```
   {number}_{description}.sql
   ```

## Generated File Example

```sql
-- migrations/0001_create_users_table.sql

-- upgrade

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME
)

-- rollback

DROP TABLE users
```

## Requirements

Before running `make-migrations`:

1. Run `dbwarden init` to create migrations directory
2. Create `warden.toml` with `sqlalchemy_url`
3. Define SQLAlchemy models with `__tablename__` attribute

## Validation Checks

The command performs several validations:

### No Models Found

If no models are found:

```
No SQLAlchemy models found. Please:
  1. Create models/ directory with your SQLAlchemy models
  2. Or set model_paths in warden.toml
```

### No New Migrations

If all models are already covered by existing migrations:

```
No new migrations to generate - all models already covered by existing migrations.
```

DBWarden automatically deduplicates SQL by checking against all existing migration files.

## Model Discovery Process

DBWarden searches for models in this order:

1. **Explicit paths**: Paths in `model_paths` (comma-separated in TOML)
2. **Auto-discovery**: Looks for `models/` or `model/` directories

The search traverses up to 5 parent directories from the current working directory.

## Supported Column Types

| SQLAlchemy Type | Generated SQL Type |
|-----------------|-------------------|
| `Integer` | `INTEGER` |
| `String(n)` | `VARCHAR(n)` |
| `Text` | `TEXT` |
| `Boolean` | `BOOLEAN` |
| `DateTime` | `DATETIME` |
| `Float` | `FLOAT` |
| `Date` | `DATE` |
| `JSON` | `JSON` |

## Supported Constraints

- Primary Key (`primary_key=True`)
- Unique (`unique=True`)
- Not Null (`nullable=False`)
- Default values
- Foreign Key (`ForeignKey('table.column')`)

## Best Practices

1. **Descriptive names**: Use clear descriptions:
   ```bash
   dbwarden make-migrations "add user profile fields"
   # NOT
   dbwarden make-migrations "changes"
   ```

2. **One feature per migration**: Create separate migrations for different features

3. **Review generated SQL**: Always review the generated SQL before applying

4. **Version control**: Commit migration files to version control

## Troubleshooting

### Models Not Being Discovered

1. Check `model_paths` in `warden.toml`
2. Ensure models have `__tablename__` attribute
3. Verify models inherit from `declarative_base()`

### Incorrect SQL Generation

1. Check SQLAlchemy model definitions
2. Ensure column types are compatible
3. Review generated migration file manually

## See Also

- [new Command](new.md): Create manual migrations
- [SQLAlchemy Models](../models.md): Model requirements and best practices
- [Migration Files](../migration-files.md): Understanding migration file structure
