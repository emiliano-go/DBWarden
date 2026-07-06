# Indexes

Indexes are handled by `IndexHandler` during the DIFF phase.

## Supported Index Types

| Method | Description |
|--------|-------------|
| B-tree | Default, for equality and range queries |
| Hash | Equality-only, smaller than btree |
| GiST | Geometric, full-text, and custom data types |
| GIN | JSONB, array, full-text, and tsvector |
| BRIN | Block range indexes for large tables |
| SP-GiST | Space-partitioned GiST |

## Declaring Indexes

Model-level indexes use `PgIndexSpec`:

```python
from dbwarden.databases.pgsql import PgIndexSpec

class Meta(PGTableMeta):
    pg_indexes = [
        PgIndexSpec("ix_users_email", ["email"], unique=True, using="btree"),
        PgIndexSpec("ix_users_data", ["data"], using="gin",
            postgresql_ops={"data": "jsonb_path_ops"}),
    ]
```

`PgIndexSpec` supports:

| Field | Description |
|-------|-------------|
| `name` | Index name (auto-generated if omitted) |
| `columns` | Indexed columns |
| `unique` | `CREATE UNIQUE INDEX` |
| `using` | Access method (`btree`, `gin`, `gist`, `hash`, `brin`, `spgist`) |
| `where` | Partial index predicate |
| `include` | `INCLUDE` columns (covering indexes) |
| `expression` | Expression index (e.g., `lower(email)`) |
| `with_params` | Storage parameters (`fillfactor`, `autovacuum_*`) |
| `tablespace` | `TABLESPACE name` |
| `nulls_not_distinct` | `NULLS NOT DISTINCT` (PG 15+) |
| `column_sorting` | Per-column `ASC` / `DESC` / `NULLS FIRST` / `NULLS LAST` |
| `postgresql_ops` | Per-column operator classes |
| `concurrently` | `CREATE INDEX CONCURRENTLY` (default `True`) |

## Partial Indexes

```python
PgIndexSpec("ix_users_active", ["email"], where="active = true")
```

```sql
CREATE INDEX CONCURRENTLY ix_users_active ON users (email) WHERE active = true;
```

## Expression Indexes

```python
PgIndexSpec("ix_users_lower_email", columns=[], expression="lower(email)")
```

```sql
CREATE INDEX CONCURRENTLY ix_users_lower_email ON users (lower(email));
```

Expression indexes are stored with empty `columns` and the expression text in the `expression` field. Changes to the expression are detected and produce a `DROP INDEX` + `CREATE INDEX` cycle.

## Operator Classes

```python
PgIndexSpec("ix_users_data", ["data"],
    using="gin",
    postgresql_ops={"data": "jsonb_path_ops"})
```

```sql
CREATE INDEX CONCURRENTLY ix_users_data ON users USING GIN (data jsonb_path_ops);
```

## Column Sorting

```python
PgIndexSpec("ix_orders_date", ["created_at DESC NULLS LAST", "id ASC"])
```
