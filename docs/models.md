# SQLAlchemy Models

DBWarden reads SQLAlchemy model metadata to generate migration SQL.

Use `model_paths` in your `database_config(...)` entries to control discovery.

Example:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/main",
    model_paths=["app/models"],
)
```

Related docs:

- [Configuration](configuration/index.md)
- [Your First Migration](tutorial/your-first-migration.md)

## Common Meta Attributes

Every backend supports a core set of cross-database attributes via `class Meta(TableMeta)`:

### Table-level

| Attribute | Type | SQL | Backends |
|-----------|------|-----|----------|
| `comment` | `str` | `COMMENT ON TABLE t IS '...'` | All |
| `indexes` | `list[dict]` | `CREATE INDEX ...` | All |
| `checks` | `list[dict]` | `ALTER TABLE t ADD CONSTRAINT ... CHECK (...)` | All |
| `uniques` | `list[dict]` | `ALTER TABLE t ADD CONSTRAINT ... UNIQUE (...)` | All |

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

### Column-level

| Attribute | Type | SQL | Backends |
|-----------|------|-----|----------|
| `comment` | `str` | `COMMENT ON COLUMN t.c IS '...'` | All |
| `public` | `bool` | Controls field visibility in schemap auto-schema | All |

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    internal_note = Column(Text)

    class Meta(TableMeta):
        class internal_note:
            comment = "Internal system note"
            public = False
```

These attributes work with any `database_type`. Backend-specific subclasses (`PGTableMeta`, `CHTableMeta`) inherit all common attributes and add their own.

## PostgreSQL Model Metadata

When `database_type="postgresql"`, DBWarden supports first-class PostgreSQL metadata via `class Meta(PGTableMeta)` inner classes. This is the **only** supported surface: `mapped_column(info=...)` raises `DBWardenConfigError`.

### Table-Level Meta

Inherit from `PGTableMeta` on your `class Meta`:

```python
from dbwarden import Base, PGTableMeta

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    class Meta(PGTableMeta):
        pg_fillfactor = 80
        pg_tablespace = "fastspace"
```

`PGTableMeta` inherits all common `TableMeta` attributes (`comment`, `indexes`, `checks`, `uniques`) and adds PostgreSQL-specific ones (`pg_fillfactor`, `pg_tablespace`, `pg_unlogged`, `pg_partition`, `pg_inherits`, `pg_excludes`, `pg_indexes`, `pg_checks`, `pg_uniques`).

### Column-Level Meta

Use `PGColumnMeta` inner classes named after the column:

```python
from dbwarden import Base, PGTableMeta, PGColumnMeta

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    bio = Column(Text)

    class Meta(PGTableMeta):
        class id(PGColumnMeta):
            pg_identity = "always"
            pg_identity_start = 100

        class bio(PGColumnMeta):
            pg_storage = "EXTENDED"
            pg_collation = "en_US.UTF-8"
```

`PGColumnMeta` includes the common `comment` and `public` attributes plus PostgreSQL-specific ones (`pg_collation`, `pg_storage`, `pg_compression`, `pg_generated`, `pg_identity` and its sequence options).

For the full list of supported attributes, see [PostgreSQL Deep Dive](databases/postgresql.md).

## ClickHouse Model Metadata

When `database_type="clickhouse"`, DBWarden supports first-class ClickHouse metadata via `class Meta(CHTableMeta)` inner classes. This is the **only** supported surface. Pass options via `mapped_column(info=...)` raises `DBWardenConfigError`.

### Table-Level Meta

Inherit from `CHTableMeta` on your `class Meta`:

```python
from dbwarden import Base, CHTableMeta, ChEngineSpec

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    event_date = Column(Date)
    payload = Column(String)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("ReplacingMergeTree", args=("version_column",))
        ch_order_by = ["region", "event_time"]
        ch_primary_key = "region"
        ch_partition_by = "toYYYYMM(event_time)"
        ch_sample_by = "intHash64(user_id)"
        ch_ttl = [
            "event_time + INTERVAL 1 MONTH DELETE",
            "event_time + INTERVAL 1 YEAR TO DISK 'cold'",
        ]
        ch_settings = {"index_granularity": "8192"}
```

`CHTableMeta` inherits all common `TableMeta` attributes (`comment`, `indexes`, `checks`, `uniques`) and adds ClickHouse-specific ones (`ch_engine`, `ch_order_by`, `ch_primary_key`, `ch_partition_by`, `ch_sample_by`, `ch_ttl`, `ch_settings`, `ch_object_type`, `ch_select_statement`, `ch_to_table`, `ch_dictionary`, `ch_dict_layout`, `ch_dict_source`, `ch_dict_lifetime`, `ch_dict_primary_key`, `ch_projections`, `ch_zookeeper_path`, `ch_replica_name`).

For the full list of supported attributes, see [ClickHouse Deep Dive](databases/clickhouse.md).

### Column-Level Meta

Use `CHColumnMeta` inner classes named after the column:

