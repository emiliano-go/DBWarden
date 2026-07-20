---
seo:
  title: ClickHouse - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse
  robots: index,follow
  og:
    type: website
    title: ClickHouse - DBWarden Documentation
    description: DBWarden treats ClickHouse as a first-class backend. Every natively
      supported feature is reverse-engineered, diffed, and emitted as correct DDL.
    url: https://dbwarden.emiliano-go.com/databases/clickhouse
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: ClickHouse - DBWarden Documentation
    description: DBWarden treats ClickHouse as a first-class backend. Every natively
      supported feature is reverse-engineered, diffed, and emitted as correct DDL.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: DBWarden treats ClickHouse as a first-class backend. Every natively
    supported feature is reverse-engineered, diffed, and emitted as correct DDL.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: ClickHouse - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse
    description: DBWarden treats ClickHouse as a first-class backend. Every natively
      supported feature is reverse-engineered, diffed, and emitted as correct DDL.
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
seo_html: "<title>ClickHouse - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"DBWarden treats ClickHouse as a first-class backend. Every natively\
  \ supported feature is reverse-engineered, diffed, and emitted as correct DDL.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"ClickHouse - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"DBWarden treats ClickHouse as a first-class\
  \ backend. Every natively supported feature is reverse-engineered, diffed, and emitted\
  \ as correct DDL.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"ClickHouse - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"DBWarden treats ClickHouse as a\
  \ first-class backend. Every natively supported feature is reverse-engineered, diffed,\
  \ and emitted as correct DDL.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"ClickHouse - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\
  ,\n    \"description\": \"DBWarden treats ClickHouse as a first-class backend. Every\
  \ natively supported feature is reverse-engineered, diffed, and emitted as correct\
  \ DDL.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      }\n    ]\n  }\n]\n</script>\n"
---

# ClickHouse

DBWarden treats ClickHouse as a first-class backend. Every natively supported feature is reverse-engineered, diffed, and emitted as correct DDL.

**Before reading further:** ClickHouse's object model is fundamentally different from PostgreSQL. What is a `SET` in PG is often a `CREATE` commitment in CH. Read [Immutability](immutability.md) first.

## Quick-start

Set up a table, a materialized view, and an aggregated table:

```python
from datetime import date
from sqlalchemy import func, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.databases.clickhouse import (
    CHTableMeta, CHViewMeta, ch_table, ch,
    merge_tree, materialized_view, kafka, aggregating_view, agg,
    AggregatingView, MaterializedView,
)

class Base(DeclarativeBase):
    pass

# 1. Source table
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column()
    amount: Mapped[float] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by=["event_date", "id"],
            partition_by=func.toYYYYMM(Event.event_date),
        )

# 2. Materialized view: Mode A (class IS the target, MV is auto-generated)
class EventDaily(MaterializedView):
    __tablename__ = "event_daily"

    date: Mapped[date] = mapped_column(primary_key=True)
    total: Mapped[float] = mapped_column()
    cnt: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select="SELECT event_date AS date, sum(amount) AS total, "
                   "count(*) AS cnt FROM events GROUP BY event_date",
            engine=merge_tree(),
            order_by=["date"],
        )

# 3. Aggregating view: sources from EventDaily model
class EventAggregated(AggregatingView):
    __tablename__ = "event_aggregated"

    class Meta(CHViewMeta):
        ch = aggregating_view(
            source=EventDaily,
            group_by=[EventDaily.date],
            aggregates=[
                agg.sum(EventDaily.total, "Float64").as_("state"),
            ],
            order_by=[EventDaily.date],
        )
```

Generate DDL and apply:

```bash
dbwarden make-migrations -d analytics
dbwarden migrate -d analytics
```

This produces: `events` (source MergeTree), `event_daily` (target MergeTree), `event_daily_mv` (MV TO event_daily), `event_aggregated` (AggregatingMergeTree target), and `event_aggregated_mv` (MV TO event_aggregated). Query the final table:

