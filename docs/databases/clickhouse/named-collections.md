---
seo:
  title: Named collections - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections
  robots: index,follow
  og:
    type: website
    title: Named collections - DBWarden Documentation
    description: Named collections are the mechanism for declaring credentials without
      exposing secret values. They are declared in the config layer, referenced by
      name from...
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Named collections - DBWarden Documentation
    description: Named collections are the mechanism for declaring credentials without
      exposing secret values. They are declared in the config layer, referenced by
      name from...
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Named collections are the mechanism for declaring credentials without
    exposing secret values. They are declared in the config layer, referenced by name
    from...
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Named collections - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections
    description: Named collections are the mechanism for declaring credentials without
      exposing secret values. They are declared in the config layer, referenced by
      name from...
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
      name: Named Collections
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections
seo_html: "<title>Named collections - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Named collections are the mechanism for declaring credentials\
  \ without exposing secret values. They are declared in the config layer, referenced\
  \ by name from...\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Named collections - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Named collections are the mechanism\
  \ for declaring credentials without exposing secret values. They are declared in\
  \ the config layer, referenced by name from...\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections\">\n<meta\
  \ property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Named collections - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Named collections are the mechanism\
  \ for declaring credentials without exposing secret values. They are declared in\
  \ the config layer, referenced by name from...\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Named collections - DBWarden Documentation\",\n    \"url\": \"\
  https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections\",\n   \
  \ \"description\": \"Named collections are the mechanism for declaring credentials\
  \ without exposing secret values. They are declared in the config layer, referenced\
  \ by name from...\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Named Collections\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/named-collections\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Named collections

Named collections are the mechanism for declaring credentials without exposing secret values. They are declared in the config layer, referenced by name from engine and RBAC specs.

## Declaration

```python
from dbwarden import database_config
from dbwarden.databases.clickhouse import named_collection

database_config(
    name="analytics",
    url="clickhouse://...",
    ch_named_collections=[
        named_collection(
            name="kafka_prod",
            keys={
                "sasl_username": "kafka_user",
# sasl_password is NOT declared here: it comes from the
        # secret store. See "declare-only" below.
            },
        ),
        named_collection(
            name="s3_prod",
            keys={
                "region": "us-east-1",
                "access_key_id": "AKIA...",
            },
        ),
    ],
)
```

## Key-set diffed, values declare-only

Named collections are diffed on their **key set**: what keys are declared and what values are referenced. The **values themselves are never diffed**. This is the "declare-only" principle:

- `named_collection("kafka_prod", keys={"sasl_username": "kafka_user"})` declares that a collection named `kafka_prod` should have the key `sasl_username`.
- The value `"kafka_user"` is metadata for dbwarden's diff output but is **never compared** to the server state. Secret values (`password`, `sasl_password`, `secret_access_key`) are not declared at all: they come from ClickHouse's secret store.

This means dbwarden will detect that a key exists in a model but is missing from the server, and emit `CREATE NAMED COLLECTION ...`. But it will never emit `ALTER NAMED COLLECTION` with a changed password value: it can't know the real value.

## Additional model examples

### Named collection for Postgres engine

```python
named_collection(
    name="pg_source",
    keys={
        "connection_string": "postgresql://user:pass@pg-host:5432/db",
        "port": "5432",
    },
)
```

### Named collection with cluster and secret reference

```python
named_collection(
    name="kafka_secure",
    keys={
        "bootstrap_servers": "kafka-broker:9092",
        "sasl_mechanism": "SCRAM-SHA-256",
        "sasl_username": "ch_user",
        # sasl_password = SECRET(...) stored in ClickHouse secret store
        "security_protocol": "sasl_ssl",
    },
)
```

Engine usage:

```python
engine = kafka_engine(
    named_collection="kafka_secure",
    topic="events",
    format="Avro",
    group_name="dbwarden",
)
```

### Dict config (raw path)

```python
database_config(
    name="analytics",
    url="clickhouse://localhost:9000",
    ch_named_collections=[
        {
            "name": "s3_data",
            "keys": {
                "region": "us-east-1",
                "url": "https://s3.amazonaws.com/mybucket",
            },
        },
    ],
)
```

## Reference from engines

```python
engine = kafka_engine(
    named_collection="kafka_prod",
    topic="events",
)
```

The engine gets credentials from the named collection. The named collection is referenced by name only in the engine settings (`kafka_named_collection`, `s3_named_collection`, etc.).

## Reference from RBAC

```python
ch_user_spec(
    named_collection="ldap_prod",
    ...
)
```

## What changes are allowed

| Change | Safety |
|--------|--------|
| Add named collection | INFO |
| Drop named collection | WARN (may break references) |
| Add key to declaration | INFO |
| Remove key from declaration | WARN |
| Change a non-secret value | INFO |
| Secret values | Not tracked |

## Rollback behavior

`DROP NAMED COLLECTION` rolls back as `CREATE NAMED COLLECTION`. Key changes roll back as inverse key changes.
