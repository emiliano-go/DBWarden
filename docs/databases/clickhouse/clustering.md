# Clustering

## ON CLUSTER

For cluster-wide DDL, set `cluster_mode` on the table or config:

```python
from dbwarden.databases.clickhouse import ClusterMode

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=replicated_merge_tree("/zk/table", "{replica}"),
            order_by=["id"],
            cluster_mode=ClusterMode.ON_CLUSTER,
        )
```

Generated DDL:

```sql
CREATE TABLE events ON CLUSTER '{cluster}' (
    id Int64
) ENGINE = ReplicatedMergeTree('/zk/table', '{replica}')
ORDER BY id
```

`ClusterMode.ON_CLUSTER` appends `ON CLUSTER '{cluster}'` to every DDL statement emitted for this object.

## ClusterMode.REPLICATED

```python
class Meta(CHTableMeta):
    ch = ch_table(
        engine=replicated_merge_tree("/zk/table", "{replica}"),
        cluster_mode=ClusterMode.REPLICATED,
    )
```

This mode omits `ON CLUSTER`: the engine handles replication via ZK. DDL statements reference only the local node.

Use `REPLICATED` when the database is already `Replicated`.

## Additional model examples

### ON CLUSTER with Distributed engine

```python
class LocalEvents(Base):
    __tablename__ = "local_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=replicated_merge_tree("/zk/events", "{replica}"),
            order_by="id",
            cluster_mode=ClusterMode.ON_CLUSTER,
        )

class GlobalEvents(Base):
    __tablename__ = "global_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=distributed_engine(
                cluster="analytics_cluster",
                database="analytics",
                table="local_events",
                sharding_key="id",
            ),
            cluster_mode=ClusterMode.ON_CLUSTER,
        )
```

Generated DDL for `local_events`:

```sql
CREATE TABLE local_events ON CLUSTER '{cluster}' (
    id Int64,
    data String
) ENGINE = ReplicatedMergeTree('/zk/events', '{replica}')
ORDER BY id
```

Generated DDL for `global_events`:

```sql
CREATE TABLE global_events ON CLUSTER '{cluster}' (
    id Int64,
    data String
) ENGINE = Distributed('analytics_cluster', 'analytics', 'local_events', id)
```

### REPLICATED mode with Replicated database

```python
# When the database itself is ENGINE = Replicated, use REPLICATED mode:
class ReplicatedDBTable(Base):
    __tablename__ = "replicated_db_table"
    id: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),  # not ReplicatedMergeTree!
            order_by="id",
            cluster_mode=ClusterMode.REPLICATED,
        )
```

DDL emits without `ON CLUSTER` because the database engine handles replication.

### Toggle between modes

```python
# From ON_CLUSTER to REPLICATED (requires --force)
class Meta(CHTableMeta):
    ch = ch_table(
        engine=replicated_merge_tree("/zk/t", "{replica}"),
        order_by="id",
        # cluster_mode=ClusterMode.ON_CLUSTER,  # old
        cluster_mode=ClusterMode.REPLICATED,      # new
    )
```

dbwarden classifies this as CRITICAL and requires `--force`.

## Gap: Replicated database is extraction-only

`CREATE DATABASE ... ENGINE = Replicated` is not declared by dbwarden. dbwarden operates *within* a database: it reads the database-level engine from the server's response during reverse-engineering but does not emit `CREATE DATABASE` statements.

When the server database is `Replicated`, dbwarden detects this and uses the `REPLICATED` cluster mode behavior (no `ON CLUSTER`). This is automatic: no config key is needed.

## What changes are allowed

| Change | Safety |
|--------|--------|
| Toggle `ON_CLUSTER` ↔ `REPLICATED` | CRITICAL: changes DDL emission |
| Change cluster name (config) | INFO |
| ZK path change | CRITICAL: requires recreate |

## Rollback behavior

Cluster mode changes are structural: they affect all emitted DDL for the database and require careful migration planning. The rollback restores the previous cluster mode.

## Config keys

```python
from dbwarden import database_config

database_config(
    name="analytics",
    url="clickhouse://...",
    ch_cluster="analytics_cluster",  # Config-wide cluster name
)
```