```sql
SELECT date, sumMerge(state) FROM event_aggregated GROUP BY date
```

## Version support

| Version | Status | Evidence |
|---------|--------|----------|
| 24.3 | Verified | 39 audit cases, zero drift |
| 26.6 (latest) | Verified | Same 39 cases, zero drift |

The canonicalizer has **zero version branching**: a single code path covers 24.3–26.6. This is measured fact from the multi-version audit harness, not an assumption.

## Capability matrix

| Category | Feature | Status |
|----------|---------|--------|
| Engines | MergeTree family (8 variants) | Done |
| | Distributed, Buffer | Done |
| | Kafka, S3, S3Queue, RabbitMQ, NATS | Done |
| | MySQL, PostgreSQL, MongoDB, Redis | Done |
| | URL, File, HDFS | Done |
| | Null, Memory, Merge, Set, Join, Dictionary | Done |
| | Log, TinyLog, StripeLog | Done |
| Column features | Codecs, TTL, DEFAULT/MATERIALIZED/ALIAS | Done |
| | LowCardinality, Nullable wrappers | Done |
| | Type normalization | Done |
| | REMOVE clauses (CODEC, TTL, DEFAULT, MATERIALIZED, ALIAS, COMMENT) | Done |
| Compiled expressions | `render_expr()` accepts SQLAlchemy `ColumnElement`/`ChRaw`/`str` | Done |
| | Expression fields in all specs accept `ColumnElement` | Done |
| Table features | ORDER BY, PRIMARY KEY, PARTITION BY, SAMPLE BY | Done |
| | TTL (table + column) | Done |
| | Settings | Done |
| | Comments (table + column) | Done |
| | Projections, skip indexes | Done |
| Materialized views | Class-based API (`materialized_view()` + `CHViewMeta`) | Done |
| | TO target, implicit `.inner`, refreshable | Done |
| | MODIFY QUERY vs recreate | Done |
| | POPULATE (data-op) | Done |
| Dictionaries | CREATE DICTIONARY via ch_dict_* | Done |
| Aggregating views | Class-based API (`aggregating_view()` + `CHViewMeta`) | Done |
| | `agg()` namespace, `-State`/`-Merge` correspondence | Done |
| | Auto-expansion: single declaration → target + MV | Done |
| | `derive_agg_target_columns()` utility | Done |
| RBAC | Roles, users, settings profiles, quotas, row policies, grants | Done |
| | `storage != 'users.xml'` filter | Done |
| | Drop gating (`--clickhouse-allow-drop-rbac`) | Done |
| Named collections | Key-set diffed, values declare-only | Done |
| Clustering | ON CLUSTER via ClusterMode.ON_CLUSTER | Done |
| | ClusterMode.REPLICATED (emit-side: omit ON CLUSTER) | Done |
| Class-based views | `ChView`, `MaterializedView`, `AggregatingView` mixin bases | Done |
| | `CHViewMeta`: Meta class for view models | Done |
| | `get_all_ch_views()`: view discovery | Done |
| | `MaterializedViewSpec`: typed spec with expression compilation | Done |
| Safety | Classify options, column, and object changes | Done |
| | --force gating for destructive changes | Done |
| | Recreate pipeline (DETACH → CREATE → INSERT → ATTACH) | Done |
| Data ops | Partition ops, mutations, OPTIMIZE, POPULATE, secret rotation | Done |

## Deliberate exclusions

These are not gaps: they are deliberate boundaries, documented with reasoning so nobody wonders "why doesn't this work" or invents syntax to fill the vacuum.

