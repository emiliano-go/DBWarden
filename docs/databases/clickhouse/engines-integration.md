---
seo:
  title: Integration engines - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration
  robots: index,follow
  og:
    type: website
    title: Integration engines - DBWarden Documentation
    description: 'dbwarden supports 13 integration engines. Credentials use the named-collectionsnamed-collections.md
      declare-only pattern: no secret values are diffed.'
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Integration engines - DBWarden Documentation
    description: 'dbwarden supports 13 integration engines. Credentials use the named-collectionsnamed-collections.md
      declare-only pattern: no secret values are diffed.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'dbwarden supports 13 integration engines. Credentials use the named-collectionsnamed-collections.md
    declare-only pattern: no secret values are diffed.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Integration engines - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration
    description: 'dbwarden supports 13 integration engines. Credentials use the named-collectionsnamed-collections.md
      declare-only pattern: no secret values are diffed.'
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
      name: Engines Integration
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration
seo_html: "<title>Integration engines - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"dbwarden supports 13 integration engines. Credentials use\
  \ the named-collectionsnamed-collections.md declare-only pattern: no secret values\
  \ are diffed.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Integration engines - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"dbwarden supports\
  \ 13 integration engines. Credentials use the named-collectionsnamed-collections.md\
  \ declare-only pattern: no secret values are diffed.\">\n<meta property=\"og:url\"\
  \ content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Integration engines - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"dbwarden supports 13 integration\
  \ engines. Credentials use the named-collectionsnamed-collections.md declare-only\
  \ pattern: no secret values are diffed.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Integration engines - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration\"\
  ,\n    \"description\": \"dbwarden supports 13 integration engines. Credentials\
  \ use the named-collectionsnamed-collections.md declare-only pattern: no secret\
  \ values are diffed.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Engines Integration\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-integration\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Integration engines

dbwarden supports 13 integration engines. Credentials use the [named-collections](named-collections.md) declare-only pattern: no secret values are diffed.

## Kafka

```python
from dbwarden.databases.clickhouse import kafka_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=kafka_engine(
            named_collection="kafka_prod",
            topic="events",
            format="JSONEachRow",
            group_name="dbwarden_consumer",
        ),
    )
```

Generated DDL:

```sql
CREATE TABLE kafka_events (
    payload String
) ENGINE = Kafka
SETTINGS kafka_named_collection = 'kafka_prod',
         kafka_topic_list = 'events',
         kafka_format = 'JSONEachRow',
         kafka_group_name = 'dbwarden_consumer';
```

Parameters that can be set directly (overriding the named collection):

| Factory parameter | DDL setting |
|------------------|-------------|
| `named_collection` | `kafka_named_collection` |
| `topic` | `kafka_topic_list` |
| `format` | `kafka_format` |
| `group_name` | `kafka_group_name` |
| `num_consumers` | `kafka_num_consumers` |
| `thread_per_consumer` | `kafka_thread_per_consumer` |
| `handle_error_mode` | `kafka_handle_error_mode` |
| `commit_every_batch` | `kafka_commit_every_batch` |

`KafkaSettings` is a fully-typed TypedDict for arbitrary Kafka engine settings:

```python
from dbwarden.databases.clickhouse import KafkaSettings

settings: KafkaSettings = {
    "kafka_max_block_size": 524288,
}
```

## S3

```python
from dbwarden.databases.clickhouse import s3_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=s3_engine(
            named_collection="s3_prod",
            pattern="events/*.parquet",
            format="Parquet",
        ),
    )
```

Parameters:

| Parameter | DDL setting |
|-----------|-------------|
| `named_collection` | `s3_named_collection` |
| `pattern` | `url` (first positional) |
| `format` | `format` |
| `compression` | `compression` |

`S3Settings` for arbitrary settings. Key naming variants (`s3_*`, `s3queue_*`) are all typed.

## S3Queue

```python
from dbwarden.databases.clickhouse import s3queue_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=s3queue_engine(
            named_collection="s3_prod",
            pattern="incoming/*.json",
            format="JSONEachRow",
        ),
    )
```

`S3QueueSettings` covers all s3queue-specific settings.

## RabbitMQ

```python
from dbwarden.databases.clickhouse import rabbitmq_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=rabbitmq_engine(
            named_collection="rabbit_prod",
            format="JSONEachRow",
        ),
    )
```

