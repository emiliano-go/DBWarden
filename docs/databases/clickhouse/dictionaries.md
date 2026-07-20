---
seo:
  title: Dictionaries - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries
  robots: index,follow
  og:
    type: website
    title: Dictionaries - DBWarden Documentation
    description: Declaration
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Dictionaries - DBWarden Documentation
    description: Declaration
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Declaration
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Dictionaries - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries
    description: Declaration
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
      name: Dictionaries
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries
seo_html: "<title>Dictionaries - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Declaration\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Dictionaries - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Declaration\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Dictionaries - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Declaration\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Dictionaries - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries\"\
  ,\n    \"description\": \"Declaration\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Dictionaries\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/dictionaries\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Dictionaries

## Declaration

Use `ch_dict_*` factory functions inside `CHTableMeta`:

```python
from dbwarden.databases.clickhouse import ch, ch_dict, ch_dict_source

class CountryLookup(Base):
    __tablename__ = "country_lookup"

    code: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_table(
            engine=dictionary_engine(),
        )
```

But dictionaries are declared via `ch_dict_spec()` or `ch_dict_*()` builders, not as a normal table. The table above becomes:

```python
from dbwarden.databases.clickhouse import (
    ch_dictionary, ch_dict_source,
    ch_dict_layout, ch_dict_lifetime,
)

class Meta(CHTableMeta):
    ch = ch_dictionary(
        primary_key="code",
        source=ch_dict_source(
            type="clickhouse",
            query="SELECT code, name FROM source_countries",
            host="...",
            port=9000,
            user="...",
            password="...",
            db="source_db",
        ),
        layout=ch_dict_layout("flat"),
        lifetime=ch_dict_lifetime(min=300, max=600),
    )
```

## Additional model examples

### MySQL-sourced dictionary

```python
class MySQLCountry(Base):
    __tablename__ = "mysql_country"

    code: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_dictionary(
            primary_key="code",
            source=ch_dict_source(
                type="mysql",
                named_collection="mysql_dict",
                query="SELECT iso_code, full_name FROM ref.countries",
            ),
            layout=ch_dict_layout("hashed"),
            lifetime=ch_dict_lifetime(min=60, max=300),
        )
```

### HTTP-sourced dictionary with complex key

```python
class CurrencyRate(Base):
    __tablename__ = "currency_rate"

    currency: Mapped[str] = mapped_column()
    rate: Mapped[float] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_dictionary(
            primary_key="currency",
            source=ch_dict_source(
                type="http",
                url="https://api.example.com/rates",
                format="JSONEachRow",
            ),
            layout=ch_dict_layout("cache", size_in_cells=1000),
            lifetime=ch_dict_lifetime(3600),
        )
```

### Range-hashed dictionary for time-based lookup

```python
class TaxRate(Base):
    __tablename__ = "tax_rate"

    region: Mapped[str] = mapped_column()
    rate: Mapped[float] = mapped_column()

    class Meta(CHTableMeta):
        ch = ch_dictionary(
            primary_key=["region", "valid_from"],
            source=ch_dict_source(
                type="clickhouse",
                query="SELECT region, valid_from, valid_to, rate FROM ref.tax_rates",
            ),
            layout=ch_dict_layout("range_hashed"),
            lifetime=ch_dict_lifetime(86400),
        )
```

Usage in queries:

```sql
SELECT dictGet('tax_rate', 'rate', ('CA', today()))
```

## Source types

Supported sources and their factory:

| Source type | Factory |
|-------------|---------|
| ClickHouse | `ch_dict_source(type="clickhouse", ...)` |
| MySQL | `ch_dict_source(type="mysql", ...)` |
| PostgreSQL | `ch_dict_source(type="postgresql", ...)` |
| MongoDB | `ch_dict_source(type="mongodb", ...)` |
| HTTP(S) | `ch_dict_source(type="http", ...)` |
| Local file | `ch_dict_source(type="file", ...)` |
| Executable | `ch_dict_source(type="executable", ...)` |

For connection secrets, always use a named collection:

```python
source=ch_dict_source(
    type="clickhouse",
    named_collection="clickhouse_dict_source",
)
```

## Layout types

```python
from dbwarden.databases.clickhouse import ch_dict_layout

layout = ch_dict_layout("flat")                # One key, single value
layout = ch_dict_layout("hashed")              # Hash table, all in memory
layout = ch_dict_layout("sparse_hashed")       # Like hashed but sparse
layout = ch_dict_layout("cache")               # LRU cache
layout = ch_dict_layout("complex_key_hashed")  # Composite keys
layout = ch_dict_layout("ip_trie")             # IP prefix matching
layout = ch_dict_layout("direct")              # No caching
layout = ch_dict_layout("range_hashed")        # Time ranges
```

Some layouts support additional parameters:

```python
layout = ch_dict_layout("cache", size_in_cells=50000)
layout = ch_dict_layout("complex_key_cache", size_in_cells=100000)
```

## Lifetime

```python
from dbwarden.databases.clickhouse import ch_dict_lifetime

# Fixed interval
lifetime = ch_dict_lifetime(300)

# Ranged
lifetime = ch_dict_lifetime(min=300, max=600)
```

## What changes are allowed

| Change | Safety |
|--------|--------|
| Lifetime adjustment | INFO |
| Layout change | CRITICAL: requires recreate |
| Source connection change | INFO (named collection swap) |
| Query/SELECT change | WARN |
| Primary key change | CRITICAL: requires recreate |

## Rollback behavior

Dictionary changes that require a recreate follow the full pipeline. See [Safety](safety.md).