| Feature | Reason |
|---------|--------|
| **Window View** | Requires `allow_experimental_window_view`. Experimental: DDL surface can change. Building a handler introduces the first version branch into the canonicalizer. Cost of waiting is near zero (MV-handler variant when it stabilizes). |
| **LIVE VIEW** | Experimental (`allow_experimental_live_view`), effectively abandoned, superseded by refreshable MVs (already supported). |
| **ANN (vector similarity) index** | Experimental (`allow_experimental_vector_similarity_index`). When stable it is a skip-index type addition: one Literal member, one audit case. Deferred, not excluded. |
| **Full-text index** | Experimental: the flag was renamed (`allow_experimental_inverted_index` → `allow_experimental_full_text_index`). The rename alone is the argument. Deferred. |
| **Replicated database engine** | dbwarden operates *within* a database, it does not provision databases. That is orchestration, same category as `config.xml`. |
| **SYSTEM commands** | Operational concern, not schema management. Not declarable in a model. |
| **Server config (`config.xml`)** | Infrastructure. Same boundary as PostgreSQL's `postgresql.conf`. |
| **Secret values** | Declare-only by design (see [named-collections](named-collections.md)). Values are not diffed. |

## Config keys

These are the **only** `database_config()` parameters for ClickHouse. Exact key shapes, documented because undocumented config keys are what assistants hallucinate.

```python
from dbwarden import database_config
from dbwarden.databases.clickhouse import (
    NamedCollectionSpec, named_collection,
    ChRoleSpec, ChUserSpec, ChRowPolicySpec,
    ChQuotaSpec, ChSettingsProfileSpec, ChGrantSpec,
)

database_config(
    name="analytics",
    url="clickhouse://...",
    ch_named_collections=[...],       # list[NamedCollectionSpec | dict]
    ch_roles=[...],                   # list[ChRoleSpec | dict]
    ch_users=[...],                   # list[ChUserSpec | dict]
    ch_row_policies=[...],            # list[ChRowPolicySpec | dict]
    ch_quotas=[...],                  # list[ChQuotaSpec | dict]
    ch_settings_profiles=[...],       # list[ChSettingsProfileSpec | dict]
    ch_grants=[...],                  # list[ChGrantSpec | dict]
)
```

## Model examples

### Partitioned time-series table with TTL

```python
class PageView(Base):
    __tablename__ = "page_views"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column()
    user_id: Mapped[int] = mapped_column()
    event_time: Mapped[datetime] = mapped_column()
    duration_ms: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=replicated_merge_tree("/zk/pv", "{replica}"),
            order_by=["event_time", "user_id"],
            partition_by="toYYYYMM(event_time)",
            ttl=["event_time + toIntervalMonth(6)"],
            settings={"index_granularity": 4096},
        )
```

### Table with codecs and column TTL

```python
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from dbwarden.databases.clickhouse import (
    CHColumnMeta, CHTableMeta, ch_table, ch,
    merge_tree,
)

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    sensor_id: Mapped[str] = mapped_column()
    ts: Mapped[datetime] = mapped_column()
    temp: Mapped[float] = mapped_column()
    humidity: Mapped[float] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by=["sensor_id", "ts"],
        )

        class temp(CHColumnMeta):
            ch = ch.field(codec="ZSTD(5)")

        class ts(CHColumnMeta):
            ch = ch.field(codec="DoubleDelta", ttl="ts + toIntervalDay(90)")

        class humidity(CHColumnMeta):
            ch = ch.field(ttl="ts + toIntervalDay(30)")
```

### Kafka ingestion with MV

```python
class KafkaEvents(Base):
    __tablename__ = "kafka_events"

    payload: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=kafka(
                named_collection="kafka_prod",
                topic="raw_events",
                format="JSONEachRow",
                group_name="dbwarden",
            ),
        )

class ParsedEvents(MaterializedView):
    __tablename__ = "parsed_events"

    class Meta(CHViewMeta):
        ch = materialized_view(
            select="""
                SELECT
                    JSONExtractString(payload, 'type') AS event_type,
                    JSONExtractFloat(payload, 'value') AS value,
                    JSONExtractDateTime(payload, 'ts') AS ts
                FROM kafka_events
            """,
            to="parsed_events_dest",
        )
```

