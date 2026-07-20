---
seo:
  title: Partitioning - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/partitioning
  robots: index,follow
  og:
    type: website
    title: Partitioning - DBWarden Documentation
    description: 'Handler: PartitionHandler DIFF phase'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/partitioning
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Partitioning - DBWarden Documentation
    description: 'Handler: PartitionHandler DIFF phase'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Handler: PartitionHandler DIFF phase'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Partitioning - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/partitioning
    description: 'Handler: PartitionHandler DIFF phase'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
      logo: https://dbwarden.emiliano-go.com/assets/images/og-image.png
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Databases
      item: https://dbwarden.emiliano-go.com/databases
    - '@type': ListItem
      position: 2
      name: PostgreSQL
      item: https://dbwarden.emiliano-go.com/databases/postgresql
    - '@type': ListItem
      position: 3
      name: Partitioning
      item: https://dbwarden.emiliano-go.com/databases/postgresql/partitioning
seo_html: "<title>Partitioning - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Handler: PartitionHandler DIFF phase\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/databases/postgresql/partitioning\">\n<meta name=\"\
  robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\"\
  >\n<meta property=\"og:title\" content=\"Partitioning - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Handler: PartitionHandler DIFF phase\"\
  >\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/partitioning\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Partitioning - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Handler: PartitionHandler DIFF phase\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Partitioning - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/partitioning\"\
  ,\n    \"description\": \"Handler: PartitionHandler DIFF phase\",\n    \"image\"\
  : \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  ,\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Partitioning\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/partitioning\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

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

### Partition Bounds Syntax

| Strategy | Bound Syntax | Example |
|----------|-------------|---------|
| RANGE | `FROM (expr) TO (expr)` | `FROM ('2024-01-01') TO ('2024-04-01')` |
| LIST | `IN (value, ...)` | `IN ('active', 'pending')` |
| HASH | `MODULUS m, REMAINDER r` | `MODULUS 4, REMAINDER 0` |

RANGE bounds are half-open: the lower bound is inclusive, the upper bound is exclusive. Use `UNBOUNDED` for open-ended ranges:

```python
{"name": "events_archived", "bound": "FOR VALUES FROM ('2023-01-01') TO (MAXVALUE)"}
```

HASH partitions use modulus/remainder for round-robin distribution:

```python
{"name": "events_hash_0", "bound": "FOR VALUES WITH (MODULUS 4, REMAINDER 0)"},
{"name": "events_hash_1", "bound": "FOR VALUES WITH (MODULUS 4, REMAINDER 1)"},
{"name": "events_hash_2", "bound": "FOR VALUES WITH (MODULUS 4, REMAINDER 2)"},
{"name": "events_hash_3", "bound": "FOR VALUES WITH (MODULUS 4, REMAINDER 3)"},
```

### DEFAULT Partition

```python
{"name": "events_default", "bound": "DEFAULT"}
```

A DEFAULT partition catches all rows that do not match any other partition bound. Only one DEFAULT partition is allowed per partitioned table.

## Sub-Partitioning

Create partitions of partitions by declaring a partition strategy on a partition table:

```python
class Event(Base):
    __tablename__ = "events"
    ...

    class Meta(PGTableMeta):
        pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}
        pg_partitions = [
            {"name": "events_2024", "bound": "FOR VALUES FROM ('2024-01-01') TO ('2025-01-01')",
             "sub_partition": {"strategy": "LIST", "columns": ["category"]}},
        ]
```

Sub-partitions can use a different strategy than the parent. Each sub-partition level has its own `pg_partitions` entries.

## Indexes on Partitioned Tables

Creating an index on the parent table automatically creates matching indexes on all partitions:

```python
class Meta(PGTableMeta):
    pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}
    pg_indexes = [
        PgIndexSpec("ix_events_user_id", ["user_id"]),
    ]
```

The index is propagated to all existing and future partitions. Unique indexes (including PKs) must include the partition key.

## FK Constraints on Partitioned Tables

Foreign keys can reference a partitioned table (referencing the parent, referencing is routed to partitions). Foreign keys from a partitioned table must include the partition key:

```python
class OrderItem(Base):
    __tablename__ = "order_items"
    ...

    class Meta(PGTableMeta):
        pg_partition = {"strategy": "HASH", "columns": ["order_id"]}
```

FK from `order_items` to `orders` must include `order_id` in the FK columns.

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Declare partition | `ALTER TABLE parent ATTACH PARTITION child FOR VALUES ...;` |
| Detach partition | `ALTER TABLE parent DETACH PARTITION child;` |
| Detach concurrently (PG 16+) | `ALTER TABLE parent DETACH PARTITION child CONCURRENTLY;` |
| Change strategy | Manual rewrite required (commented in DDL) |

### DETACH CONCURRENTLY (PG 16+)

PostgreSQL 16+ supports `DETACH CONCURRENTLY`, which avoids the `ACCESS EXCLUSIVE` lock normally required:

```sql
ALTER TABLE events DETACH PARTITION events_2023 CONCURRENTLY;
```

The partition becomes an independent table. A background worker finalizes the detach. You can monitor with `pg_detach_pending` in `pg_partitioned_table`.

## Maintenance Operations

Individual partitions support the same maintenance as regular tables:

- `ANALYZE partition_name;` on each partition
- `VACUUM partition_name;` on each partition
- Index creation directly on a partition (not propagated to parent)
- Tablespace management per partition

## Inheritance vs Partitioning

PartitionHandler only tracks tables with `pg_partition` declared (true PG partitioning). Traditional inheritance (`pg_inherits`) is handled separately via `PgTableHandler`.

Partitioning vs Inheritance:

| Aspect | Partitioning | Inheritance |
|--------|-------------|-------------|
| Constraint exclusion | Automatic | Manual (CHECK constraints) |
| Unique constraints | Requires partition key | Supported across any columns |
| FK references | To parent only | To each child separately |
| Row movement | Possible (PG 17+) | Not supported |
| Sub-partitioning | Supported | Not supported |
