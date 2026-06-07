# ClickHouse

DBWarden supports ClickHouse as an analytics backend. ClickHouse uses SQL syntax but has a fundamentally different DDL model from traditional relational databases. This page explains how DBWarden handles ClickHouse-specific behavior and what limitations apply.

## Connection Model

ClickHouse uses an HTTP-based wire protocol. DBWarden resolves the `clickhouse://` URL and creates a ClickHouse-specific client (`AsyncClient`/`Client`) instead of a standard SQLAlchemy session. Internal URL normalization converts the `clickhouse://` scheme to the `clickhouse+http://` dialect expected by the SQLAlchemy ClickHouse driver.

```
clickhouse://user:pass@host:8123/dbname?param=value
```

## What Works

### CREATE TABLE with Engine Settings

DBWarden generates `CREATE TABLE` statements with full ClickHouse engine metadata from SQLAlchemy model `__table_args__`:

```python
class Analytics(Base):
    __tablename__ = "events"
    __table_args__ = (
        {"clickhouse_engine": "ReplicatedMergeTree"},
        {"clickhouse_order_by": "(timestamp, event_type)"},
        {"clickhouse_partition_by": "toYYYYMM(timestamp)"},
        {"clickhouse_primary_key": "(timestamp)"},
        {"clickhouse_sample_by": "rand()"},
        {"clickhouse_ttl": "timestamp + INTERVAL 90 DAY"},
        {"clickhouse_zookeeper_path": "/clickhouse/tables/events"},
        {"clickhouse_replica_name": "{replica}"},
    )
```

If no engine is configured, DBWarden falls back to `ENGINE = MergeTree()`.

### ADD COLUMN / DROP COLUMN

Standard `ALTER TABLE ... ADD COLUMN` and `ALTER TABLE ... DROP COLUMN` work for ClickHouse.

### ALTER COLUMN DEFAULT

ClickHouse supports `ALTER TABLE ... MODIFY COLUMN ... DEFAULT ...` (and `DROP DEFAULT`) which maps to the standard `SET DEFAULT` / `DROP DEFAULT` pattern.

### Model Discovery

DBWarden reverse-engineers ClickHouse models via `generate-models --clickhouse-engines`. Without `--clickhouse-engines`, engine metadata may be missing from generated models.

### Materialized Views, Projections, Dictionaries

- **Materialized views**: set `clickhouse_mv=True` and `clickhouse_mv_query` on the model
- **Projections**: pass `clickhouse_projections=list[...]` in `__table_args__`
- **Dictionaries**: set `clickhouse_dictionary=True` with `clickhouse_dict_layout`, `clickhouse_dict_source`, and `clickhouse_dict_lifetime`

### Snapshot Command

The `snapshot` command extracts the raw `CREATE TABLE` query from `system.tables` for ClickHouse, rather than using SQLAlchemy reflection.

## What Emits Comments Only

Several DDL operations are not supported by ClickHouse. DBWarden emits SQL comment placeholders suggesting manual action.

### ALTER TABLE RENAME

ClickHouse does not support `ALTER TABLE ... RENAME TO`. The rename table operation emits a comment:

```sql
-- ClickHouse does not support ALTER TABLE RENAME.
-- Manually rename users TO accounts in ClickHouse.
```

### ALTER COLUMN TYPE

ClickHouse does not support in-place `ALTER COLUMN TYPE`. A comment is emitted:

```sql
-- ClickHouse does not support ALTER COLUMN TYPE.
-- Use dbwarden new to write a manual migration for:
-- ALTER TABLE users ALTER COLUMN name TYPE TEXT
```

### ALTER COLUMN NULLABLE

ClickHouse handles nullability through the column type (e.g., `Nullable(String)` vs `String`). In-place SET/DROP NOT NULL is not supported; a comment is emitted.

### Foreign Keys

ClickHouse does not enforce foreign key constraints. Any FK add/drop operations emit a comment-only placeholder.

Table recreation is typically required to add or remove FKs in ClickHouse.

### Indexes

ClickHouse uses a different indexing model (skip indices, bloom filters) that does not map to standard `CREATE INDEX`.

When a model `Index` has `clickhouse_type` set in `Index.info` (e.g., `info={"clickhouse_type": "minmax", "clickhouse_granularity": 3}`), DBWarden generates real ClickHouse DDL:

```sql
ALTER TABLE table ADD INDEX idx_name (col1, col2) TYPE minmax GRANULARITY 3
```

If `clickhouse_type` is not specified, index add/drop operations emit a comment placeholder instead.

### Safe Type Change

`--safe-type-change` is not supported for ClickHouse. The multi-step temp-column strategy emits a comment:

```sql
-- ClickHouse safe type change not supported.
-- Manually recreate users with new type for bio.
```

## DDL Transactional Behavior

ClickHouse executes DDL statements individually. There is no transactional DDL — partial failure during a multi-statement migration can leave the schema in an inconsistent state. Each statement is applied atomically, but there is no rollback across statements.

## Statement Ordering

The standard statement ordering applies to ClickHouse, but operations that emit comments (rename table, alter type, alter nullable, FK, index) produce zero-effect placeholders. The ordering ensures that the upgrade script remains structurally consistent even when backends skip operations.

## Verification Workflow

Because ClickHouse significantly diverges from standard SQL DDL, always review auto-generated migrations before applying:

```bash
dbwarden make-migrations -d analytics
dbwarden migrate -d analytics
```

Use `dbwarden make-migrations --plan -d analytics` to preview the ops without writing files.

See [models.md](../models.md) for detailed ClickHouse model examples.
