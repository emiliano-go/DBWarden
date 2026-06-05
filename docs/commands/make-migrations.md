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

# Output plan JSON only
dbwarden make-migrations --database primary --plan
```

## Options

- `description` (optional) - Custom migration name. If not provided, automatically generated from schema changes
- `--database`, `-d` - Target database
- `--plan` - Print the migration plan JSON without writing files
- `--verbose`, `-v` - Verbose output

## Generated artifacts

When a migration is generated, DBWarden writes two files side by side:

- `{database_name}__{version}_{description}.sql`
- `{database_name}__{version}_{description}.plan.json`

The companion plan file contains machine-readable metadata about the generated migration, including:

- `migration_id`
- `operations`
- `required_flags`
- `checksum`

Example:

```json
{
  "migration_id": "primary__0001_create_users",
  "operations": [
    {
      "type": "create_table",
      "table": "users",
      "severity": "INFO"
    }
  ],
  "required_flags": [],
  "checksum": "sha256..."
}
```

`--plan` switches the command into JSON-output mode. In that mode DBWarden prints the plan to stdout and does not write the `.sql` or `.plan.json` files.

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
# Creates primary__0001_create_table_users.sql and primary__0001_create_table_users.plan.json
dbwarden make-migrations --database primary

# Creates primary__0002_add_column_users_email.sql and primary__0002_add_column_users_email.plan.json
dbwarden make-migrations --database primary

# Creates primary__0003_add_columns_users_email_name.sql and primary__0003_add_columns_users_email_name.plan.json
dbwarden make-migrations --database primary

# Uses custom name
dbwarden make-migrations "initial_schema" --database primary
```

## Notes

- Generated file includes both `-- upgrade` and `-- rollback`
- Generated `.plan.json` files are useful for CI checks and debugging
- If no models are discovered, configure `model_paths` explicitly
- with `--dev`, translation can target dev SQLite behavior

See also: [Migration File Format](../migration-files.md)
