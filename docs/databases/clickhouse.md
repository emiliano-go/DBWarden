# ClickHouse

DBWarden treats ClickHouse as a **first-class backend**: every natively supported feature is reverse-engineered, diffed, and emitted as correct DDL.

## First-Class Features

"First-class" means the round-trip is verified: reverse-engineer a live database with `generate-models`, feed the output back into `make-migrations`, and get **zero diff**.

```bash
# Step 1: reverse-engineer your live ClickHouse database
dbwarden generate-models -d analytics

# Step 2: feed the generated models back in, zero diff
dbwarden make-migrations -d analytics
# -> "No new migrations to generate"  (output is empty; your models match the DB exactly)
```

The following ClickHouse features are fully supported in this round-trip:

| Category | Features |
|----------|----------|
| Engine Spec | `MergeTree`, `ReplicatedMergeTree`, `SummingMergeTree`, `AggregatingMergeTree`, `CollapsingMergeTree`, `VersionedCollapsingMergeTree`, `ReplacingMergeTree`, `Distributed` via `ChEngineSpec(name, args, zookeeper_path, replica_name, settings)` |
| Ordering | `ORDER BY (col1, col2)` via `ch_order_by` (string or list) |
| Primary Key | `PRIMARY KEY (col1)` via `ch_primary_key` (must be prefix of order by) |
| Partitioning | `PARTITION BY toYYYYMM(col)` via `ch_partition_by` |
| Sampling | `SAMPLE BY intHash64(col)` via `ch_sample_by` |
| TTL | Table and column TTL via `ch_ttl` as list of expressions |
| Settings | `SETTINGS index_granularity=8192` via `ch_settings` dict |
| Materialized Views | `CREATE MATERIALIZED VIEW ... TO target AS SELECT ...` via `ch_select_statement`, `ch_to_table` |
| Projections | `PROJECTION name (SELECT ...)` via `ProjectionSpec` list |
| Dictionaries | `CREATE DICTIONARY ... SOURCE(...) LIFETIME(...) LAYOUT(...)` via `ch_dict_*` fields |
| Skip Indexes | `ALTER TABLE ... ADD INDEX ... TYPE bloom_filter GRANULARITY N` via `index()` factory with `clickhouse_type` / `clickhouse_granularity` |
| Column Codecs | `CODEC(ZSTD(3))` via `ch_codec` on `CHColumnMeta` |
| LowCardinality / Nullable | Type wrappers via `ch_low_cardinality`, `ch_nullable` on `CHColumnMeta` |
| Column Defaults | `DEFAULT expr`, `MATERIALIZED expr`, `ALIAS expr` via column Meta |
| Type Normalization | `VARCHAR` -> `String`, `INTEGER` -> `Int32`, `BIGINT` -> `Int64`, `FLOAT(53)` -> `Float64`, `NUMERIC(p,s)` -> `Decimal(p,s)`, `BOOLEAN` -> `Bool`, `ARRAY(Integer)` -> `Array(Int32)`, `Enum` -> `Enum8/Enum16`, `UUID` -> `UUID`, `JSON` -> `JSON`, `DATETIME` -> `DateTime` / `DateTime64` |
| Auto-detect | `generate-models` auto-enables ClickHouse engine metadata when `database_type="clickhouse"` (no `--clickhouse-engines` flag needed) |
| Snapshot | Full `system.tables` / `system.columns` extraction with CH metadata in `ch_options` and `ch_column` |

## Declaring Metadata

ClickHouse metadata is declared in a `class Meta` inner class on the model. This is the **only** supported surface. Pass options via `mapped_column(info=...)` raises `DBWardenConfigError`.

### Table-Level Meta

Inherit from `CHTableMeta` on your `class Meta`:

```python
from dbwarden import Base, CHTableMeta, ChEngineSpec, ProjectionSpec, index

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    event_date = Column(Date)
    payload = Column(String)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = ["event_date", "id"]
        ch_primary_key = "event_date"
        ch_partition_by = "toYYYYMM(event_date)"
        ch_sample_by = "intHash64(id)"
        ch_ttl = ["event_date + toIntervalYear(1)"]
        ch_settings = {"index_granularity": "8192"}
        comment = "Core event store"
```

`CHTableMeta` inherits from `TableMeta`, which provides common attributes shared across all backends:

