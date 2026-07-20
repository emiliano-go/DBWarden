---
seo:
  title: Type Mapping - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping
  robots: index,follow
  og:
    type: website
    title: Type Mapping - DBWarden Documentation
    description: DBWarden normalizes SQLAlchemy column types to PostgreSQL native
      types during snapshot extraction and DDL generation.
    url: https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Type Mapping - DBWarden Documentation
    description: DBWarden normalizes SQLAlchemy column types to PostgreSQL native
      types during snapshot extraction and DDL generation.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: DBWarden normalizes SQLAlchemy column types to PostgreSQL native types
    during snapshot extraction and DDL generation.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Type Mapping - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping
    description: DBWarden normalizes SQLAlchemy column types to PostgreSQL native
      types during snapshot extraction and DDL generation.
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
      name: Type Mapping
      item: https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping
seo_html: "<title>Type Mapping - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"DBWarden normalizes SQLAlchemy column types to PostgreSQL native types\
  \ during snapshot extraction and DDL generation.\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping\">\n<meta name=\"\
  robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\"\
  >\n<meta property=\"og:title\" content=\"Type Mapping - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"DBWarden normalizes SQLAlchemy column\
  \ types to PostgreSQL native types during snapshot extraction and DDL generation.\"\
  >\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Type Mapping - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"DBWarden normalizes SQLAlchemy column\
  \ types to PostgreSQL native types during snapshot extraction and DDL generation.\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Type Mapping - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping\"\
  ,\n    \"description\": \"DBWarden normalizes SQLAlchemy column types to PostgreSQL\
  \ native types during snapshot extraction and DDL generation.\",\n    \"image\"\
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
  \        \"name\": \"Type Mapping\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/type-mapping\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Type Mapping

DBWarden normalizes SQLAlchemy column types to PostgreSQL native types during snapshot extraction and DDL generation.

## Standard SQLAlchemy Types

| SQLAlchemy Type | PostgreSQL Type | Notes |
|-----------------|-----------------|-------|
| `Integer` | `INTEGER` | |
| `BigInteger` | `BIGINT` | |
| `SmallInteger` | `SMALLINT` | |
| `String(n)` | `VARCHAR(n)` | |
| `Text` | `TEXT` | |
| `Unicode(n)` | `VARCHAR(n)` | |
| `UnicodeText` | `TEXT` | |
| `Boolean` | `BOOLEAN` | |
| `DateTime` | `TIMESTAMP WITHOUT TIME ZONE` | |
| `Date` | `DATE` | |
| `Time` | `TIME WITHOUT TIME ZONE` | |
| `Float` | `FLOAT` | |
| `Double` / `DOUBLE_PRECISION` | `DOUBLE PRECISION` | |
| `Numeric(p, s)` | `NUMERIC(p, s)` | |
| `LargeBinary` | `BYTEA` | |
| `PickleType` | `BYTEA` | |
| `JSON` | `JSON` | |
| `ARRAY(Type)` | `type[]` | e.g. `ARRAY(String)` → `text[]` |
| `Enum(*members)` | `CREATE TYPE ... AS ENUM` | Auto-creates enum type |

## PostgreSQL Dialect-Specific Types

These types from `sqlalchemy.dialects.postgresql` map directly to their PostgreSQL equivalents:

| SQLAlchemy Type | PostgreSQL Type | Notes |
|-----------------|-----------------|-------|
| `JSONB` | `JSONB` | Binary JSON, supports GIN indexes |
| `TIMESTAMP` | `TIMESTAMP WITHOUT TIME ZONE` | |
| `TIMESTAMPTZ` | `TIMESTAMP WITH TIME ZONE` | |
| `TIME` | `TIME WITHOUT TIME ZONE` | |
| `TIMETZ` | `TIME WITH TIME ZONE` | |
| `INTERVAL` | `INTERVAL` | |
| `UUID` | `UUID` | |
| `BYTEA` | `BYTEA` | |
| `OID` | `OID` | |
| `REGCLASS` | `REGCLASS` | |
| `TEXT` | `TEXT` | |
| `BOOLEAN` | `BOOLEAN` | |
| `CIDR` | `CIDR` | IPv4/IPv6 network |
| `INET` | `INET` | IPv4/IPv6 host address |
| `MACADDR` | `MACADDR` | MAC address |
| `MACADDR8` | `MACADDR8` | MAC address (EUI-64) |
| `MONEY` | `MONEY` | Currency amount |
| `TSVECTOR` | `TSVECTOR` | Full-text search document |
| `TSQUERY` | `TSQUERY` | Full-text search query |
| `INT4RANGE` | `INT4RANGE` | Range of integer |
| `INT8RANGE` | `INT8RANGE` | Range of bigint |
| `NUMRANGE` | `NUMRANGE` | Range of numeric |
| `DATERANGE` | `DATERANGE` | Range of date |
| `TSTZRANGE` | `TSTZRANGE` | Range of timestamptz |
| `TSRANGE` | `TSRANGE` | Range of timestamp |
| `BIT(n)` | `BIT(n)` | Fixed-length bit string |
| `VARBIT(n)` | `VARBIT(n)` | Variable-length bit string |
| `XML` | `XML` | XML data |
| `ARRAY(type, dimensions)` | `type[]` | Multi-dimensional array |
| `ENUM(*members)` | `CREATE TYPE ... AS ENUM` | Named enum (creates persistent type) |

