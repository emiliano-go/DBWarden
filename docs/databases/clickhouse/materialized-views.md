---
seo:
  title: Materialized views - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views
  robots: index,follow
  og:
    type: website
    title: Materialized views - DBWarden Documentation
    description: 'Plain MVs: two shapes'
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Materialized views - DBWarden Documentation
    description: 'Plain MVs: two shapes'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Plain MVs: two shapes'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Materialized views - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views
    description: 'Plain MVs: two shapes'
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
      name: Materialized Views
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views
seo_html: "<title>Materialized views - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Plain MVs: two shapes\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views\">\n<meta\
  \ name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Materialized views - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Plain MVs: two shapes\"\
  >\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Materialized views - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Plain MVs: two shapes\">\n<meta\
  \ name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Materialized views - DBWarden Documentation\",\n    \"url\":\
  \ \"https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views\",\n\
  \    \"description\": \"Plain MVs: two shapes\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Materialized Views\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/materialized-views\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Materialized views

## Plain MVs: two shapes

### Mode A: Class IS the target table (preferred)

The view class IS the target table; `__tablename__` is the table name.
The MV is auto-generated as `f"{__tablename__}_mv"`.  Columns, engine, and
`order_by` are required for Mode A (engine is enforced; columns and
`order_by` are strongly recommended but not strictly validated).

Columns are declared via `mapped_column` on the class.  Although no
SQLAlchemy `Base` is needed; the class is NOT a SQLAlchemy model, and
`session.query(ClassName)` will *not* work; the column descriptors are
read from `cls.__dict__` by the discovery pipeline.

```python
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from dbwarden.databases.clickhouse import MaterializedView, CHViewMeta, materialized_view, merge_tree

class EventCount(MaterializedView):
    __tablename__ = "event_counts"

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
CREATE TABLE event_counts (date Date, count Int64)
ENGINE = MergeTree() ORDER BY date

CREATE MATERIALIZED VIEW event_counts_mv TO event_counts
AS SELECT sum(amount) AS total FROM events
```

### Mode B: Explicit `to=` target

The class IS the MV; it writes to a pre-existing target table.  No columns,
no engine, no `order_by`; the target owns its own storage.

```python
from sqlalchemy import func
from dbwarden.databases.clickhouse import MaterializedView, CHViewMeta, materialized_view

class EventCountMV(MaterializedView):
    __tablename__ = "event_counts_mv"

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="events_dest",
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW event_counts_mv TO events_dest
AS SELECT sum(amount) AS total FROM events
```

## Refreshable MVs (24.3+)

```python
class DailyRollupMV(MaterializedView):
    __tablename__ = "daily_rollup_mv"

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="rollup_dest",
            refresh="EVERY 3600 SECONDS",
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW daily_rollup_mv TO rollup_dest
REFRESH EVERY 3600 SECONDS
AS SELECT sum(amount) AS total FROM events
```

Refreshable MVs (introduced in CH 24.3) replace LIVE VIEW and support:

- Periodic refresh (`EVERY n SECONDS`)
- Refresh dependencies (`DEPENDS ON`) embedded in the `refresh=` string
- Empty vs populating initial state

These options are combined in a single `refresh` string:

```python
refresh="EVERY 3600 SECONDS DEPENDS ON my_other_mv"
```

Refresh on cluster is configured at the deployment level via `--cluster-mode`.

## Additional model examples

### Refreshable MV with DEPENDS ON

```python
class HourlyRollupMV(MaterializedView):
    __tablename__ = "hourly_rollup_mv"

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Event.amount).label("total"),
            to="hourly_rollup_dest",
            refresh="EVERY 300 SECONDS DEPENDS ON daily_rollup_mv",
        )
```

Generated DDL:

```sql
CREATE MATERIALIZED VIEW hourly_rollup_mv TO hourly_rollup_dest
REFRESH EVERY 300 SECONDS DEPENDS ON daily_rollup_mv
AS SELECT sum(amount) AS total FROM events
```

### MV on clustered setup

```python
class ClusterMV(MaterializedView):
    __tablename__ = "cluster_mv"

    class Meta(CHViewMeta):
        ch = materialized_view(
            select="SELECT hostName() AS node, count(*) AS cnt FROM events",
            to="cluster_mv_dest",
        )
```

### MV chaining (MV reading from MV)

```python
# First MV: raw -> hourly
class RawToHourlyMV(MaterializedView):
    __tablename__ = "raw_to_hourly_mv"
    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(Raw.value).label("total"),
            to="hourly_dest",
        )

# Second MV: hourly -> daily
class HourlyToDailyMV(MaterializedView):
    __tablename__ = "hourly_to_daily_mv"
    class Meta(CHViewMeta):
        ch = materialized_view(
            select=func.sum(HourlyDest.total).label("total"),
            to="daily_dest",
        )
```

## What the `.inner` table is

When an MV has no `TO target` (deprecated module-level form only), ClickHouse
creates a hidden table named ``.inner.<view_name>`` with the MV's result
schema.  dbwarden reverse-engineers this table during ``generate-models``.

The class API **does not support** implicit ``.inner.`` storage; every
MV must either be the target (Mode A) or name a target (Mode B).  The
``.inner.`` form appears only when reverse-engineering legacy MVs that were
created outside dbwarden.

## `MODIFY QUERY` vs recreate

ClickHouse supports `ALTER TABLE ... MODIFY QUERY` for refreshable MVs. For
plain (non-refreshable) MVs, the query is immutable: any change requires a
DROP + CREATE.

dbwarden classifies this as:

| MV type | `MODIFY QUERY` | Safety |
|---------|----------------|--------|
| Refreshable | Supported | INFO |
| Plain (non-refreshable) | Not supported by CH | CRITICAL: requires `--force` |

## `POPULATE` as data operation

`POPULATE` is a one-time statement that inserts existing source data into the
MV on creation. dbwarden treats it as a
[data operation](data-operations.md), not a DDL property:

```python
from dbwarden.databases.clickhouse import data_ops
from dbwarden.databases.clickhouse.materialized_view import materialized_view

spec = materialized_view(
    name="event_counts_mv",
    select="SELECT sum(amount) AS total FROM events",
    to="events_dest",
)
pop = data_ops.populate(spec)
```

This is because `POPULATE` is a write concern, not a structural declaration:
it runs once during creation and changes nothing about the schema.

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

MV DROP is a rollback of MV CREATE. Data created by the MV is not restored by
rollback of the DDL: you must re-POPULATE.
