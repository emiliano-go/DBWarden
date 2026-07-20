---
seo:
  title: Special engines - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special
  robots: index,follow
  og:
    type: website
    title: Special engines - DBWarden Documentation
    description: 'These engines do not participate in ORDER BY: they are storage-format-specific
      serverside readers.'
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Special engines - DBWarden Documentation
    description: 'These engines do not participate in ORDER BY: they are storage-format-specific
      serverside readers.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'These engines do not participate in ORDER BY: they are storage-format-specific
    serverside readers.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Special engines - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special
    description: 'These engines do not participate in ORDER BY: they are storage-format-specific
      serverside readers.'
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
      name: Engines Special
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special
seo_html: "<title>Special engines - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"These engines do not participate in ORDER BY: they are storage-format-specific\
  \ serverside readers.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Special engines - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"These engines do not participate\
  \ in ORDER BY: they are storage-format-specific serverside readers.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Special engines - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"These engines do not participate\
  \ in ORDER BY: they are storage-format-specific serverside readers.\">\n<meta name=\"\
  twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Special engines - DBWarden Documentation\",\n    \"url\": \"\
  https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special\",\n    \"\
  description\": \"These engines do not participate in ORDER BY: they are storage-format-specific\
  \ serverside readers.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Engines Special\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/engines-special\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Special engines

These engines do not participate in `ORDER BY`: they are storage-format-specific serverside readers.

## Factories

```python
from dbwarden.databases.clickhouse import (
    null_engine, memory_engine, merge_engine,
    set_engine, join_engine, dictionary_engine,
    log_engine, tinylog_engine, stripelog_engine,
)
```

## Additional model examples

### Null engine as MV sink

```python
class NullSink(Base):
    __tablename__ = "null_sink"

    payload: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=null_engine(),
        )

class ViewFromSink(Base):
    __tablename__ = "view_from_sink"

    value: Mapped[int] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_tree(),
            order_by="value",
            ch_to_table="sink_dest",
            ch_select="SELECT count(*) AS value FROM null_sink",
        )
```

### Merge engine for partitioned read

```python
class AllEvents(Base):
    __tablename__ = "all_events"

    date: Mapped[date] = mapped_column()
    payload: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=merge_engine(
                source_database="analytics",
                table_regex="events_202[0-9]_*",
            ),
        )
```

### Dictionary engine with explicit dictionary

```python
class CountryDict(Base):
    __tablename__ = "country_dict"

    code: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(engine=dictionary_engine())
```

The dictionary is declared separately via `ch_dictionary()`. See [Dictionaries](dictionaries.md).

## Null

```python
engine = null_engine()
```

DDL: `ENGINE = Null`. Accepts any data and discards it. Used as the target of a materialized view that does its own aggregation.

## Memory

```python
engine = memory_engine()
```

DDL: `ENGINE = Memory`. In-memory storage, lost on restart. Schema management only.

## Merge

```python
engine = merge_engine(
    source_database="analytics",
    table_regex="events_.*",
)
```

DDL: `ENGINE = Merge('analytics', 'events_.*')`. A virtual table that reads from multiple tables whose names match the regex.

## Set

```python
engine = set_engine()
```

DDL: `ENGINE = Set`. Always in-memory. Use for IN-query acceleration.

## Join

```python
engine = join_engine(
    join_type="LEFT",
    strictness="ALL",
)
```

DDL: `ENGINE = Join(LEFT, ALL)`. Specialized for JOIN queries.

## Dictionary

```python
engine = dictionary_engine()
```

DDL: `ENGINE = Dictionary(<dict_name>)`. References a [Dictionary](dictionaries.md) object by name.

## Log, TinyLog, StripeLog

```python
engine = log_engine()
engine = tinylog_engine()
engine = stripelog_engine()
```

DDLs: `ENGINE = Log`, `TinyLog`, `StripeLog`. Append-only file-based storage. No ORDER BY, no parts merging. StripeLog is multithreaded on read; TinyLog is the simplest.

## What changes are allowed

These engines have no ORDER BY, so immutability rules don't apply in the same way. An engine change (e.g., Memory → MergeTree) requires `--force` and a recreate.

| Change | Safety |
|--------|--------|
| Engine variant | CRITICAL with `--force` |
| Merge source/target | INFO |
| Join type/strictness | WARN |

## Rollback behavior

Engine changes trigger recreate. See [Safety](safety.md) for the pipeline.
