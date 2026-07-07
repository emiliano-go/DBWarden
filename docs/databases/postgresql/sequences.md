# Sequences

**Handler**: `SequenceHandler` (PREAMBLE phase, config-driven)

```python
pg_sequences=[
    {
        "name": "order_number_seq",
        "start": 1000,
        "increment": 1,
        "minvalue": 1,
        "maxvalue": 999999,
        "cycle": True,
    },
]
```

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE SEQUENCE name START WITH 1000 INCREMENT BY 1 MINVALUE 1 MAXVALUE 999999 CYCLE;` |
| Drop | `DROP SEQUENCE IF EXISTS name;` |

## Options

| Key | SQL |
|-----|-----|
| `start` | `START WITH n` |
| `increment` | `INCREMENT BY n` |
| `minvalue` | `MINVALUE n` |
| `maxvalue` | `MAXVALUE n` |
| `cycle` | `CYCLE` / `NO CYCLE` |
| `owned_by` | `OWNED BY table.column` |

## Ownership

When `owned_by` is set, dropping the owning table/column automatically drops the sequence. If `owned_by` is `None`, the sequence is standalone and persists after table drops.

## Sequence vs Auto-increment

Auto-increment on PK columns (SERIAL/IDENTITY) automatically creates and manages sequences. Independent sequences declared via `pg_sequences` are useful for manual sequence management, custom numbering, or shared sequences across tables.
