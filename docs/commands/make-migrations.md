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

# Explicitly declare table renames
dbwarden make-migrations --rename-table users:accounts

# Safe multi-step type changes
dbwarden make-migrations --database primary --safe-type-change
```

## Options

- `description` (optional) — Custom migration name. If not provided, automatically generated from schema changes.
- `--database`, `-d` — Target database.
- `--plan` — Print the migration plan JSON without writing files.
- `--verbose`, `-v` — Verbose output.
- `--rename` — Repeatable. Declare a column rename in the format `table.old_name:new_name`. See [Rename Detection](#rename-detection) below.
- `--rename-table` — Repeatable. Declare a table rename in the format `old_table:new_table`. See [Table Rename Detection](#table-rename-detection) below.
- `--safe-type-change` — Use a multi-step strategy for type changes: add a temporary column, data migration comment, verification step, then drop-and-rename. Useful for databases where `ALTER COLUMN TYPE` would lock the table.

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

## Column-Level Diff

When a schema snapshot exists, `make-migrations` does more than detect new and dropped columns. It also compares columns that exist in both the snapshot and the model for three kinds of change:

| Change | Snapshot vs Model | Generated SQL |
|--------|-------------------|---------------|
| **Type change** | `snapshot.type != model.type` (normalized) | `ALTER COLUMN ... TYPE ...` |
| **Nullability change** | `snapshot.nullable != model.nullable` | `ALTER COLUMN ... SET NOT NULL` / `DROP NOT NULL` |
| **Default change** | `snapshot.default != model.default` | `ALTER COLUMN ... SET DEFAULT` / `DROP DEFAULT` |

### Type change detection

Types are normalized before comparison (see [Schema Snapshots](schema-snapshots.md)). If the normalized type differs between the snapshot and the model, an `alter_column_type` operation is emitted.

Example — model changes `VARCHAR` to `TEXT`:

```sql
-- upgrade

ALTER TABLE users ALTER COLUMN bio TYPE TEXT

-- rollback

-- ALTER TABLE users ALTER COLUMN bio TYPE <original_type>
```

### Nullability change

When a model column changes nullable, the corresponding `SET NOT NULL` or `DROP NOT NULL` is generated:

```sql
-- upgrade

ALTER TABLE users ALTER COLUMN email SET NOT NULL

-- rollback

ALTER TABLE users ALTER COLUMN email DROP NOT NULL
```

### Default change

```sql
-- upgrade

ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'

-- rollback

ALTER TABLE users ALTER COLUMN role DROP DEFAULT
```

### Safe type change (`--safe-type-change`)

For databases that don't support in-place `ALTER COLUMN TYPE` (or when you want to avoid table locks), pass `--safe-type-change` to generate a multi-step strategy:

1. Add a temporary column with the new type
2. Comment indicating a data migration (`UPDATE ... SET temp = CAST(...)`)
3. Verification step comment
4. After manual verification, drop the old column and rename the temporary column

On SQLite, this strategy is not supported and a comment is emitted instead.

### DROP COLUMN warning

All `DROP COLUMN` statements are prefixed with a warning comment:

```sql
-- WARNING: DROPPING COLUMN users.legacy_field

ALTER TABLE users DROP COLUMN legacy_field
```

## Table Rename Detection

When a table is dropped from the snapshot and a new table with similar columns is added to the model, DBWarden auto-detects it as a potential **table rename** using a column-overlap heuristic.

### Auto-detection

| Condition | Outcome |
|-----------|---------|
| A table present in the snapshot but absent from models AND a table absent from the snapshot but present in models | Overlap computed by matching column names and normalized types |
| Overlap ratio ≥ 0.6 | Prompted as a rename candidate |
| Overlap ratio < 0.6 | Emitted as drop+add with a warning comment |

The overlap ratio is `matching_columns / max(len(snapshot_cols), len(model_cols))`. A 0.6 threshold is intentionally conservative — a 10-column table with 6 matching columns is a plausible rename, while a 2-column table with 1 match is not.

### Interactive prompt (TTY)

**Single candidate:**
```
Possible table rename detected:
  users → accounts  (78% columns match)

Treat as rename? [Y/n]:
```

**Multiple candidates:**
```
Possible table renames detected:
  [1] users → accounts     (78% columns match)
  [2] posts → articles     (100% columns match)

Treat as renames? (default: all yes)
  - Press Enter to rename all
  - Type numbers to drop+add instead (e.g. "1" or "1 2"):
```

Table rename prompts appear **before** column rename prompts to ensure table names are resolved before column-level changes.

### CI / non-interactive path

```
Warning: table rename candidates detected but running non-interactive. Emitting drop+add.
  users → accounts  (78% columns match)
Rerun with --rename-table users:accounts to resolve.
```

### `--rename-table` flag

Format: `--rename-table <old_table>:<new_table>`

```bash
# Single table rename
dbwarden make-migrations --rename-table users:accounts

# Multiple renames
dbwarden make-migrations --rename-table users:accounts --rename-table posts:articles

# Combined with column rename
dbwarden make-migrations --rename-table users:accounts --rename accounts.username:email
```

Note: when combining table and column renames, the column rename references the **new** table name. Table renames are applied to the snapshot before column-level processing.

### SQL generation

All four supported backends (SQLite, PostgreSQL, MySQL, MariaDB) use the same syntax:

```sql
-- upgrade
ALTER TABLE users RENAME TO accounts;

-- rollback
ALTER TABLE accounts RENAME TO users;
```

ClickHouse emits a comment-only placeholder since it does not support `ALTER TABLE RENAME`.

## Statement ordering

Operations in the generated migration are ordered consistently:

```
RENAME TABLE        (0)   — table renames first (all subsequent ops use new name)
RENAME COLUMN       (1)
ALTER COLUMN TYPE   (2)
ALTER COLUMN NULLABLE (3)
ALTER COLUMN DEFAULT  (4)
CREATE TABLE        (5)
ADD COLUMN          (6)
ALTER FOREIGN KEY   (7)   — reserved for future use
ALTER INDEX         (8)   — reserved for future use
DROP COLUMN         (9)
DROP TABLE          (10)
```

Table renames are ordered first so that all subsequent statements reference the new table name.

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
| `"rename_flag"` | Explicitly declared via `--rename` or `--rename-table` CLI flag |
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
| Single RENAME TABLE | `rename_table_oldname_newname` |
| Multiple RENAME TABLE | `rename_tables_old1_old2` |
| Single ALTER COLUMN TYPE | `alter_column_type_tablename_col` |
| Single ALTER COLUMN NULLABLE | `alter_column_nullable_tablename_col` |
| Single ALTER COLUMN DEFAULT | `alter_column_default_tablename_col` |
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

# Creates primary__0003_alter_column_type_users_bio.sql with type change
dbwarden make-migrations --database primary

# Creates primary__0004_add_columns_users_email_name.sql + .plan.json
dbwarden make-migrations --database primary

# Creates primary__0003_rename_table_users_accounts.sql with a confirmed table rename
dbwarden make-migrations --database primary --rename-table users:accounts

# Uses safe multi-step type change for PostgreSQL
dbwarden make-migrations --database primary --safe-type-change

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
- Column-level diff (type/null/default changes) only works with a schema snapshot.
- Without a snapshot, `make-migrations` falls back to live-DB diffing which only detects new/dropped columns.

See also: [Migration File Format](../migration-files.md), [Schema Snapshots](schema-snapshots.md)
