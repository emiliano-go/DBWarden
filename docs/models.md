# SQLAlchemy Models

DBWarden reads SQLAlchemy model metadata to generate migration SQL.

Use `model_paths` in your `database_config(...)` entries to control discovery.

Example:

```python
database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:pass@localhost:5432/main",
    model_paths=["app/models"],
)
```

Related docs:

- [Configuration](configuration.md)
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
