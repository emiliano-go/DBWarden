# `generate-models`

Reverse-engineer SQLAlchemy model code from a live database.

## Usage

```bash
dbwarden generate-models --output ./models/ --database primary
dbwarden generate-models --output ./models/ --database primary --single-file
dbwarden generate-models --database primary --tables users,posts
dbwarden generate-models --database primary --exclude-tables logs,audit
```

## Options

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Output directory (default: `models`) |
| `--tables` | Comma-separated list of tables to include |
| `--exclude-tables` | Comma-separated list of tables to exclude |
| `--clickhouse-engines` | Include ClickHouse engine metadata. Auto-detected when `database_type="clickhouse"` |
| `--relationships` | Generate `relationship()` attributes for foreign keys |
| `--dialect` | SQL dialect for type mapping (auto-detected from database type) |
| `--single-file` | Generate a single `models.py` instead of one file per table |
| `--database`, `-d` | Target database name |

## Output rules

- **Default**: one `.py` file per table (e.g., `users.py`, `posts.py`)
- **`--single-file`**: generates `models.py` with all models
- Each file imports `declarative_base()` and defines `Base`

## Type mapping

Database column types are mapped to SQLAlchemy types:

| Database Type | SQLAlchemy Type |
|---------------|----------------|
| `INTEGER` | `Integer` |
| `VARCHAR(N)` | `String(length=N)` |
| `TEXT` | `Text` |
| `BOOLEAN` / `TINYINT(1)` | `Boolean` |
| `DECIMAL(P,S)` | `Numeric(precision=P, scale=S)` |
| `DATETIME` / `TIMESTAMP` | `DateTime` |
| `BIGINT` | `BigInteger` |
| `FLOAT` / `DOUBLE` | `Float` |
| `Nullable(...)` (ClickHouse) | Inner type (nullable is explicit) |

## PostgreSQL First-Class Output

For PostgreSQL databases, `generate-models` reverse-engineers all supported metadata and emits it as `class Meta` inner classes with `PGTableMeta` and `PGColumnMeta`:

```python
from dbwarden import Base, PGTableMeta, PGColumnMeta

class User(Base):
    __tablename__ = "users"

    id:    Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    bio:   Mapped[str | None] = mapped_column(Text, nullable=True)

    class Meta(PGTableMeta):
        comment = "Core user accounts"
        pg_fillfactor = 80

        class id(PGColumnMeta):
            pg_identity = "always"
            pg_identity_start = 100
            pg_identity_increment = 1

        class bio(PGColumnMeta):
            pg_storage = "EXTENDED"
            pg_collation = "en_US.UTF-8"
```

The following metadata is reverse-engineered:

- **Identity columns**: `GENERATED ALWAYS/BY DEFAULT AS IDENTITY` with sequence options
- **Collation**: per-column `COLLATE` setting
- **Storage**: per-column `STORAGE` (PLAIN, MAIN, EXTERNAL, EXTENDED)
- **Generated columns**: `GENERATED ALWAYS AS (...) STORED`
- **Table fillfactor**: `WITH (fillfactor = N)`
- **Tablespace**: `SET TABLESPACE`
- **Inheritance**: `INHERITS (parent)`
- **EXCLUDE constraints**: `EXCLUDE USING ...`
- **FK options**: `ondelete`, `onupdate`, `deferrable` on `ForeignKey()`
- **Index options**: `USING`, `WHERE`, `INCLUDE`, `WITH`, `TABLESPACE`, `NULLS NOT DISTINCT`
- **Table and column comments**

For the complete feature reference, see [PostgreSQL Deep Dive](../databases/postgresql.md).

## ClickHouse First-Class Output

For ClickHouse databases, `generate-models` reverse-engineers all supported metadata and emits it as `class Meta` inner classes with `CHTableMeta`, `CHColumnMeta`, `ChEngineSpec`, and `ProjectionSpec`. Engine metadata is included automatically when `database_type="clickhouse"` (no `--clickhouse-engines` flag required).

```python
from dbwarden import Base, CHTableMeta, CHColumnMeta, ChEngineSpec, ProjectionSpec

class Event(Base):
    __tablename__ = "events"

    id:    Mapped[int] = mapped_column(Int64, primary_key=True)
    event_date: Mapped[date] = mapped_column(Date)
    payload: Mapped[str] = mapped_column(String)

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

The following metadata is reverse-engineered:

- **Engine spec**: engine name, arguments, ZooKeeper path, replica name, settings via `ChEngineSpec`
- **Ordering and partitioning**: `ch_order_by`, `ch_primary_key`, `ch_partition_by`, `ch_sample_by`
- **TTL**: table-level TTL expressions
- **Projections**: named projections via `ProjectionSpec`
- **Materialized views**: `ch_select_statement`, `ch_to_table`
- **Dictionaries**: `ch_dictionary`, `ch_dict_layout`, `ch_dict_source`, `ch_dict_lifetime`, `ch_dict_primary_key`
- **Column metadata**: codec, default expression, LowCardinality/Nullable wrappers via `CHColumnMeta`
- **Skip indexes**: `index()` with `clickhouse_type`, `clickhouse_granularity`
- **Table and column comments**

For the complete feature reference, see [ClickHouse Deep Dive](../databases/clickhouse.md).

## Use cases

- **Bootstrapping**: start a new project from an existing database
- **Documentation**: generate model stubs to document the schema
- **Recovery**: regenerate models when migration scripts are missing

## Warnings

- Generated code requires manual review and cleanup
- ClickHouse engine metadata is auto-detected; review the generated `ChEngineSpec` to ensure correctness
