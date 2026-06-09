# Modeling Guide

This guide walks through the process of defining SQLAlchemy models that DBWarden can read to generate migration SQL. For the complete reference of all supported Meta attributes, see [SQLAlchemy Models Reference](../models.md).

## How DBWarden Reads Models

DBWarden discovers models in the directories specified by `model_paths` in your `database_config(...)`. It reads two sources of metadata from each model:

1. **Column definitions**: standard SQLAlchemy `Column(...)` types, nullability, defaults, primary keys
2. **`class Meta` inner class**: backend-specific options like engine specs, partitioning, codecs

All backend-specific metadata uses the `class Meta` pattern. The `__table_args__` approach is not supported for PostgreSQL or ClickHouse metadata. Using `mapped_column(info=...)` for backend-specific options raises `DBWardenConfigError`.

## Common Meta Attributes

Every backend supports a core set of cross-database attributes. These work with any `database_type`.

### Table-Level

```python
from dbwarden import Base, TableMeta

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255))

    class Meta(TableMeta):
        comment = "Core user accounts"
        indexes = [
            {"name": "ix_users_email", "columns": ["email"]},
        ]
```

Available table-level attributes: `comment`, `indexes`, `checks`, `uniques`. See [Common Meta Attributes](../models.md#common-meta-attributes) for details.

### Column-Level

```python
class Meta(TableMeta):
    class internal_note:
        comment = "Internal system note"
        public = False
```

Available column-level attributes: `comment`, `public`. Fields named with a leading `_` are implicitly `public=False`.

For the full list of backend-specific column attributes (`pg_*`, `ch_*`, `my_*`, `mdb_*`, `sq_*`), see [Column-Level Meta Base Class](../models.md#column-level-meta-base-class).

## PostgreSQL Models

When `database_type="postgresql"`, use `class Meta(PGTableMeta)` for table-level metadata and `PGColumnMeta` inner classes for column-level metadata.

```python
from dbwarden import Base, PGTableMeta, PGColumnMeta

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    bio = Column(Text)

    class Meta(PGTableMeta):
        pg_fillfactor = 80

        class id(PGColumnMeta):
            pg_identity = "always"
            pg_identity_start = 100

        class bio(PGColumnMeta):
            pg_storage = "EXTENDED"
            pg_compression = "pglz"
```

See the [reference](../models.md#postgresql-model-metadata) for the full list of `PGTableMeta` and `PGColumnMeta` attributes, or the [PostgreSQL Deep Dive](../databases/postgresql.md) for DDL behavior and snapshot format.

## ClickHouse Models

When `database_type="clickhouse"`, use `class Meta(CHTableMeta)` for table-level metadata and `CHColumnMeta` inner classes for column-level metadata.

```python
from dbwarden import Base, CHTableMeta, CHColumnMeta, ChEngineSpec, ChIndexSpec, ProjectionSpec

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    event_date = Column(Date)
    payload = Column(String)
    tags = Column(ARRAY(String))

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = ["event_date", "id"]
        ch_partition_by = "toYYYYMM(event_date)"
        ch_ttl = ["event_date + toIntervalYear(1)"]
        ch_settings = {"index_granularity": "8192"}
        ch_projections = [
            ProjectionSpec("by_date",
                "SELECT event_date, sum(amount) GROUP BY event_date"),
        ]
        ch_indexes = [
            ChIndexSpec("ix_payload", ["payload"],
                type="bloom_filter", granularity=1),
        ]

        class payload(CHColumnMeta):
            ch_codec = "ZSTD(3)"
            ch_nullable = False

        class tags(CHColumnMeta):
            ch_low_cardinality = True
```

See the [reference](../models.md#clickhouse-model-metadata) for the full list of `CHTableMeta` and `CHColumnMeta` attributes, or the [ClickHouse Deep Dive](../databases/clickhouse.md) for DDL behavior, materialized views, and dictionaries.

## Using `generate-models` as a Starting Point

The fastest way to get a correct model is to reverse-engineer it from your live database:

```bash
# PostgreSQL
dbwarden generate-models -d primary --tables users,orders

# ClickHouse (auto-detects engine metadata)
dbwarden generate-models -d analytics
```

DBWarden produces one `.py` file per table (or a single `models.py` with `--single-file`). The generated output includes `class Meta` with all detected backend-specific metadata.

Review the generated code before using it:

- Column types are mapped from database types to SQLAlchemy types. Verify the mapping is correct for your use case.
- Generated `class Meta` attributes are complete but may need adjustment (for example, you might want different index names or additional column hints).
- Partitioning, TTL, and engine settings are captured from the live database. If the database schema has drifted from what you intend, edit the model before running `make-migrations`.

## Auto-Generated Pydantic Schemas with `@auto_schema`

Use `@auto_schema` to generate four Pydantic schema classes on your model:

| Attribute | Contents |
|-----------|---------|
| `Model.Schema` | All mapped columns |
| `Model.CreateSchema` | Excludes server-defaulted columns (PKs with identity, `server_default`) |
| `Model.UpdateSchema` | All fields optional |
| `Model.PublicSchema` | Excludes fields where `public=False` or name starts with `_` |

```python
from dbwarden.schema import auto_schema

@auto_schema
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255))
    password_hash = Column(String(255))

    class Meta:
        class email:
            comment = "Primary contact email"
            public = True

        class password_hash:
            public = False

# PublicSchema excludes password_hash and any _prefixed fields
public = User.PublicSchema(email="alice@example.com")
```

The decorator reads `class Meta` to infer `SchemaConfig`, then calls `schemap` to build the Pydantic models. Column `comment` values are injected into Pydantic field descriptions, and backend-specific metadata (`pg_*`, `ch_*`, etc.) is included in `json_schema_extra.dbwarden_backend_meta`.

`@auto_schema` requires the `schemap` dependency (included with `pip install dbwarden`).

To customize schema generation, pass a `SchemaConfig` explicitly:

```python
from dbwarden.schema import auto_schema, SchemaConfig

@auto_schema(config=SchemaConfig(exclude_public=["internal_note"]))
class Order(Base):
    ...
```

`SchemaConfig` supports the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `exclude_always` | `list[str]` | Excluded from all schemas |
| `exclude_create` | `list[str]` | Excluded from CreateSchema only |
| `exclude_update` | `list[str]` | Excluded from UpdateSchema only |
| `exclude_public` | `list[str]` | Excluded from PublicSchema only |
| `field_overrides` | `dict` | Override field types in generated schemas |
| `required_always` | `list[str]` | Fields that are always required |
| `optional_always` | `list[str]` | Fields that are always optional |

## When to Use Manual Migrations

Auto-generated migrations handle most cases, but some schema changes require a manual migration via `dbwarden new`:

- PostgreSQL `USING` clause for type casts (e.g., casting `TEXT` to `INTEGER`)
- Complex column renames that the heuristic auto-detection does not catch
- Data migrations (backfilling, transforming existing data)
- Operations that ClickHouse does not support natively (table rename, some type changes)

DBWarden emits SQL comment placeholders for unsupported operations with instructions on what to write manually.

## Best Practices

- **One model class per table**: DBWarden discovers models by scanning directories. Each table should have exactly one model class.
- **Use `model_paths`**: always set `model_paths` explicitly in `database_config(...)`. Auto-discovery is available but explicit paths are more predictable.
- **Review generated migrations**: always read the `.sql` file before running `dbwarden migrate`, especially for ClickHouse where DDL is not transactional.
- **Use `--dev` for local development**: configure a `dev_database_url` (SQLite works well) and use `dbwarden --dev` to iterate quickly without touching your real database.
- **Keep Meta classes minimal**: only set attributes that differ from the default. Default values are omitted from generated migrations, reducing noise.
- **Use `@auto_schema` for API projects**: generates Pydantic schemas from your model annotations. Fields with `public=False` or a leading `_` are excluded from `PublicSchema`.
