# Aggregating views

Use `ch_agg_state`, `ch_agg_merge`, and the `agg()` namespace to declare AggregatingMergeTree-targeted views with the correct `-State` / `-Merge` correspondence.

## Declaration

```python
from dbwarden.databases.clickhouse import ch, agg

class EventsHourly(Base):
    __tablename__ = "events_hourly"
    hour: Mapped[datetime] = mapped_column()
    state: Mapped[tuple] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=aggregating_merge_tree(),
            order_by="hour",
            ch_select="""
                SELECT toStartOfHour(event_time) AS hour,
                       agg.sumState(payload_size) AS state
                FROM events
                GROUP BY hour
            """,
        )
```

The `agg` namespace (`agg.sumState`, `agg.countState`, `agg.uniqState`, `agg.anyState`, `agg.anyHeavyState`, `agg.minState`, `agg.maxState`, `agg.avgState`, `agg.groupArrayState`, `agg.groupArrayInsertAtState`, `agg.groupUniqArrayState`, `agg.topKState`, `agg.quantileState`, `agg.quantilesState`, `agg.quantileDeterministicState`, `agg.quantileTimingState`, `agg.quantileTDigestState`, `agg.quantileBFloat16State`, `agg.quantileBFloat16WeightedState`, `agg.medianState`, `agg.covarSampState`, `agg.covarPopState`, `agg.corrState`) provides typed state-returning aggregate wrappers.

## Additional model examples

### Multiple aggregate states in one MV

```python
class EventStats(Base):
    __tablename__ = "event_stats"

    date: Mapped[date] = mapped_column()
    sum_state: Mapped[tuple] = mapped_column()
    uniq_state: Mapped[tuple] = mapped_column()
    topk_state: Mapped[tuple] = mapped_column()
    quantile_state: Mapped[tuple] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=aggregating_merge_tree(),
            order_by="date",
            ch_select="""
                SELECT toDate(event_time) AS date,
                       agg.sumState(amount) AS sum_state,
                       agg.uniqState(user_id) AS uniq_state,
                       agg.topKState(10)(page) AS topk_state,
                       agg.quantileState(0.95)(latency_ms) AS quantile_state
                FROM events
                GROUP BY date
            """,
        )
```

Query the result:

```sql
SELECT
    date,
    sumMerge(sum_state) AS total_revenue,
    uniqMerge(uniq_state) AS unique_users,
    topKMerge(10)(topk_state) AS top_pages,
    quantileMerge(0.95)(quantile_state) AS p95_latency
FROM event_stats
GROUP BY date
```

### Two-stage aggregation over ReplicatedMergeTree

```python
# Stage 1: per-shard aggregation
class ShardStats(Base):
    __tablename__ = "shard_stats"
    date: Mapped[date] = mapped_column()
    state: Mapped[tuple] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=aggregating_merge_tree(),
            order_by="date",
            ch_select="SELECT toDate(ts) AS date, agg.sumState(val) AS state FROM raw GROUP BY date",
        )

# Stage 2: final merge across shards
class GlobalStats(Base):
    __tablename__ = "global_stats"
    date: Mapped[date] = mapped_column()
    total: Mapped[float] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by="date",
            ch_select="SELECT date, sumMerge(state) AS total FROM shard_stats GROUP BY date",
        )
```

### With explicit column types

```python
class SessionMetrics(Base):
    __tablename__ = "session_metrics"
    date: Mapped[date] = mapped_column()
    duration_state: Mapped[tuple] = mapped_column()
    page_state: Mapped[tuple] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=aggregating_merge_tree(),
            order_by="date",
            ch_select="""
                SELECT session_date AS date,
                       agg.avgState(duration_seconds) AS duration_state,
                       agg.groupArrayState(page_url) AS page_state
                FROM sessions
                GROUP BY date
            """,
        )
```

Query:

```sql
SELECT
    date,
    avgMerge(duration_state) AS avg_duration,
    groupArrayMerge(page_state) AS pages
FROM session_metrics
GROUP BY date
```

## The `-State` / `-Merge` correspondence

Every `agg.*State(col)` call maps to `aggFunctionState, aggFunction)` type. The SELECT in the MV uses `-State`, the SELECT in the final query uses `-Merge`:

| State function | Merge function | Type |
|---------------|----------------|------|
| `agg.sumState(x)` | `sumMerge(state)` | `AggregateFunction(sum, T)` |
| `agg.countState(x)` | `countMerge(state)` | `AggregateFunction(count, T)` |
| `agg.uniqState(x)` | `uniqMerge(state)` | `AggregateFunction(uniq, T)` |
| `agg.avgState(x)` | `avgMerge(state)` | `AggregateFunction(avg, T)` |
| `agg.minState(x)` | `minMerge(state)` | `AggregateFunction(min, T)` |
| `agg.maxState(x)` | `maxMerge(state)` | `AggregateFunction(max, T)` |
| `agg.quantileState(x)` | `quantileMerge(state)` | `AggregateFunction(quantile, T)` |
| `agg.topKState(x)` | `topKMerge(state)` | `AggregateFunction(topK, T)` |

A downstream query reads from the aggregating table using `-Merge`:

```sql
SELECT hour, sumMerge(state) FROM events_hourly GROUP BY hour
```

## What changes are allowed

| Change | Safety |
|--------|--------|
| Add/drop aggregating table | WARN |
| Change aggregate function | CRITICAL: incompatible state |
| Change source column type | CRITICAL: AggregateFunction signature locked |
| Change ORDER BY | Append-only |

## Rollback behavior

Changing an aggregate function changes the type of the state column. Since `AggregateFunction(sum, Float64)` vs `AggregateFunction(avg, Float64)` are different types, the change requires a full recreate. See [Immutability](immutability.md) for the type-lock explanation.