| Attribute | Type | SQL |
|-----------|------|-----|
| `comment` | `str` | `COMMENT ON TABLE t IS '...'` |
| `indexes` | `list[IndexSpec]` | Skip indexes via `index()` factory |
| `checks` | `list[dict]` | `ALTER TABLE t ADD CONSTRAINT ... CHECK (...)` |
| `uniques` | `list[dict]` | `ALTER TABLE t ADD CONSTRAINT ... UNIQUE (...)` |

ClickHouse-specific `CHTableMeta` attributes:

| Attribute | Type | SQL |
|-----------|------|-----|
| `ch_engine` | `ChEngineSpec` | `ENGINE = MergeTree()` (or other engine) |
| `ch_order_by` | `str` or `list[str]` | `ORDER BY (col1, col2)` |
| `ch_primary_key` | `str` or `list[str]` | `PRIMARY KEY (col1)` (must be prefix of order by) |
| `ch_partition_by` | `str` | `PARTITION BY toYYYYMM(col)` |
| `ch_sample_by` | `str` | `SAMPLE BY intHash64(col)` |
| `ch_ttl` | `list[str]` | `TTL expr1, expr2` |
| `ch_settings` | `dict[str, str]` | `SETTINGS key=value` (emitted last) |
| `ch_object_type` | `str` | `"table"`, `"materialized_view"`, or `"dictionary"` (auto-detected) |
| `ch_select_statement` | `str` | `AS SELECT ...` for materialized views |
| `ch_to_table` | `str` | `TO target_table` for materialized views |
| `ch_dictionary` | `bool` | Whether this model is a dictionary |
| `ch_dict_layout` | `str` | Dictionary layout (e.g., `"FLAT()"`) |
| `ch_dict_source` | `str` | Dictionary source (e.g., `"CLICKHOUSE(TABLE 'src')"`) |
| `ch_dict_lifetime` | `int` or `str` | Dictionary cache lifetime |
| `ch_dict_primary_key` | `str` or `list[str]` | Dictionary primary key |
| `ch_projections` | `list[ProjectionSpec]` | Named projections |
| `ch_zookeeper_path` | `str` | ZooKeeper path for replicated engines |
| `ch_replica_name` | `str` | Replica name for replicated engines |

### Engine Spec

Use `ChEngineSpec` to define the table engine:

```python
from dbwarden import ChEngineSpec

# Simple engine
ch_engine = ChEngineSpec("MergeTree")

# Engine with positional arguments
ch_engine = ChEngineSpec("ReplacingMergeTree", args=("version_column",))

# Replicated engine with ZooKeeper path and replica name
ch_engine = ChEngineSpec("ReplicatedMergeTree",
    zookeeper_path="/clickhouse/tables/shard1/events",
    replica_name="{replica}")

# Distributed engine with settings
ch_engine = ChEngineSpec("Distributed",
    args=("cluster", "db", "events", "rand()"),
    settings={"insert_distributed_sync": "1"})
```

The `ChEngineSpec` constructor fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Engine name (e.g., `"MergeTree"`, `"ReplicatedMergeTree"`) |
| `args` | `tuple[str, ...]` | Positional engine arguments |
| `zookeeper_path` | `str` or `None` | ZooKeeper path (injected as first engine arg) |
| `replica_name` | `str` or `None` | Replica name (injected as second engine arg) |
| `settings` | `dict[str, str]` or `None` | `SETTINGS key=value` pairs |

### Projections

Use `ProjectionSpec` in `ch_projections` to attach named projections:

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

### Skip Indexes

Use the `index()` factory with `clickhouse_type` and `clickhouse_granularity`:

```python
from dbwarden import index

class Meta(CHTableMeta):
    indexes = [
        index("ix_payload", "payload",
            clickhouse_type="bloom_filter",
            clickhouse_granularity=1),
        index("ix_url", "url",
            clickhouse_type="minmax",
            clickhouse_granularity=3),
    ]
```

Generated SQL:

```sql
ALTER TABLE events ADD INDEX ix_payload (payload) TYPE bloom_filter GRANULARITY 1
ALTER TABLE events ADD INDEX ix_url (url) TYPE minmax GRANULARITY 3
```

### Column-Level Meta

Use `CHColumnMeta` inner classes for per-column metadata. The inner class must be named after the column:

```python
from dbwarden import Base, CHTableMeta, CHColumnMeta, ChEngineSpec

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    payload = Column(String)
    event_time = Column(DateTime)
    tags = Column(ARRAY(String))

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = "event_time"

        class payload(CHColumnMeta):
            ch_codec = "ZSTD(3)"
            ch_nullable = False

        class tags(CHColumnMeta):
            ch_low_cardinality = True

        class event_time(CHColumnMeta):
            ch_default_expression = "now()"
```