### RBAC config

```python
database_config(
    name="analytics",
    url="clickhouse://localhost:9000",
    ch_named_collections=[
        named_collection("ldap_auth", ldap_server="ldap.example.com"),
    ],
    ch_roles=[ChRoleSpec("analyst"), ChRoleSpec("engineer")],
    ch_users=[
        ChUserSpec(
            name="bob",
            named_collection="ldap_auth",
            default_role="analyst",
        ),
    ],
    ch_grants=[
        ChGrantSpec(privileges=["SELECT"], on="analytics.*", to="analyst"),
    ],
)
```

### S3-backed table with projection

```python
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from dbwarden.databases.clickhouse import (
    CHTableMeta, ch_table, s3, projection,
)

class S3Logs(Base):
    __tablename__ = "s3_logs"

    ts: Mapped[datetime] = mapped_column()
    level: Mapped[str] = mapped_column()
    message: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=s3(
                named_collection="s3_logs",
                path="logs/*.parquet",
                format="Parquet",
            ),
            projections=[
                projection(
                    name="by_level",
                    query="SELECT level, count() GROUP BY level",
                ),
            ],
        )
```

## Workflow examples

### Generate models from existing ClickHouse

```bash
# Point dbwarden at an existing ClickHouse instance
$ dbwarden generate-models -d analytics --url clickhouse://user:pass@host:9000/analytics

# Models are written to models/analytics/*.py with ch_table() / materialized_view()
# declarations that match the live schema exactly
# (verified: 39 audit cases, zero drift)
```

### Diff and preview a migration

```bash
# Change a model (e.g., add a column), then preview
$ cat >> models/analytics.py << 'EOF'
class Event(Base):
    __tablename__ = "events"
    # ... existing columns ...
    user_agent: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by=["event_date", "id"],
        )
EOF

$ dbwarden make-migrations --plan -d analytics

# Output:
# ALTER TABLE events ADD COLUMN user_agent String   (INFO)
```

### Handle a destructive change

```bash
# Model changes ORDER BY to a non-extension
$ dbwarden make-migrations --plan -d analytics

# Output:
# CRITICAL: Changing ORDER BY from (a, b) to (c) requires --force

# Review the plan, then apply
$ dbwarden make-migrations --plan --force -d analytics
# Shows the full recreate pipeline:
#   DETACH TABLE events
#   CREATE TABLE events_new ...
#   INSERT INTO events_new SELECT * FROM events
#   RENAME TABLE ...

$ dbwarden migrate --force -d analytics
```

### Cluster-wide deployment

```bash
# Deploy to a cluster with 3 nodes
$ dbwarden migrate -d analytics --cluster-mode on_cluster

# Each DDL statement includes ON CLUSTER '{cluster}'
# ClickHouse propagates to all nodes automatically
```

### Deploy RBAC changes

```bash
# Add a new role and user, drop an old one
$ dbwarden make-migrations --plan -d analytics

# Output:
# CREATE ROLE IF NOT EXISTS engineer        (INFO)
# CREATE USER IF NOT EXISTS alice ...       (INFO)
# DROP USER bob                             (WARN: gated)

$ dbwarden migrate -d analytics --clickhouse-allow-drop-rbac
```

### Materialize a projection on existing data

```python
from dbwarden.databases.clickhouse import data_op

# After adding a projection to a table with existing data:
data_op(
    name="materialize_daily_agg",
    forward="ALTER TABLE events MATERIALIZE PROJECTION daily_agg",
)
```

## Verification workflow

```bash
# Reverse-engineer a live database
$ dbwarden generate-models -d analytics

# Preview ops without writing files
$ dbwarden make-migrations --plan -d analytics

# Write and apply
$ dbwarden make-migrations -d analytics
$ dbwarden migrate -d analytics
```

Always review auto-generated migrations before applying, especially for destructive changes flagged as CRITICAL.
