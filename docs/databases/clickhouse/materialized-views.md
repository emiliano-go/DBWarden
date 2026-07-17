# Materialized views

## Plain MVs

```python
from sqlalchemy import Column, Integer, String, Text
from dbwarden.databases.clickhouse import ch

class EventCount(Base):
    __tablename__ = "event_counts"

    date: Mapped[date] = mapped_column()
    count: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        # If you set ch_to_table, the MV writes to an explicit table.
        # If you omit it, ClickHouse creates an implicit .inner table.
        ch = ch_table(
            engine=merge_tree(),
            order_by=["date"],
            ch_to_table="events_dest",
            ch_select="SELECT event_date AS date, count(*) AS count FROM events GROUP BY event_date",
        )
```

Generated DDL with explicit target:

```sql
CREATE MATERIALIZED VIEW event_counts TO events_dest
AS SELECT event_date AS date, count(*) AS count FROM events
GROUP BY event_date
```

Generated DDL with implicit `.inner` (no `ch_to_table`):

```sql
CREATE MATERIALIZED VIEW event_counts
AS SELECT event_date AS date, count(*) AS count FROM events
GROUP BY event_date
```

The `.inner` table is created automatically by ClickHouse and reverse-engineered as a separate model. You can customize its engine via `ch_inner_engine`.

## Refreshable MVs (24.3+)

```python
class DailyRollup(Base):
    __tablename__ = "daily_rollup"

    date: Mapped[date] = mapped_column()
    total: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by="date",
            ch_to_table="rollup_dest",
            ch_select="SELECT event_date, sum(amount) FROM raw GROUP BY event_date",
            ch_refresh_interval=3600,  # seconds
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW daily_rollup TO rollup_dest
REFRESH EVERY 3600 SECONDS
AS SELECT event_date, sum(amount) FROM raw
GROUP BY event_date
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

    hour: Mapped[datetime] = mapped_column()
    total_events: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by="hour",
            ch_to_table="hourly_rollup_dest",
            ch_select="""
                SELECT toStartOfHour(event_time) AS hour,
                       count(*) AS total_events
                FROM raw_events
                GROUP BY hour
            """,
            ch_refresh_interval=300,  # every 5 minutes
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW hourly_rollup TO hourly_rollup_dest
REFRESH EVERY 300 SECONDS
AS SELECT toStartOfHour(event_time) AS hour, count(*) AS total_events
FROM raw_events GROUP BY hour
```

### MV on clustered setup

```python
class ClusterMV(Base):
    __tablename__ = "cluster_mv"

    node: Mapped[str] = mapped_column()
    cnt: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by="node",
            ch_to_table="cluster_mv_dest",
            ch_select="SELECT hostName() AS node, count(*) AS cnt FROM events",
            cluster_mode=ClusterMode.ON_CLUSTER,
        )
```

### MV chaining (MV reading from MV)

```python
# First MV: raw -> hourly
class RawToHourly(Base):
    __tablename__ = "raw_to_hourly"
    hour: Mapped[datetime] = mapped_column()
    total: Mapped[float] = mapped_column()
    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(), order_by="hour",
            ch_to_table="hourly_dest",
            ch_select="SELECT toStartOfHour(ts) AS hour, sum(val) AS total FROM raw GROUP BY hour",
        )

# Second MV: hourly -> daily
class HourlyToDaily(Base):
    __tablename__ = "hourly_to_daily"
    date: Mapped[date] = mapped_column()
    total: Mapped[float] = mapped_column()
    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(), order_by="date",
            ch_to_table="daily_dest",
            ch_select="SELECT toDate(hour) AS date, sum(total) AS total FROM hourly_dest GROUP BY date",
        )
```

## What the `.inner` table is

When an MV has no `TO target`, ClickHouse creates a hidden table named `.inner.<view_name>` with the MV's result schema. dbwarden reverse-engineers this table during `generate-models`. You can declare columns on the MV model and they populate the `.inner` table's DDL:

```python
class EventMV(Base):
    __tablename__ = "event_mv"

    date: Mapped[date] = mapped_column()
    total: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by="date",
            ch_select="SELECT event_date AS date, count(*) AS total FROM events GROUP BY event_date",
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

dbwarden treats `POPULATE` as a [data operation](data-operations.md), not a DDL property. It is part of `ch_data_ops`, not `ch_table()`:

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
