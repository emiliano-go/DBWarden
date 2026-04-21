# Auto-Generated Migration Filenames

## Problem

Currently, when running `dbwarden make-migrations` without a description, the migration file is named:

```
primary__0001_auto_generated.sql
```

This is not descriptive. Users often forget to add a description, resulting in unclear migration filenames.

## Goal

Automatically generate descriptive migration filenames based on the tables being modified.

## Current Behavior

```python
# make_migrations.py, line ~101
safe_desc = re.sub(r"[^a-zA-Z0-9]", "_", description or "auto_generated").lower()
```

- If description provided → use it (e.g., `"create users"` → `primary__0001_create_users.sql`)
- If no description → use `"auto_generated"` (e.g., `primary__0001_auto_generated.sql`)

## Proposed Solution

When no description is provided, analyze the SQL to determine which tables are affected and generate a descriptive name.

### Naming Convention

| Scenario | Generated Name | Example Output |
|----------|---------------|----------------|
| Single table CREATE | `{table}_create` | `primary__0001_create_users.sql` |
| Single table ADD COLUMN | `{table}_add_columns` | `primary__0002_add_bio_column.sql` |
| Multiple tables | `{table1}_and_{table2}_...` | `primary__0001_users_and_posts_create.sql` |
| Other operations | `{table1}_and_{table2}_alter` | `primary__0001_alter_tables.sql` |

### Implementation

**Location:** `dbwarden/commands/make_migrations.py`

**New function to add:**

```python
def _generate_auto_description(tables: list, upgrade_sql: str) -> str:
    """
    Generate auto-description from affected tables.
    
    Args:
        tables: List of ModelTable objects being migrated.
        upgrade_sql: The generated upgrade SQL.
        
    Returns:
        Descriptive string for the migration filename.
    """
    table_names = [t.name for t in tables]
    
    # Determine action from SQL content
    sql_upper = upgrade_sql.upper()
    if "CREATE TABLE" in sql_upper:
        action = "create"
    elif "ADD COLUMN" in sql_upper:
        action = "add_columns"
    elif "DROP TABLE" in sql_upper:
        action = "drop"
    elif "ALTER TABLE" in sql_upper:
        action = "alter"
    else:
        action = "modify"
    
    # Format: table1_and_table2_action
    if len(table_names) == 1:
        return f"{table_names[0]}_{action}"
    else:
        joined = "_and_".join(table_names)
        return f"{joined}_{action}"
```

**Update to existing code:**

```python
# Around line 101 in make_migrations.py
# Before:
safe_desc = re.sub(r"[^a-zA-Z0-9]", "_", description or "auto_generated").lower()

# After:
if description:
    safe_desc = re.sub(r"[^a-zA-Z0-9]", "_", description).lower()
else:
    safe_desc = _generate_auto_description(tables, upgrade_sql)
```

### Edge Cases

1. **No tables detected**: Fall back to `"auto_generated"`
2. **Empty upgrade_sql**: Fall back to `"auto_generated"` (nothing to migrate)
3. **Complex migrations (multiple actions)**: Use `"alter"` as action
4. **Very long table names**: Truncate to first 20 chars to keep filename reasonable

### Testing

- Add unit tests for `_generate_auto_description` function
- Test with single table, multiple tables, various SQL operations
- Ensure backward compatibility (description parameter still works)

## Files to Modify

1. `dbwarden/commands/make_migrations.py` - Add auto-naming logic

## Acceptance Criteria

1. `dbwarden make-migrations` (no description) → generates `primary__0001_create_users.sql` based on tables
2. `dbwarden make-migrations "my description"` → generates `primary__0001_my_description.sql` (unchanged)
3. Multiple tables → `primary__0001_users_and_posts_create.sql`
4. Fallback works when no tables detected