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

## ClickHouse Model Metadata

When `database_type="clickhouse"`, DBWarden can read ClickHouse-specific options from `__table_args__` and column `info` metadata.

### Table options

Supported keys:

- `clickhouse_engine`
- `clickhouse_order_by`
- `clickhouse_primary_key`
- `clickhouse_partition_by`
- `clickhouse_sample_by`
- `clickhouse_ttl`
- `clickhouse_mv`
- `clickhouse_mv_query`
- `clickhouse_mv_engine`
- `clickhouse_mv_order_by`
- `clickhouse_mv_populate`
- `clickhouse_projections`
- `clickhouse_zookeeper_path`
- `clickhouse_replica_name`

Example:

```python
class Event(Base):
    __tablename__ = "events"
    __table_args__ = {
        "clickhouse_engine": ("ReplacingMergeTree", "version_column"),
        "clickhouse_order_by": ["region", "event_time"],
        "clickhouse_primary_key": "region",
        "clickhouse_partition_by": "toYYYYMM(event_time)",
        "clickhouse_sample_by": "intHash64(user_id)",
        "clickhouse_ttl": [
            "event_time + INTERVAL 1 MONTH DELETE",
            "event_time + INTERVAL 1 YEAR TO DISK 'cold'",
        ],
    }
```

Notes:

- `clickhouse_engine="SummingMergeTree"` renders as `ENGINE = SummingMergeTree()`
- tuple/list engine values render positional arguments, for example `("ReplacingMergeTree", "version_column")`
- `clickhouse_primary_key` may be a string or ordered list/tuple, but it must be a prefix of `clickhouse_order_by`
- if no ClickHouse engine is configured, DBWarden currently falls back to `ENGINE = MergeTree()`

### Replicated engines

For Replicated\* engine tables, use `clickhouse_zookeeper_path` and `clickhouse_replica_name` alongside `clickhouse_engine`:

```python
class ReplicatedEvent(Base):
    __tablename__ = "replicated_events"
    __table_args__ = {
        "clickhouse_engine": "ReplicatedMergeTree",
        "clickhouse_zookeeper_path": "'/clickhouse/tables/shard1'",
        "clickhouse_replica_name": "'{replica}'",
        "clickhouse_order_by": ["event_time"],
        "clickhouse_partition_by": "toYYYYMM(event_time)",
    }
```

This renders as:

```sql
ENGINE = ReplicatedMergeTree('/clickhouse/tables/shard1', '{replica}')
```

`clickhouse_zookeeper_path` and `clickhouse_replica_name` are injected as the first two engine arguments. If the engine value is a tuple form like `("ReplicatedReplacingMergeTree", "ver_col")`, they are inserted before the existing positional arguments.

### Materialized views

Use `clickhouse_mv=True` to render a materialized view instead of a regular table:

```python
class EventRollup(Base):
    __tablename__ = "event_rollup_mv"
    __table_args__ = {
        "clickhouse_mv": True,
        "clickhouse_mv_query": "SELECT region, count() AS total FROM events GROUP BY region",
        "clickhouse_mv_engine": "SummingMergeTree",
        "clickhouse_mv_order_by": ["region"],
        "clickhouse_mv_populate": False,
    }
```

Notes:

- `clickhouse_mv_query` is required when `clickhouse_mv=True`
- `clickhouse_mv_populate=True` is supported but should be used cautiously
- materialized view SQL is rendered as `CREATE MATERIALIZED VIEW ... AS SELECT ...`

### Projections

Attach projections directly to a ClickHouse table:

```python
__table_args__ = {
    "clickhouse_order_by": ["author", "created_at"],
    "clickhouse_projections": [
        {"name": "by_author", "query": "SELECT * ORDER BY author"},
        {"name": "daily_stats", "query": "SELECT toDate(created_at) AS day, count() GROUP BY day"},
    ],
}
```

Current behavior:

- projection definitions are rendered into generated ClickHouse DDL
- safety checks classify added projections as `INFO`
- removed projections are classified as `WARNING`

### Dictionaries

ClickHouse dictionaries are defined as model classes with `clickhouse_dictionary=True` in `__table_args__`:

```python
class CountryCode(Base):
    __tablename__ = "country_codes"
    __table_args__ = {
        "clickhouse_dictionary": True,
        "clickhouse_dict_layout": "FLAT()",
        "clickhouse_dict_source": "CLICKHOUSE(HOST 'localhost' TABLE 'countries')",
        "clickhouse_dict_lifetime": "MIN 0 MAX 3600",
        "clickhouse_dict_primary_key": "code",
    }
```

Required keys when `clickhouse_dictionary=True`:

| Key | Description | Example |
|-----|-------------|---------|
| `clickhouse_dict_layout` | Dictionary layout | `"FLAT()"`, `"COMPLEX_KEY_HASHED()"` |
| `clickhouse_dict_source` | Source configuration | `"CLICKHOUSE(HOST '...' TABLE '...')"` |
| `clickhouse_dict_lifetime` | Cache lifetime | `"MIN 0 MAX 3600"` or `3600` |

Optional key:

| Key | Description | Default |
|-----|-------------|---------|
| `clickhouse_dict_primary_key` | Primary key expression | First column |

Generated SQL:

```sql
CREATE DICTIONARY IF NOT EXISTS country_codes (
    code String,
    name String
)
PRIMARY KEY code
SOURCE(CLICKHOUSE(HOST 'localhost' TABLE 'countries'))
LIFETIME(MIN 0 MAX 3600)
LAYOUT(FLAT())
```

Current behavior:

- dictionary columns are defined like regular model columns; the first column is the default primary key
- safety checks classify new dictionaries as `INFO`
- dictionary source, layout, and lifetime changes are classified as `WARNING` (requires `--force`)

### Column hints

Use column `info` to attach ClickHouse-specific metadata:

```python
from sqlalchemy import Column, String

payload = Column(
    String,
    info={
        "clickhouse_type": "LowCardinality(String)",
        "clickhouse_codec": "ZSTD(3)",
    },
)
```

Supported column hints:

- `clickhouse_type`: explicit rendered type string
- `clickhouse_codec`: rendered as `CODEC(...)`

This is useful when:

- you are using a custom SQLAlchemy type that should render as a ClickHouse-specific SQL type
- you want explicit control over wrapper types like `LowCardinality(...)`, `Array(...)`, `Map(...)`, or `Tuple(...)`
- you need per-column compression settings
