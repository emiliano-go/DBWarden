---
seo:
  title: Types - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/types
  robots: index,follow
  og:
    type: website
    title: Types - DBWarden Documentation
    description: 'DBWarden supports three object-level type families: enums, domains,
      and composite types. Enums are model-derived auto-discovered from table columns.
      Domains...'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/types
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Types - DBWarden Documentation
    description: 'DBWarden supports three object-level type families: enums, domains,
      and composite types. Enums are model-derived auto-discovered from table columns.
      Domains...'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'DBWarden supports three object-level type families: enums, domains,
    and composite types. Enums are model-derived auto-discovered from table columns.
    Domains...'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Types - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/types
    description: 'DBWarden supports three object-level type families: enums, domains,
      and composite types. Enums are model-derived auto-discovered from table columns.
      Domains...'
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
      name: Types
      item: https://dbwarden.emiliano-go.com/databases/postgresql/types
seo_html: "<title>Types - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"DBWarden supports three object-level type families: enums, domains,\
  \ and composite types. Enums are model-derived auto-discovered from table columns.\
  \ Domains...\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/postgresql/types\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Types - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"DBWarden supports three object-level\
  \ type families: enums, domains, and composite types. Enums are model-derived auto-discovered\
  \ from table columns. Domains...\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/types\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Types - DBWarden Documentation\">\n<meta\
  \ name=\"twitter:description\" content=\"DBWarden supports three object-level type\
  \ families: enums, domains, and composite types. Enums are model-derived auto-discovered\
  \ from table columns. Domains...\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Types - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/types\"\
  ,\n    \"description\": \"DBWarden supports three object-level type families: enums,\
  \ domains, and composite types. Enums are model-derived auto-discovered from table\
  \ columns. Domains...\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Types\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/types\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Types

DBWarden supports three object-level type families: enums, domains, and composite types. Enums are model-derived (auto-discovered from table columns). Domains and composite types are config-driven.

## Enums

**Handler**: `EnumHandler` (DIFF phase)

Enums are auto-discovered from column types during snapshot extraction. Enum values are tracked with position data, so `ALTER TYPE ... ADD VALUE ... AFTER ...` preserves ordering.

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE TYPE name AS ENUM ('val1', 'val2', ...)` |
| Add value | `ALTER TYPE name ADD VALUE 'newval' AFTER 'existing'` |
| Rename value | `ALTER TYPE name RENAME VALUE 'old' TO 'new'` (PG 10+) |
| Drop | `DROP TYPE IF EXISTS name` |

### Adding Enum Values

New enum values are inserted after the preceding existing value to preserve sort order:

```python
# Current enum: mood AS ENUM ('sad', 'ok', 'happy')
# Adding 'ecstatic' after 'happy':
# ALTER TYPE mood ADD VALUE 'ecstatic' AFTER 'happy'
```

### Enum Value Renaming (PG 10+)

```sql
ALTER TYPE mood RENAME VALUE 'sad' TO 'unhappy';
```

### Enum Value Deletion

PostgreSQL does **not** support `ALTER TYPE ... DROP VALUE`. Removing an enum value requires:
1. `ALTER TYPE name RENAME TO name_old`
2. `CREATE TYPE name AS ENUM (...)` without the removed value
3. `ALTER TABLE ... ALTER COLUMN c TYPE name USING c::text::name`
4. `DROP TYPE name_old`

This is **not** automated by DBWarden. Value removal is classified as a manual operation.

### Enum Type Normalization

SQLAlchemy's `Enum` type with `create_type=True` creates a persistent PostgreSQL enum type. Without it, the enum is rendered as a `VARCHAR` with a `CHECK` constraint.

## Domains

**Handler**: `DomainHandler` (PREAMBLE phase)

Domains are config-driven objects declared via `pg_domains`:

```python
pg_domains=[
    {
        "name": "us_postal_code",
        "type": "text",
        "not_null": True,
        "check": "VALUE ~ '^\d{5}(-\d{4})?$'",
    },
    {
        "name": "positive_int",
        "type": "int",
        "check": "VALUE > 0",
        "default": "1",
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE DOMAIN name AS base_type [DEFAULT default] [NOT NULL] [CHECK (expr)]` |
| Drop | `DROP DOMAIN IF EXISTS name CASCADE;` |
| Set default | `ALTER DOMAIN name SET DEFAULT expr;` |
| Drop default | `ALTER DOMAIN name DROP DEFAULT;` |
| Set not null | `ALTER DOMAIN name SET NOT NULL;` |
| Drop not null | `ALTER DOMAIN name DROP NOT NULL;` |
| Add constraint | `ALTER DOMAIN name ADD CONSTRAINT c CHECK (expr);` |
| Drop constraint | `ALTER DOMAIN name DROP CONSTRAINT c;` |
| Rename | `ALTER DOMAIN name RENAME TO new_name;` |
| Rename constraint | `ALTER DOMAIN name RENAME CONSTRAINT old TO new;` |
| Set schema | `ALTER DOMAIN name SET SCHEMA new_schema;` |

### Domain Constraint Validation

Domain constraints are checked on every use of the domain, not just at column creation. This means changing a domain's CHECK constraint can invalidate existing data in every table that uses the domain.

Changes to domain definition are detected as drop-then-create. When a domain check is relaxed or tightened, existing rows must satisfy the new constraint or be updated first.

## Composite Types

**Handler**: `CompositeTypeHandler` (PREAMBLE phase)

Composite types are config-driven objects declared via `pg_composite_types`:

```python
pg_composite_types=[
    {
        "name": "address",
        "columns": [
            {"name": "street", "type": "text"},
            {"name": "city", "type": "text"},
            {"name": "zip", "type": "text"},
        ],
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE TYPE name AS (col1 type1, col2 type2, ...)` |
| Drop | `DROP TYPE IF EXISTS name CASCADE;` |

### Composite Type Modification

PostgreSQL does **not** support `ALTER TYPE` for composite types. To modify a composite type:
1. `DROP TYPE name CASCADE;` (automatically drops dependent columns/tables)
2. `CREATE TYPE name AS (...);` with the new definition
3. Recreate any dropped columns referencing this type

This is **not** automated by DBWarden. Composite type changes are detected as drop-then-create with `CASCADE`.

### Schema

Composite types can be scoped to a schema:

```python
{"name": "address", "schema": "app", "columns": [...]}
```

## Range Types

PostgreSQL supports built-in range types that DBWarden normalizes during schema extraction:

| PostgreSQL Type | SQLAlchemy Type | Example Value |
|----------------|-----------------|---------------|
| `INT4RANGE` | `INT4RANGE` | `[1, 10)` |
| `INT8RANGE` | `INT8RANGE` | `[100, 200)` |
| `NUMRANGE` | `NUMRANGE` | `[0.0, 1.0)` |
| `DATERANGE` | `DATERANGE` | `[2024-01-01, 2024-12-31)` |
| `TSTZRANGE` | `TSTZRANGE` | `["2024-01-01 00:00:00+00", "2024-12-31 23:59:59+00")` |
| `TSRANGE` | `TSRANGE` | `[2024-01-01, 2024-12-31)` |

Range type bounds are canonicalized as `[lower, upper)` (inclusive lower, exclusive upper) by PostgreSQL.

## Type Mapping Summary

See [Type Mapping](type-mapping.md) for the complete SQLAlchemy-to-PostgreSQL type normalization reference.