```python
from dbwarden import Base, CHTableMeta, CHColumnMeta, ChEngineSpec

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    payload = Column(String)
    tags = Column(ARRAY(String))

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = "event_time"

        class payload(CHColumnMeta):
            ch_codec = "ZSTD(3)"
            ch_nullable = False

        class tags(CHColumnMeta):
            ch_low_cardinality = True
```

`CHColumnMeta` includes the common `comment` and `public` attributes plus ClickHouse-specific ones (`ch_codec`, `ch_default_expression`, `ch_materialized`, `ch_alias`, `ch_ttl`, `ch_low_cardinality`, `ch_nullable`).

### Engine Spec

Use `ChEngineSpec` for the table engine:

```python
from dbwarden import ChEngineSpec

# Simple engine
ch_engine = ChEngineSpec("MergeTree")

# Engine with arguments
ch_engine = ChEngineSpec("ReplacingMergeTree", args=("version_column",))

# Replicated engine
ch_engine = ChEngineSpec("ReplicatedMergeTree",
    zookeeper_path="/clickhouse/tables/shard1/events",
    replica_name="{replica}")

# Distributed engine with settings
ch_engine = ChEngineSpec("Distributed",
    args=("cluster", "db", "events", "rand()"),
    settings={"insert_distributed_sync": "1"})
```

For replicated engines, `ch_zookeeper_path` and `ch_replica_name` are injected as the first two engine arguments. If `args` contains existing positional arguments, they come after the ZooKeeper path and replica name.

### Projections

Use `ProjectionSpec` in `ch_projections`:

```python
from dbwarden import ProjectionSpec

class Meta(CHTableMeta):
    ch_order_by = ["author", "created_at"]
    ch_projections = [
        ProjectionSpec("by_author", "SELECT * ORDER BY author"),
        ProjectionSpec("daily_stats",
            "SELECT toDate(created_at) AS day, count() GROUP BY day"),
    ]
```

Current behavior:

- projection definitions are rendered into generated ClickHouse DDL
- safety checks classify added projections as `INFO`
- removed projections are classified as `WARNING`

### Skip Indexes

Use the `index()` factory with `clickhouse_type` and `clickhouse_granularity`:

```python
from dbwarden import index

class Meta(CHTableMeta):
    indexes = [
        index("ix_payload", "payload",
            clickhouse_type="bloom_filter",
            clickhouse_granularity=1),
    ]
```

### Materialized Views

Materialized views use `ch_select_statement` and optionally `ch_to_table`:

```python
class EventRollup(Base):
    __tablename__ = "event_rollup_mv"

    event_date = Column(Date)
    total = Column(Int64)

    class Meta(CHTableMeta):
        ch_object_type = "materialized_view"
        ch_select_statement = (
            "SELECT toDate(event_time) AS event_date, count() AS total "
            "FROM events GROUP BY event_date"
        )
        ch_to_table = "mv_target"
```

When `ch_to_table` is set, the `ENGINE` clause is omitted (ClickHouse rejects `ENGINE` with `TO`).

### Dictionaries

ClickHouse dictionaries use `ch_dictionary = True` with related `ch_dict_*` fields:

```python
class CountryCode(Base):
    __tablename__ = "country_codes"

    code = Column(String)
    name = Column(String)

    class Meta(CHTableMeta):
        ch_dictionary = True
        ch_dict_layout = "FLAT()"
        ch_dict_source = "CLICKHOUSE(HOST 'localhost' TABLE 'countries')"
        ch_dict_lifetime = "MIN 0 MAX 3600"
        ch_dict_primary_key = "code"
```

Required fields when `ch_dictionary = True`:

| Field | Description | Example |
|-------|-------------|---------|
| `ch_dict_layout` | Dictionary layout | `"FLAT()"`, `"COMPLEX_KEY_HASHED()"` |
| `ch_dict_source` | Source configuration | `"CLICKHOUSE(HOST '...' TABLE '...')"` |
| `ch_dict_lifetime` | Cache lifetime | `"MIN 0 MAX 3600"` or `3600` |

Optional field:

| Field | Description | Default |
|-------|-------------|---------|
| `ch_dict_primary_key` | Primary key expression | First column |

Column types render as CH-native types (`Int64`, `String`).

### Column Hints

Use `CHColumnMeta` inner classes for per-column hints instead of `info={}`:

```python
class Meta(CHTableMeta):
    class payload(CHColumnMeta):
        ch_codec = "ZSTD(3)"
        ch_low_cardinality = True
        ch_nullable = False
```

Supported `CHColumnMeta` fields:

| Field | Description | Example |
|-------|-------------|---------|
| `ch_codec` | Compression codec | `"ZSTD(3)"` |
| `ch_default_expression` | Default value expression | `"now()"` |
| `ch_materialized` | Materialized expression | `"lower(name)"` |
| `ch_alias` | Alias expression | `"concat(a, b)"` |
| `ch_ttl` | Column TTL expression | `"event_time + INTERVAL 1 YEAR"` |
| `ch_low_cardinality` | Wrap type in LowCardinality | `True` |
| `ch_nullable` | Wrap type in Nullable | `True` |
| `comment` | Column comment | `"User payload"` |
| `public` | Schema visibility | `False` |
