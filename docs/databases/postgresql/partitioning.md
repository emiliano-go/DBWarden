# Partitioning

**Handler**: `PartitionHandler` (DIFF phase)

Partitioning is declared on `PGTableMeta` and requires the table to be a true PostgreSQL partitioned table (not traditional inheritance).

## Declaring a Partitioned Table

```python
class Meta(PGTableMeta):
    pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}
```

### Partition Strategies

| Strategy | Description |
|----------|-------------|
| `RANGE` | Partition by range of values on one or more columns |
| `LIST` | Partition by discrete values |
| `HASH` | Partition by hash of values |

### Partition Columns

```python
# Range partition by date
pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}

# List partition by category
pg_partition = {"strategy": "LIST", "columns": ["category"]}

# Hash partition by id
pg_partition = {"strategy": "HASH", "columns": ["id"]}
```

## Attaching Partitions

Child partitions are declared via `pg_partitions`:

```python
class Meta(PGTableMeta):
    pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}
    pg_partitions = [
        {"name": "events_2024_q1", "bound": "FOR VALUES FROM ('2024-01-01') TO ('2024-04-01')"},
        {"name": "events_2024_q2", "bound": "FOR VALUES FROM ('2024-04-01') TO ('2024-07-01')"},
    ]
```

Partitions are automatically attached/detached during migration.

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Declare partition | `ALTER TABLE parent ATTACH PARTITION child FOR VALUES ...;` |
| Detach partition | `ALTER TABLE parent DETACH PARTITION child;` |
| Change strategy | Manual rewrite required (commented in DDL) |

## Inheritance vs Partitioning

PartitionHandler only tracks tables with `pg_partition` declared (true PG partitioning). Traditional inheritance (`pg_inherits`) is handled separately via `PgTableHandler`.