`CHColumnMeta` includes common column attributes shared across all backends:

| Attribute | Type | SQL |
|-----------|------|-----|
| `comment` | `str` | `COMMENT ON COLUMN t.c IS '...'` |
| `public` | `bool` | Controls field visibility in schemap auto-schema |

ClickHouse-specific `CHColumnMeta` attributes:

| Attribute | Type | SQL |
|-----------|------|-----|
| `ch_codec` | `str` | `CODEC(ZSTD(3))` |
| `ch_default_expression` | `str` | `DEFAULT expr` |
| `ch_materialized` | `str` | `MATERIALIZED expr` |
| `ch_alias` | `str` | `ALIAS expr` |
| `ch_ttl` | `str` | Column-level TTL expression |
| `ch_low_cardinality` | `bool` | Wrap type in `LowCardinality(...)` |
| `ch_nullable` | `bool` | Wrap type in `Nullable(...)` |

### Materialized Views

Materialized views use `ch_select_statement` instead of `ch_engine` for the target:

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

When `ch_to_table` is set, the generated SQL omits the `ENGINE` clause (ClickHouse rejects `ENGINE` with `TO` clause):

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS event_rollup_mv TO dbwarden.mv_target (
    event_date Date NOT NULL,
    total Int64 NOT NULL
)
AS SELECT toDate(event_time) AS event_date, count() AS total FROM events GROUP BY event_date
```

### Dictionaries

ClickHouse dictionaries use `ch_dictionary = True` and related `ch_dict_*` fields:

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

Generated SQL:

```sql
CREATE DICTIONARY IF NOT EXISTS country_codes (
    code Int64,
    name String
)
PRIMARY KEY code
SOURCE(CLICKHOUSE(HOST 'localhost' TABLE 'countries'))
LIFETIME(MIN 0 MAX 3600)
LAYOUT(FLAT())
```

Column types render as CH-native types (`Int64`, `String`) rather than SQLAlchemy types (`BIGINT`, `VARCHAR`).

## DDL Behavior

### ADD COLUMN / DROP COLUMN

Standard `ALTER TABLE ... ADD COLUMN` and `ALTER TABLE ... DROP COLUMN` work for ClickHouse. Column types render as CH-native type names (e.g., `ALTER TABLE events ADD COLUMN value Float64 NOT NULL`).

### ALTER COLUMN DEFAULT

ClickHouse supports `ALTER TABLE ... MODIFY COLUMN ... DEFAULT ...` (and `DROP DEFAULT`) which maps to the standard `SET DEFAULT` / `DROP DEFAULT` pattern.

### ALTER COLUMN TYPE

ClickHouse supports in-place `ALTER TABLE ... MODIFY COLUMN ... type` for compatible type changes (e.g., `Int32` to `Int64`). Incompatible type changes (e.g., `String` to `Int64`) require table recreation.

### ALTER TABLE MODIFY SETTING

Not all `SETTINGS` are dynamic. Some settings require table recreation. Review the ClickHouse documentation for your version to confirm which settings are `MODIFY SETTING` compatible.

### DDL Transactional Behavior

ClickHouse executes DDL statements individually. There is no transactional DDL; partial failure during a multi-statement migration can leave the schema in an inconsistent state. Each statement is applied atomically, but there is no rollback across statements.

### Statement Ordering

The standard statement ordering applies to ClickHouse. Operations that emit comments (table rename, safe type change) produce zero-effect placeholders. The ordering ensures the upgrade script remains structurally consistent even when backends skip operations.

## What Emits Comments Only

Several DDL operations are not supported by ClickHouse. DBWarden emits SQL comment placeholders suggesting manual action.

### ALTER TABLE RENAME

ClickHouse does not support `ALTER TABLE ... RENAME TO`. A comment is emitted.

```sql
-- ClickHouse does not support ALTER TABLE RENAME.
-- Manually rename users TO accounts in ClickHouse.
```

### Safe Type Change

`--safe-type-change` is not supported for ClickHouse. The multi-step temp-column strategy emits a comment.

```sql
-- ClickHouse safe type change not supported.
-- Manually recreate users with new type for bio.
```

### Foreign Keys

ClickHouse does not enforce foreign key constraints. Any FK add/drop operations emit a comment-only placeholder. Table recreation is typically required to add or remove FKs in ClickHouse.

### Indexes (Standard)

Standard SQL indexes are not supported. Only ClickHouse skip indexes (declared via `index()` with `clickhouse_type`) generate real DDL. See [Skip Indexes](#skip-indexes) above.

## Snapshot Format

The snapshot JSON captures all ClickHouse-specific metadata. Key sections:

### Column Extras

```json
{
  "name": "payload",
  "type": "String",
  "ch_column": {
    "ch_codec": "ZSTD(3)",
    "ch_default_expression": null,
    "ch_materialized": null,
    "ch_alias": null,
    "ch_ttl": null,
    "ch_low_cardinality": false,
    "ch_nullable": false,
    "ch_type": "String"
  }
}
```

### Table Extras

```json
{
  "ch_options": {
    "ch_engine_raw": {"name": "MergeTree", "args": [], "zookeeper_path": null, "replica_name": null, "settings": null},
    "ch_engine": ["MergeTree"],
    "ch_order_by": ["event_date", "id"],
    "ch_primary_key": ["event_date"],
    "ch_partition_by": "toYYYYMM(event_date)",
    "ch_sample_by": null,
    "ch_ttl": ["event_date + toIntervalYear(1)"],
    "ch_settings": {"index_granularity": "8192"},
    "ch_object_type": "table",
    "ch_projections": [{"name": "by_date", "query": "SELECT event_date, sum(amount) GROUP BY event_date"}],
    "ch_zookeeper_path": null,
    "ch_replica_name": null
  }
}
```

## Reverse Engineering

`generate-models` queries `system.tables`, `system.columns`, and `system.data_skipping_indices` to reverse-engineer all ClickHouse metadata. The emitted model uses `class Meta` with `CHTableMeta`, `CHColumnMeta`, `ChEngineSpec`, and `ProjectionSpec`.

```bash
dbwarden generate-models -d analytics
```

Auto-detection is the default: when `database_type="clickhouse"`, engine metadata is included automatically. The `--clickhouse-engines` flag is no longer required.

Generated output for a table with engine, ordering, partitioning, codec, and projections:

```python
from dbwarden import Base, CHTableMeta, CHColumnMeta, ChEngineSpec, ProjectionSpec