## Auto-increment Normalization

| Condition | Resulting Type | Sequence Behavior |
|-----------|---------------|-------------------|
| `Integer` + `autoincrement=True` | `SERIAL` | Auto-creates `tablename_colname_seq` |
| `BigInteger` + `autoincrement=True` | `BIGSERIAL` | Auto-creates sequence |
| `Integer` + `autoincrement=False` | `INTEGER` | No sequence |
| `BigInteger` + `autoincrement=False` | `BIGINT` | No sequence |
| `Integer` (unspecified autoincrement) | `SERIAL` | Backward compatible |
| `GENERATED ALWAYS AS IDENTITY` | `INTEGER` | Creates implicit sequence |
| `GENERATED BY DEFAULT AS IDENTITY` | `INTEGER` | Creates implicit sequence |

See [DDL Behavior](ddl-behavior.md#auto-increment-lifecycle) for the full lifecycle.

## Type Normalization Details

### SERIAL / BIGSERIAL

`SERIAL` and `BIGSERIAL` are syntactic sugar for `INTEGER` / `BIGINT` with an auto-created sequence and a `DEFAULT nextval(...)` expression. DBWarden normalizes them during reverse-engineering:

- On input (`generate-models`): a column typed `INTEGER` with `nextval('seq'::regclass)` default is normalized to `Integer(autoincrement=True)`
- On output (`make-migrations`): a column with `autoincrement=True` emits `SERIAL` / `BIGSERIAL` in `CREATE TABLE`

### TIMESTAMP / TIMESTAMPTZ

| SQLAlchemy Type | Normalized DDL |
|----------------|----------------|
| `DateTime` | `TIMESTAMP WITHOUT TIME ZONE` |
| `TIMESTAMP` | `TIMESTAMP WITHOUT TIME ZONE` |
| `TIMESTAMPTZ` | `TIMESTAMP WITH TIME ZONE` |

### NUMERIC Precision

`Numeric(10, 2)` emits `NUMERIC(10, 2)`. Without precision: `NUMERIC`.

### JSONB vs JSON

- `JSON` → `JSON` (stores exact copy of input text)
- `JSONB` → `JSONB` (stores decomposed binary, supports indexing)

### ARRAY Handling

`ARRAY(String)` emits `text[]`. `ARRAY(Integer)` emits `integer[]`. Multi-dimensional arrays preserve dimensions:

| SQLAlchemy | PostgreSQL |
|------------|------------|
| `ARRAY(String)` | `text[]` |
| `ARRAY(Integer, dimensions=2)` | `integer[][]` |
| `ARRAY(JSONB)` | `jsonb[]` |

### Range Types

Range types accept `Range` objects in Python. DBWarden preserves the range type variant:

| SQLAlchemy | PostgreSQL | Example Value |
|------------|------------|---------------|
| `INT4RANGE` | `INT4RANGE` | `[1, 10)` |
| `TSTZRANGE` | `TSTZRANGE` | `["2024-01-01", "2024-12-31")` |
| `DATERANGE` | `DATERANGE` | `[2024-01-01, 2024-12-31)` |

### Enum Normalization

SQLAlchemy `Enum` types with `create_constraint=True` are extracted as `CREATE TYPE` statements. Enum members are tracked positionally so new values are added with `AFTER` to preserve ordering.

### Domain-Based Columns

When a column uses a domain type (e.g., `us_postal_code`), DBWarden preserves the domain type name in the snapshot rather than expanding to the base type. See [Types](types.md#domains) for domain lifecycle.
