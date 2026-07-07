# Event Triggers

**Handler**: `EventTriggerHandler` (PREAMBLE phase, config-driven)

Event triggers fire on database-level DDL events. They are scoped to the entire database cluster (not per-schema).

```python
pg_event_triggers=[
    {
        "name": "trg_ddl_audit",
        "event": "ddl_command_start",
        "function": "audit_ddl",
        "tags": ["CREATE TABLE", "ALTER TABLE"],
    },
]
```

## Events

| Event | Fires On |
|-------|----------|
| `ddl_command_start` | Before any DDL statement |
| `ddl_command_end` | After any DDL statement |
| `sql_drop` | When objects are dropped |
| `table_rewrite` | When `ALTER TABLE` rewrites a table |

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE EVENT TRIGGER name ON event WHEN TAG IN ('tag1', 'tag2') EXECUTE FUNCTION func();` |
| Drop | `DROP EVENT TRIGGER IF EXISTS name;` |

## Enabled State

| Value | Meaning |
|-------|---------|
| `O` | Enabled (default) |
| `D` | Disabled |
| `R` | Enabled in replica mode |
| `A` | Always enabled |

## Notes

- Event triggers require a superuser to create
- The backing function must be created first (see [Functions & Triggers](functions-and-triggers.md))
- `DROP EVENT TRIGGER` does not auto-drop the backing function
- Tags filter which DDL commands fire the trigger; absent tags means all DDL commands
