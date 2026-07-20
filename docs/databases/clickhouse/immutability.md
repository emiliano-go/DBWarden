---
seo:
  title: 'Immutability: what can never change - DBWarden Documentation'
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/immutability
  robots: index,follow
  og:
    type: website
    title: 'Immutability: what can never change - DBWarden Documentation'
    description: This page is the single most important thing to read before writing
      your first ClickHouse model. PG users expect most properties to be mutable via
      ALTER....
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/immutability
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: 'Immutability: what can never change - DBWarden Documentation'
    description: This page is the single most important thing to read before writing
      your first ClickHouse model. PG users expect most properties to be mutable via
      ALTER....
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: This page is the single most important thing to read before writing
    your first ClickHouse model. PG users expect most properties to be mutable via
    ALTER....
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: 'Immutability: what can never change - DBWarden Documentation'
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/immutability
    description: This page is the single most important thing to read before writing
      your first ClickHouse model. PG users expect most properties to be mutable via
      ALTER....
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
      name: ClickHouse
      item: https://dbwarden.emiliano-go.com/databases/clickhouse
    - '@type': ListItem
      position: 3
      name: Immutability
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/immutability
seo_html: "<title>Immutability: what can never change - DBWarden Documentation</title>\n\
  <meta name=\"description\" content=\"This page is the single most important thing\
  \ to read before writing your first ClickHouse model. PG users expect most properties\
  \ to be mutable via ALTER....\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/immutability\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Immutability: what can never change\
  \ - DBWarden Documentation\">\n<meta property=\"og:description\" content=\"This\
  \ page is the single most important thing to read before writing your first ClickHouse\
  \ model. PG users expect most properties to be mutable via ALTER....\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/immutability\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Immutability: what can never change -\
  \ DBWarden Documentation\">\n<meta name=\"twitter:description\" content=\"This page\
  \ is the single most important thing to read before writing your first ClickHouse\
  \ model. PG users expect most properties to be mutable via ALTER....\">\n<meta name=\"\
  twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Immutability: what can never change - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/immutability\"\
  ,\n    \"description\": \"This page is the single most important thing to read before\
  \ writing your first ClickHouse model. PG users expect most properties to be mutable\
  \ via ALTER....\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Immutability\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/immutability\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Immutability: what can never change

This page is the single most important thing to read before writing your first ClickHouse model. PG users expect most properties to be mutable via `ALTER`. ClickHouse is different: many properties are design-time commitments that can never be changed, and others require a full table rebuild.

## Model example: table with immutable properties

```python
class Orders(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column()
    amount: Mapped[float] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by=["created_at", "id"],
            partition_by="toYYYYMM(created_at)",
            primary_key=["id"],
            sample_by="intHash64(id)",
        )
```

Once applied, `partition_by`, `primary_key`, `sample_by` and `engine` can never be altered. Only `order_by` can be extended by appending new columns: `["created_at", "id"]` → `["created_at", "id", "status"]`.

## What can never change

| Property | Constraint | Mechanism |
|----------|------------|-----------|
| `PARTITION BY` | Cannot be altered after creation | ClickHouse does not support `ALTER TABLE MODIFY PARTITION BY`. The only fix is a full table rebuild. |
| `PRIMARY KEY` | Cannot be altered | Unlike PG where you can `ALTER TABLE ... SET WITHOUT CLUSTER`, ClickHouse's primary key is baked into the storage order at creation. |
| `SAMPLE BY` | Cannot be altered | Same as partition by: set at CREATE time only. |
| `ENGINE` | Cannot be `ALTER`ed | Changing `MergeTree` to `ReplicatedMergeTree` (or vice versa) requires a full data copy. See below. |

## What extends only

| Property | Behavior | Example |
|----------|----------|---------|
| `ORDER BY` | New columns can be appended to the end. Existing columns cannot be removed or reordered. | `ORDER BY (a, b)` → `ORDER BY (a, b, c)` is valid. `ORDER BY (b, a)` is not. |

This is enforced by dbwarden: the differ refuses an `ORDER BY` change that is not an append-only extension. If you try, you get a CRITICAL-safety classification and must use `--force` to trigger a recreate.

## Model example: change requiring recreate

This ORDER BY change is refused by dbwarden:

```python
# Current model
class Meta(CHTableMeta):
    ch = ch_table(
        engine=replicated_merge_tree("/zk/orders", "{replica}"),
        order_by=["created_at", "id"],
    )

# Attempted change (reordered, not append-only)
class Meta(CHTableMeta):
    ch = ch_table(
        engine=replicated_merge_tree("/zk/orders", "{replica}"),
        order_by=["id", "created_at"],  # REORDERED: not append-only
    )
```

dbwarden emits: `CRITICAL: Changing ORDER BY from (created_at, id) to (id, created_at) requires --force`. The correct extension:

```python
class Meta(CHTableMeta):
    ch = ch_table(
        order_by=["created_at", "id", "status"],  # append-only: OK
    )
```

## What requires `--force` (recreate)

These properties trigger the recreate pipeline (DETACH source → CREATE new → INSERT INTO ... SELECT → RENAME → ATTACH) when changed:

| Change | Safety |
|--------|--------|
| Engine change (including ZK path / replica name) | CRITICAL |
| ORDER BY non-extension change (remove/reorder columns) | CRITICAL |
| PRIMARY KEY change | CRITICAL |
| PARTITION BY change | CRITICAL |
| SAMPLE BY change | INFO |
| Object type change (`table` ↔ `materialized_view`) | CRITICAL |
| MV target (`ch_to_table`) change | CRITICAL |
| Column type change (incompatible) | CRITICAL |
| LowCardinality / Nullable wrapper change | CRITICAL |

### Model example: full recreate with AggregateFunction

```python
# Source column type change triggers MV recreate
# Current: amount is Float64
class Meta(CHTableMeta):
    ch = ch_table(
        engine=merge_tree(),
        order_by="date",
        ch_select="SELECT date, agg.sumState(amount) AS state FROM events GROUP BY date",
    )

# If amount changes to Float32, the AggregateFunction signature changes:
#   AggregateFunction(sum, Float64) -> AggregateFunction(sum, Float32)
# This is CRITICAL and requires --force + recreate
```

**The 40GB-vs-500GB rebuild argument.** A 40GB table recreates in minutes. A 500GB table needs planning: provision a second table, backfill, verify, swap. dbwarden's recreate pipeline handles the orchestration but the cost is real. Test on a staging environment first.

## AggregateFunction signatures are incompatible state

`AggregateFunction(sum, Float64)` and `AggregateFunction(sum, Float32)` are different types. An MV that selects `sum(value)` where `value` is `Float64` produces `AggregateFunction(sum, Float64)`. If the source column type changes, the MV's aggregate type is locked: it cannot be `ALTER`ed to `Float32`. The only fix is to drop and recreate the MV.

This is not a dbwarden limitation: it is ClickHouse's columnar storage model. dbwarden will flag it as a CRITICAL change requiring a recreate.

## What dbwarden refuses entirely

dbwarden will not emit `ALTER TABLE ... MODIFY ORDER BY` for a non-extension change. It will refuse to emit `ALTER TABLE ... MODIFY PARTITION BY` (ClickHouse doesn't support it). It will refuse to emit an engine change without the recreate flag.

The error messages name the constraint and the flag required to override:
```
CRITICAL: Changing ORDER BY from (a, b) to (c, d) requires --force and
triggers a full table recreate (DETACH -> CREATE -> INSERT -> ATTACH).
```
