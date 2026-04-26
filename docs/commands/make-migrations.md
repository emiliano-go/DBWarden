# `make-migrations`

Generate SQL migration file(s) from SQLAlchemy models.

## Usage

```bash
# Auto-generated name from schema changes
dbwarden make-migrations

# User-provided description
dbwarden make-migrations "create users table"

# With database option
dbwarden make-migrations --database primary --verbose
```

## Options

- `description` (optional) - Custom migration name. If not provided, automatically generated from schema changes
- `--database`, `-d` - Target database
- `--verbose`, `-v` - Verbose output

## Auto-Generated Names

When no description is provided, DBWarden automatically generates a descriptive name from the schema changes:

| Change | Generated Name |
|--------|----------------|
| Single CREATE TABLE | `create_table_tablename` |
| Multiple CREATE TABLE | `create_tables_users_posts` |
| Single ADD COLUMN | `add_column_tablename_columnname` |
| Multiple ADD COLUMN (same table) | `add_columns_tablename_col1_col2` |
| ADD + DROP (same table) | `alter_tablename_col1_col2` |
| Changes across tables | `add_column_users_email_and_1_more_tables` |
| Many targets | `add_columns_tablename_col1_col2_and_3_more` |

### Name Rules

- Snake case throughout
- Operation words pluralized for multiple targets (e.g., `add_column` → `add_columns`)
- Mixed operations use `alter`
- Max 72 characters (table/target names truncated as needed)

## Examples

```bash
# Creates 0001_create_table_users.sql
dbwarden make-migrations

# Creates 0002_add_column_users_email.sql  
dbwarden make-migrations

# Creates 0003_add_columns_users_email_name.sql
dbwarden make-migrations

# Uses custom name
dbwarden make-migrations -d initial_schema
```

## Notes

- Generated file includes both `-- upgrade` and `-- rollback`
- If no models are discovered, configure `model_paths` explicitly
- with `--dev`, translation can target dev SQLite behavior

See also: [Migration File Format](../migration-files.md)