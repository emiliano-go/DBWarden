# Functions & Triggers

Functions and triggers are **config-driven** objects processed during the PREAMBLE phase (before table diffing). They are declared in `database_config(...)`.

## Functions

Declared via `pg_functions`. Each function definition includes the body, language, and options.

```python
pg_functions=[
    {
        "name": "update_timestamp",
        "language": "plpgsql",
        "body": """
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
        """,
        "returns": "trigger",
    },
    {
        "name": "count_users",
        "language": "sql",
        "body": "SELECT count(*) FROM users",
        "returns": "bigint",
        "volatility": "STABLE",
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE FUNCTION name (...args...) RETURNS type AS $$ body $$ LANGUAGE lang;` |
| Drop | `DROP FUNCTION IF EXISTS name (...args...) CASCADE;` |

Changes are detected as drop-then-create. There is no `CREATE OR REPLACE` for changed bodies.

### Options

| Config Key | SQL |
|------------|-----|
| `volatility` | `VOLATILE` / `STABLE` / `IMMUTABLE` |
| `security_definer` | `SECURITY DEFINER` |
| `leakproof` | `LEAKPROOF` |
| `parallel` | `PARALLEL UNSAFE` / `RESTRICTED` / `SAFE` |
| `cost` | `COST n` |
| `rows` | `ROWS n` |

### Return Types

| Returns | Description |
|---------|-------------|
| `trigger` | Trigger function (returns `TRIGGER`) |
| `void` | No return value |
| `table (...)` | Set-returning function (use `rows` for estimate) |
| Any PG type | Scalar return |

### Arguments

```python
{
    "name": "add_user",
    "args": [
        {"name": "p_name", "type": "text"},
        {"name": "p_email", "type": "text"},
    ],
    "returns": "int",
    "language": "sql",
    "body": "INSERT INTO users (name, email) VALUES (p_name, p_email) RETURNING id",
}
```

## Triggers

Declared via `pg_triggers`. Each trigger binds a function to a table event.

```python
pg_triggers=[
    {
        "name": "trg_users_updated_at",
        "table": "users",
        "function": "update_timestamp",
        "timing": "BEFORE",
        "events": ["UPDATE"],
        "for_each": "ROW",
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE TRIGGER name timing event ON table FOR EACH ROW EXECUTE FUNCTION func();` |
| Alter | `ALTER TRIGGER name ON table RENAME TO new_name;` |
| Drop | `DROP TRIGGER IF EXISTS name ON table;` |

### Events

One or more of: `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`.

### Timing

| Timing | Description |
|--------|-------------|
| `BEFORE` | Fires before the event |
| `AFTER` | Fires after the event |
| `INSTEAD OF` | Replaces the event (views only) |

### Condition

Use `condition` to add a `WHEN` clause:

```python
pg_triggers=[{
    "name": "trg_prevent_delete",
    "table": "users",
    "function": "prevent_delete",
    "timing": "BEFORE",
    "events": ["DELETE"],
    "for_each": "ROW",
    "condition": "OLD.is_protected",
}]
```
