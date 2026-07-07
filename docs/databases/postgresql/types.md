# Types

DBWarden supports three object-level type families: enums, domains, and composite types. Enums are model-derived (auto-discovered from table columns). Domains and composite types are config-driven.

## Enums

**Handler**: `EnumHandler` (DIFF phase)

Enums are auto-discovered from column types during snapshot extraction. Enum values are tracked with position data, so `ALTER TYPE ... ADD VALUE ... AFTER ...` preserves ordering.

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE TYPE name AS ENUM ('val1', 'val2', ...)` |
| Add value | `ALTER TYPE name ADD VALUE 'newval' AFTER 'existing'` |
| Drop | `DROP TYPE IF EXISTS name` |

## Domains

**Handler**: `DomainHandler` (PREAMBLE phase)

Domains are config-driven objects declared via `pg_domains`:

```python
pg_domains=[
    {
        "name": "us_postal_code",
        "type": "text",
        "not_null": True,
        "check": "VALUE ~ '^\d{5}(-\d{4})?$'",
    },
    {
        "name": "positive_int",
        "type": "int",
        "check": "VALUE > 0",
        "default": "1",
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE DOMAIN name AS base_type [DEFAULT default] [NOT NULL] [CHECK (expr)]` |
| Drop | `DROP DOMAIN IF EXISTS name CASCADE;` |

Changes to domain definition are detected as drop-then-create.

## Composite Types

**Handler**: `CompositeTypeHandler` (PREAMBLE phase)

Composite types are config-driven objects declared via `pg_composite_types`:

```python
pg_composite_types=[
    {
        "name": "address",
        "columns": [
            {"name": "street", "type": "text"},
            {"name": "city", "type": "text"},
            {"name": "zip", "type": "text"},
        ],
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE TYPE name AS (col1 type1, col2 type2, ...)` |
| Drop | `DROP TYPE IF EXISTS name CASCADE;` |

### Schema

Composite types can be scoped to a schema:

```python
{"name": "address", "schema": "app", "columns": [...]}
```
