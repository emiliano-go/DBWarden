---
seo:
  title: MergeTree engine family - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree
  robots: index,follow
  og:
    type: website
    title: MergeTree engine family - DBWarden Documentation
    description: Factories
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: MergeTree engine family - DBWarden Documentation
    description: Factories
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Factories
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: MergeTree engine family - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree
    description: Factories
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
      name: Engines Mergetree
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree
seo_html: "<title>MergeTree engine family - DBWarden Documentation</title>\n<meta\
  \ name=\"description\" content=\"Factories\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"MergeTree engine family - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Factories\">\n<meta\
  \ property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"MergeTree engine family - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Factories\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"MergeTree engine family - DBWarden Documentation\",\n    \"url\"\
  : \"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree\",\n\
  \    \"description\": \"Factories\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Engines Mergetree\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-mergetree\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# MergeTree engine family

## Factories

All MergeTree variants have typed factory functions in `dbwarden.databases.clickhouse`:

```python
from dbwarden.databases.clickhouse import (
    merge_tree, replacing_merge_tree, replicated_merge_tree,
    summing_merge_tree, aggregating_merge_tree,
    collapsing_merge_tree, versioned_collapsing_merge_tree,
    graphite_merge_tree,
)
```

| Factory | Engine name | Signature |
|---------|-------------|-----------|
| `merge_tree()` | `MergeTree` | `()` |
| `replacing_merge_tree(ver?)` | `ReplacingMergeTree` | `(version_col: str \| None = None)` |
| `replicated_merge_tree(zk, replica, ...)` | `ReplicatedMergeTree` | `(zookeeper_path, replica_name, *args)` |
| `summing_merge_tree(...)` | `SummingMergeTree` | `(*columns: str)` |
| `aggregating_merge_tree()` | `AggregatingMergeTree` | `()` |
| `collapsing_merge_tree(sign)` | `CollapsingMergeTree` | `(sign_col: str)` |
| `versioned_collapsing_merge_tree(sign, ver)` | `VersionedCollapsingMergeTree` | `(sign_col, version_col)` |
| `graphite_merge_tree(section?)` | `GraphiteMergeTree` | `(config_section: str = "default")` |

Example:

```python
class Meta(CHTableMeta):
    ch = ch_table(
        engine=replicated_merge_tree(
            "/clickhouse/tables/events",
            "{replica}",
            "ver",
        ),
        order_by=["event_date", "id"],
    )
```

Generated DDL:

```sql
CREATE TABLE events (
    event_date Date,
    id Int64
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/events', '{replica}', 'ver')
ORDER BY (event_date, id)
```

## MergeTreeSettings

`ch_table(settings=MergeTreeSettings(...))` type-checks known MergeTree settings:

```python
from dbwarden.databases.clickhouse import MergeTreeSettings

settings: MergeTreeSettings = {
    "index_granularity": 8192,
    "ttl_only_drop_parts": True,
    "min_bytes_for_wide_part": 10485760,
}
```

Boolean values are automatically converted to `"0"` / `"1"`. Integer values are stringified. All values are rendered as strings before reaching the server.

## What changes are allowed

| Property | Allowed |
|----------|---------|
| Engine variant | Only with `--force` (full recreate) |
| ZK path / replica name | Only with `--force` |
| Settings | Any key-value via `MODIFY SETTING` (where supported by server) |
| ORDER BY | Append-only |
| PARTITION BY | Never |

## Additional model examples

### ReplacingMergeTree with version column

```python
class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    price: Mapped[float] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=replacing_merge_tree(version_col="updated_at"),
            order_by="sku",
        )
```

Deduplicates by `sku`, keeping the row with the latest `updated_at`.

### CollapsingMergeTree for mutable state

```python
class OrderState(Base):
    __tablename__ = "order_state"

    order_id: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column()
    amount: Mapped[float] = mapped_column()
    sign: Mapped[int8] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=collapsing_merge_tree(sign_col="sign"),
            order_by="order_id",
        )
```

Cancellations emit a row with `sign = -1` that collapses with the original `sign = 1`.

### SummingMergeTree

```python
class DailySummary(Base):
    __tablename__ = "daily_summary"

    dt: Mapped[date] = mapped_column()
    product: Mapped[str] = mapped_column()
    revenue: Mapped[float] = mapped_column()
    units: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=summing_merge_tree("revenue"),
            order_by=["dt", "product"],
        )
```

`revenue` and `units` are summed automatically during merge.

### GraphiteMergeTree

```python
class GraphiteMetrics(Base):
    __tablename__ = "graphite_metrics"

    path: Mapped[str] = mapped_column()
    value: Mapped[float] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=graphite_merge_tree(config_section="rollup_default"),
            order_by=["path", "timestamp"],
            partition_by="toYYYYMM(timestamp)",
        )
```

## Rollback behavior

Engine changes with `--force` trigger the full recreate pipeline. See [Safety](safety.md).