`RabbitMQSettings`, typed TypedDict.

## NATS

```python
from dbwarden.databases.clickhouse import nats_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=nats_engine(
            named_collection="nats_prod",
            format="JSONEachRow",
        ),
    )
```

`NatsSettings`, typed TypedDict.

## MySQL, PostgreSQL, MongoDB, Redis

```python
from dbwarden.databases.clickhouse import mysql_engine, postgresql_engine, mongodb_engine, redis_engine

# MySQL engine
engine = mysql_engine(
    named_collection="mysql_prod",
    query="SELECT * FROM source_db.table",
)

# PostgreSQL engine
engine = postgresql_engine(
    named_collection="pg_prod",
    query="SELECT * FROM source_schema.source_table",
)

# MongoDB engine
engine = mongodb_engine(
    named_collection="mongo_prod",
    collection="source_collection",
)

# Redis engine
engine = redis_engine(
    named_collection="redis_prod",
    key="prefix:*",
)
```

Each has an associated `*Settings` TypedDict for engine-specific settings.

## Additional model examples

### Named collection for multi-engine reuse

```python
# Single named collection reused by Kafka and S3 engines
named_collection(
    name="aws_prod",
    keys={
        "region": "us-east-1",
        "access_key_id": "AKIA...",
        # secret_access_key from secret store
    },
)

engine = kafka_engine(
    named_collection="aws_prod",
    topic="events",
    format="JSONEachRow",
    group_name="ch_consumer",
)

engine2 = s3_engine(
    named_collection="aws_prod",
    pattern="data/*.parquet",
    format="Parquet",
)
```

### S3Queue with complex settings

```python
engine = s3queue_engine(
    named_collection="aws_prod",
    pattern="incoming/*.json",
    format="JSONEachRow",
)

# With custom settings
settings: S3QueueSettings = {
    "s3queue_processing_threads": 8,
    "s3queue_polling_min_timeout_ms": 1000,
    "s3queue_polling_max_timeout_ms": 30000,
    "s3queue_tracked_files_limit": 100000,
}
```

### PostgreSQL engine with query

```python
engine = postgresql_engine(
    named_collection="pg_prod",
    query="SELECT id, name, created_at FROM public.users WHERE active = 1",
)
```

### URL engine with multiple formats

```python
# CSV
engine = url_engine(
    named_collection="http_data",
    format="CSV",
)

# With specific compression
engine = url_engine(
    named_collection="http_data",
    format="JSONEachRow",
    compression="gzip",
)
```

## URL

```python
from dbwarden.databases.clickhouse import url_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=url_engine(
            named_collection="http_prod",
            format="CSV",
        ),
    )
```

`URLSettings`.

## File

```python
from dbwarden.databases.clickhouse import file_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=file_engine(
            path="/var/lib/clickhouse/user_files/export.csv",
            format="CSV",
        ),
    )
```

## HDFS

```python
from dbwarden.databases.clickhouse import hdfs_engine

class Meta(CHTableMeta):
    ch = ch_table(
        engine=hdfs_engine(
            named_collection="hdfs_prod",
            format="Parquet",
        ),
    )
```

`HDFSSettings`.

## Per-engine settings TypedDicts

Every integration engine has its own `*Settings` TypedDict for arbitrary settings. These are all defined in `dbwarden.databases.clickhouse`:

| Engine | TypedDict |
|--------|-----------|
| Kafka | `KafkaSettings` |
| S3 | `S3Settings` |
| S3Queue | `S3QueueSettings` |
| RabbitMQ | `RabbitMQSettings` |
| NATS | `NatsSettings` |
| MySQL | `MySQLSettings` |
| PostgreSQL | `PostgreSQLSettings` |
| MongoDB | `MongoDBSettings` |
| Redis | `RedisSettings` |
| URL | `URLSettings` |
| HDFS | `HDFSSettings` |

## What changes are allowed

| Change | Safety |
|--------|--------|
| Named collection swap | CRITICAL (metadata only, not data) |
| Any setting | INFO: `ALTER TABLE MODIFY SETTING` |
| Format change | WARN: requires data re-ingestion |
| Pattern / query / key change | WARN |

## Rollback behavior

Settings changes revert via `RESET SETTING`. Named collection swaps require reversing the collection reference.
