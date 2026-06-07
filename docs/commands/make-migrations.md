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

# Explicitly declare column renames
dbwarden make-migrations --rename users.username:email --rename posts.title:headline
```

## Options

- `description` (optional) — Custom migration name. If not provided, automatically generated from schema changes.
- `--database`, `-d` — Target database.
- `--plan` — Print the migration plan JSON without writing files.
- `--verbose`, `-v` — Verbose output.
- `--rename` — Repeatable. Declare a column rename in the format `table.old_name:new_name`. See [Rename Detection](#rename-detection) below.

## Schema Snapshots

After each migration is applied, DBWarden writes a **schema snapshot** to `dbwarden/schemas/<migration_id>.schema.json`. These snapshots capture the full DDL state (tables, columns, types, indexes, constraints, enums) at that point in time.

`make-migrations` diffs your SQLAlchemy models against the **latest** snapshot instead of the live database. This means:

- You don't need a running database to generate migrations (after the first `migrate`).
- Rename detection works by comparing dropped and added columns between the snapshot and your models.
- If no snapshot exists, `make-migrations` falls back to diffing against the live database.

See [Schema Snapshots](schema-snapshots.md) for details.

## Rename Detection

When a column is dropped from the snapshot and a new column of the same type is added to the model, DBWarden auto-detects it as a potential **rename** and emits `ALTER TABLE ... RENAME COLUMN` instead of `DROP` + `ADD`.

### Auto-detection rules

| Condition | Outcome |
|-----------|---------|
| Same table, 1 dropped + 1 added, same normalized type | Auto-detected as rename |
| Different types | Never auto-detected (emits drop + add) |
| Same name kept | Skipped (no op) |
| 2+ dropped + 2+ added of same type | Paired sequentially (positional) |

### Interactive prompt (TTY)

When auto-detected renames are found and you're in an interactive terminal, `make-migrations` prompts you to confirm each one:

**Single rename:**
```
Detected rename: users.username → email. Confirm rename? [Y/n]:
```

**Multiple renames:**
```
Detected column renames:
  [1] users.username → email
  [2] posts.title → headline
  [s] Skip all
  [a] Accept all
Select renames to confirm (e.g. 1,3 or a or s):
```

### CI / non-TTY behavior

When not in an interactive terminal, auto-detected renames are **not applied**. Instead, a warning is printed suggesting the `--rename` flag:

```
The following auto-detected column renames were not confirmed:
  users.username → email (use --rename users.username:email to confirm)
  posts.title → headline (use --rename posts.title:headline to confirm)
These will be emitted as DROP + ADD instead of RENAME.
```

To apply them in CI, pass the corresponding `--rename` flags.

### `--rename` flag

The `--rename` flag explicitly tells `make-migrations` to treat a drop+add pair as a rename. It is required in non-TTY environments (CI) and can also be used to force renames that auto-detection would miss (e.g., type changes).

Format: `--rename <table>.<old_name>:<new_name>`

Examples:

```bash
# Single rename
dbwarden make-migrations --rename users.username:email

# Multiple renames
dbwarden make-migrations --rename users.username:email --rename posts.title:headline

# Force rename even when types differ
dbwarden make-migrations --rename users.phone:mobile_phone
```

### Resolution order

1. **`--rename` flags** are always applied as `RENAME COLUMN` with `resolved_from: "rename_flag"`.
2. **Auto-detected renames** confirmed via interactive prompt get `resolved_from: "prompt"`.
3. **Auto-detected renames** not in `--rename` flags and not confirmed (or in CI) are emitted as `DROP` + `ADD` instead.

## Generated artifacts

When a migration is generated, DBWarden writes two files side by side:

- `{database_name}__{version}_{description}.sql`
- `{database_name}__{version}_{description}.plan.json`

The companion plan file contains machine-readable metadata about the generated migration:

- `migration_id`
- `operations` — each operation includes `type`, `table`, `severity` and optionally `resolved_from` (for rename operations)
- `required_flags`
- `checksum`

Example with rename:

```json
{
  "migration_id": "primary__0003_rename_column_users_username",
  "operations": [
    {
      "type": "rename_column",
      "table": "users",
      "new_name": "email",
      "severity": "INFO",
      "resolved_from": "rename_flag"
    },
    {
      "type": "add_column",
      "table": "users",
      "column": "phone",
      "severity": "INFO"
    }
  ],
  "required_flags": [],
  "checksum": "sha256..."
}
```

Possible `resolved_from` values:

| Value | Meaning |
|-------|---------|
| `"rename_flag"` | Explicitly declared via `--rename` CLI flag |
| `"prompt"` | Confirmed interactively by the user |
| (absent) | Auto-detected rename kept without prompt (currently unused, reserved) |

`--plan` switches the command into JSON-output mode. In that mode DBWarden prints the plan to stdout and does not write the `.sql` or `.plan.json` files.

## Auto-Generated Names

When no description is provided, DBWarden automatically generates a descriptive name from the schema changes:

| Change | Generated Name |
|--------|----------------|
| Single CREATE TABLE | `create_table_tablename` |
| Multiple CREATE TABLE | `create_tables_users_posts` |
| Single ADD COLUMN | `add_column_tablename_columnname` |
| Multiple ADD COLUMN (same table) | `add_columns_tablename_col1_col2` |
| Single RENAME COLUMN | `rename_column_tablename_new_name` |
| Multiple RENAME COLUMN (same table) | `rename_columns_tablename_col1_col2` |
| ADD + DROP (same table) | `alter_tablename_col1_col2` |
| Changes across tables | `add_column_users_email_and_1_more_tables` |
| Many targets | `add_columns_tablename_col1_col2_and_3_more` |

### Name Rules

- Snake case throughout.
- Operation words pluralized for multiple targets (e.g., `add_column` → `add_columns`).
- Mixed operations use `alter`.
- Max 72 characters (table/target names truncated as needed).

## Examples

```bash
# Creates primary__0001_create_table_users.sql + .plan.json
dbwarden make-migrations --database primary

# Creates primary__0002_add_column_users_email.sql + .plan.json
dbwarden make-migrations --database primary

# Creates primary__0003_rename_column_users_email.sql with a confirmed rename
dbwarden make-migrations --database primary --rename users.username:email

# Creates primary__0004_add_columns_users_email_name.sql + .plan.json
dbwarden make-migrations --database primary

# Uses custom name
dbwarden make-migrations "initial_schema" --database primary

# Preview plan JSON without writing files
dbwarden make-migrations --database primary --plan
```

## Notes

- Generated file includes both `-- upgrade` and `-- rollback`.
- Generated `.plan.json` files are useful for CI checks and debugging.
- If no models are discovered, configure `model_paths` explicitly.
- With `--dev`, translation can target dev SQLite behavior.
- Schema snapshots are written to `dbwarden/schemas/` after each successful `migrate` — see [Schema Snapshots](schema-snapshots.md).

See also: [Migration File Format](../migration-files.md), [Schema Snapshots](schema-snapshots.md)
