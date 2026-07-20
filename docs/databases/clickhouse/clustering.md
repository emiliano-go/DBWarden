---
seo:
  title: Clustering - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/clustering
  robots: index,follow
  og:
    type: website
    title: Clustering - DBWarden Documentation
    description: ON CLUSTER
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/clustering
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Clustering - DBWarden Documentation
    description: ON CLUSTER
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: ON CLUSTER
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Clustering - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/clustering
    description: ON CLUSTER
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
      name: Clustering
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/clustering
seo_html: "<title>Clustering - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"ON CLUSTER\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/clustering\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Clustering - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"ON CLUSTER\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/clustering\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Clustering - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"ON CLUSTER\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Clustering - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/clustering\"\
  ,\n    \"description\": \"ON CLUSTER\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Clustering\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/clustering\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

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
