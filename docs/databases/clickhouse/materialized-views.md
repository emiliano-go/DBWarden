# Materialized views

## Plain MVs

Use `materialized_view()` in `class Meta` with `CHViewMeta`:

```python
from sqlalchemy import func, Column, Date, Float64
from dbwarden.databases.clickhouse import CHViewMeta, materialized_view, merge_tree

class EventCount(Base):
    __tablename__ = "event_counts"

    date: Mapped[date] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="events_dest",
        )
```

Two storage shapes, which diff differently:

| Shape | `to` | `engine` / `order_by` | DDL |
|-------|-----------|----------------------|-----|
| **Explicit target** | Set | Not needed (target owns storage) | `CREATE MATERIALIZED VIEW ... TO target AS SELECT ...` |
| **Implicit `.inner`** | `None` | Required | `CREATE MATERIALIZED VIEW ... ENGINE = MergeTree() ORDER BY ... AS SELECT ...` |

Explicit target (preferred):

```python
class EventCount(Base):
    __tablename__ = "event_counts"

    date: Mapped[date] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="events_dest",
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW event_counts TO events_dest
AS SELECT sum(amount) AS total FROM events GROUP BY event_date
```

Implicit `.inner` storage: engine and order_by are required:

```python
class EventCountInner(Base):
    __tablename__ = "event_counts_inner"

    date: Mapped[date] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            engine=merge_tree(),
            order_by=["date"],
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW event_counts_inner
ENGINE = MergeTree() ORDER BY date
AS SELECT sum(amount) AS total FROM events GROUP BY event_date
```

The `.inner` table is created automatically by ClickHouse and reverse-engineered as a separate model.

## Refreshable MVs (24.3+)

```python
class DailyRollup(Base):
    __tablename__ = "daily_rollup"

    date: Mapped[date] = mapped_column(primary_key=True)
    total: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="rollup_dest",
            refresh="EVERY 3600 SECONDS",
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW daily_rollup TO rollup_dest
REFRESH EVERY 3600 SECONDS
AS SELECT sum(amount) AS total FROM events GROUP BY event_date
```

Refreshable MVs (introduced in CH 24.3) replace LIVE VIEW and support:
- Periodic refresh (`EVERY n SECONDS`)
- Refresh dependencies (`DEPENDS ON`)
- Refresh on cluster (`ON CLUSTER`)
- Empty vs populating initial state

## Additional model examples

### Refreshable MV with DEPENDS ON

```python
class HourlyRollup(Base):
    __tablename__ = "hourly_rollup"

    hour: Mapped[datetime] = mapped_column(primary_key=True)
    total_events: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="hourly_rollup_dest",
            refresh="EVERY 300 SECONDS",
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW hourly_rollup TO hourly_rollup_dest
REFRESH EVERY 300 SECONDS
AS SELECT sum(amount) AS total FROM events GROUP BY event_date
```

### MV on clustered setup

```python
class ClusterMV(Base):
    __tablename__ = "cluster_mv"

    node: Mapped[str] = mapped_column(primary_key=True)
    cnt: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select="SELECT hostName() AS node, count(*) AS cnt FROM events",
            to="cluster_mv_dest",
        )
```

### MV chaining (MV reading from MV)

```python
# First MV: raw -> hourly
class RawToHourly(Base):
    __tablename__ = "raw_to_hourly"
    hour: Mapped[datetime] = mapped_column(primary_key=True)
    total: Mapped[float] = mapped_column()
    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Raw.value).label("total"),
            to="hourly_dest",
        )

# Second MV: hourly -> daily
class HourlyToDaily(Base):
    __tablename__ = "hourly_to_daily"
    date: Mapped[date] = mapped_column(primary_key=True)
    total: Mapped[float] = mapped_column()
    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(HourlyDest.total).label("total"),
            to="daily_dest",
        )
```

## What the `.inner` table is

When an MV has no `TO target`, ClickHouse creates a hidden table named `.inner.<view_name>` with the MV's result schema. dbwarden reverse-engineers this table during `generate-models`. You can declare columns on the MV model and they populate the `.inner` table's DDL:

```python
class EventMV(Base):
    __tablename__ = "event_mv"

    date: Mapped[date] = mapped_column(primary_key=True)
    total: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            engine=merge_tree(),
            order_by=["date"],
        )
```

## `MODIFY QUERY` vs recreate

ClickHouse supports `ALTER TABLE ... MODIFY QUERY` for refreshable MVs. For plain (non-refreshable) MVs, the query is immutable: any change requires a DROP + CREATE.

dbwarden classifies this as:

| MV type | `MODIFY QUERY` | Safety |
|---------|----------------|--------|
| Refreshable | Supported | INFO |
| Plain (non-refreshable) | Not supported by CH | CRITICAL: requires `--force` |

## `POPULATE` as data operation

`POPULATE` is a one-time statement that inserts existing source data into the MV on creation:

```sql
CREATE MATERIALIZED VIEW mv_populate TO dest
POPULATE
AS SELECT ...
```

dbwarden treats `POPULATE` as a [data operation](data-operations.md), not a DDL property. It is part of `ch_data_ops`, not `materialized_view()`:

```python
from dbwarden.databases.clickhouse import data_ops

def deploy_mv():
    with data_ops() as ops:
        ops.populate("mv_populate")
```

This is because `POPULATE` is a write concern, not a structural declaration: it runs once during creation and changes nothing about the schema.

## What changes are allowed

| Change | Safety |
|--------|--------|
| Add/drop MV | WARN |
| Change `TO` target | CRITICAL: requires recreate |
| Change SELECT (non-refreshable) | CRITICAL: requires recreate |
| Change SELECT (refreshable) | INFO |
| Change refresh interval | INFO |
| Toggle POPULATE | Data-op, not structural |

## Rollback behavior

MV DROP is a rollback of MV CREATE. Data created by the MV is not restored by rollback of the DDL: you must re-POPULATE.
