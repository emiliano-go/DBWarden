---
seo:
  title: Schemas - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/schemas
  robots: index,follow
  og:
    type: website
    title: Schemas - DBWarden Documentation
    description: 'Handler: SchemaHandler PREAMBLE phase'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/schemas
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Schemas - DBWarden Documentation
    description: 'Handler: SchemaHandler PREAMBLE phase'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Handler: SchemaHandler PREAMBLE phase'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Schemas - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/schemas
    description: 'Handler: SchemaHandler PREAMBLE phase'
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
      name: Schemas
      item: https://dbwarden.emiliano-go.com/databases/postgresql/schemas
seo_html: "<title>Schemas - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Handler: SchemaHandler PREAMBLE phase\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/databases/postgresql/schemas\">\n<meta name=\"\
  robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\"\
  >\n<meta property=\"og:title\" content=\"Schemas - DBWarden Documentation\">\n<meta\
  \ property=\"og:description\" content=\"Handler: SchemaHandler PREAMBLE phase\"\
  >\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/schemas\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Schemas - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Handler: SchemaHandler PREAMBLE phase\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Schemas - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/schemas\"\
  ,\n    \"description\": \"Handler: SchemaHandler PREAMBLE phase\",\n    \"image\"\
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
  \        \"name\": \"Schemas\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/schemas\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Schemas

**Handler**: `SchemaHandler` (PREAMBLE phase)

## Config-Level Schema

Set `pg_schema` in `database_config(...)` to set the connection's `search_path`:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/main",
    pg_schema="app",
)
```

All unqualified table references use this schema. The `_dbwarden_seeds` tracking table is created in the schema specified by `search_path`.

## Model-Level Schema

Set `pg_schema` on `PGTableMeta` or `PGViewMeta`:

```python
class Meta(PGTableMeta):
    pg_schema = "app"
```

When a model has `pg_schema`, all DDL references the fully qualified name (`app.users`). This takes precedence over the config-level `search_path`.

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE SCHEMA IF NOT EXISTS name;` |
| Drop | `DROP SCHEMA IF EXISTS name CASCADE;` |

## Schema Ownership

When a schema is created, it is owned by the role that created it. Set a different owner:

```sql
ALTER SCHEMA app OWNER TO app_admin;
```

## Schema Privileges

Schemas require privileges for access:

| Privilege | Effect |
|-----------|--------|
| `USAGE` | Allows access to objects in the schema |
| `CREATE` | Allows creating new objects in the schema |

```sql
GRANT USAGE ON SCHEMA app TO app_user;
GRANT CREATE ON SCHEMA app TO app_admin;
```

Without `USAGE` on a schema, a user cannot see or access any objects within it, even if they have table-level privileges.

## Search Path Resolution

PostgreSQL resolves unqualified names by searching schemas in `search_path` order:

```
current_schema (first match wins) -> pg_catalog -> public
```

Use the `current_schema` function to check the effective search path:

```sql
SELECT current_schema; -- Returns the first schema in the path
SHOW search_path;      -- Returns the full search path string
```

The config-level `pg_schema` becomes the first entry in `search_path`, which means it takes precedence for all unqualified references.

## pg_catalog vs public

- `pg_catalog` is always searched unless explicitly excluded
- `public` schema is accessible by default to all roles
- Custom schemas require explicit `USAGE` grants

## Temporary Schema

PostgreSQL creates a `pg_temp_*` schema for temporary tables. Temporary tables take precedence over permanent tables when their schema is first in `search_path`. You can reference `pg_temp.schema_name` explicitly.

## Extensions

Extensions are created during the PREAMBLE phase via `pg_extensions`:

```python
pg_extensions=["uuid-ossp", "pgcrypto"]
```

Generated DDL: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

## Code Seeds and Schema

Code seeds automatically qualify the table name with the model's `pg_schema`. If `User` has `pg_schema = "app"`, the seed INSERT becomes `INSERT INTO app.users (...) VALUES (...)`.