class Event(Base):
    __tablename__ = "events"

    id = Column(Int64, primary_key=True)
    event_date = Column(Date)
    payload = Column(String)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by = ["event_date", "id"]
        ch_partition_by = "toYYYYMM(event_date)"
        ch_ttl = ["event_date + toIntervalYear(1)"]
        ch_settings = {"index_granularity": "8192"}
        ch_projections = [
            ProjectionSpec("by_date", "SELECT event_date, sum(amount) GROUP BY event_date"),
        ]

        class payload(CHColumnMeta):
            ch_codec = "ZSTD(3)"
```

## Safety Classification

| Change Type | Severity | Flag Required |
|-------------|----------|---------------|
| Add column | `INFO` | None |
| Drop column | `WARNING` | `--force` |
| Change column type (ch_type) | `CRITICAL` | `--force` |
| Change column codec | `WARN` | None |
| Change column default | `WARN` | None |
| Change column TTL | `WARN` | None |
| Change LowCardinality / Nullable | `CRITICAL` | `--force` |
| Change engine | `CRITICAL` | `--force` |
| Change order by | `CRITICAL` | `--force` |
| Change partition by | `WARN` | `--force` |
| Change sample by | `INFO` | None |
| Change TTL | `INFO` | None |
| Change settings | `WARN` | `--force` |
| Change object type | `CRITICAL` | `--force` |
| Change dictionary layout / source / lifetime | `WARN` | `--force` |
| Add projection | `INFO` | None |
| Drop projection | `WARNING` | `--force` |
| Add skip index | `INFO` | None |
| Drop skip index | `WARNING` | `--force` |
| Add materialized view | `INFO` | None |
| Drop materialized view | `CRITICAL` | `--force` |

## Verification Workflow

Because ClickHouse diverges from standard SQL DDL, always review auto-generated migrations before applying:

```bash
dbwarden make-migrations -d analytics
dbwarden migrate -d analytics
```

Use `dbwarden make-migrations --plan -d analytics` to preview the ops without writing files.

See [models.md](../models.md) for detailed ClickHouse model examples and [Modeling Guide](../tutorial/modeling.md) for a complete walkthrough.
