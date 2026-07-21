---
seo:
  title: PostgreSQL - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql
  robots: index,follow
  og:
    type: website
    title: PostgreSQL - DBWarden Documentation
    description: 'DBWarden treats PostgreSQL as a first-class backend: every natively
      supported feature is reverse-engineered, diffed, and emitted as correct DDL.'
    url: https://dbwarden.emiliano-go.com/databases/postgresql
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: PostgreSQL - DBWarden Documentation
    description: 'DBWarden treats PostgreSQL as a first-class backend: every natively
      supported feature is reverse-engineered, diffed, and emitted as correct DDL.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'DBWarden treats PostgreSQL as a first-class backend: every natively
    supported feature is reverse-engineered, diffed, and emitted as correct DDL.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: PostgreSQL - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql
    description: 'DBWarden treats PostgreSQL as a first-class backend: every natively
      supported feature is reverse-engineered, diffed, and emitted as correct DDL.'
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
seo_html: "<title>PostgreSQL - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"DBWarden treats PostgreSQL as a first-class backend: every natively\
  \ supported feature is reverse-engineered, diffed, and emitted as correct DDL.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/postgresql\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"PostgreSQL - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"DBWarden treats PostgreSQL as a first-class\
  \ backend: every natively supported feature is reverse-engineered, diffed, and emitted\
  \ as correct DDL.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"PostgreSQL - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"DBWarden treats PostgreSQL as a\
  \ first-class backend: every natively supported feature is reverse-engineered, diffed,\
  \ and emitted as correct DDL.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"PostgreSQL - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\
  ,\n    \"description\": \"DBWarden treats PostgreSQL as a first-class backend: every\
  \ natively supported feature is reverse-engineered, diffed, and emitted as correct\
  \ DDL.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      }\n    ]\n  }\n]\n</script>\n"
---

# PostgreSQL

DBWarden treats PostgreSQL as a **first-class backend**: every natively supported feature is reverse-engineered, diffed, and emitted as correct DDL.

"First-class" means the round-trip is verified: reverse-engineer a live database with `generate-models`, feed the output back into `make-migrations`, and get **zero diff**.

Implementation note: PostgreSQL diffs and SQL emission flow through the `dbwarden.engine.backends.postgresql.handlers` handler package. The handler pipeline is described in the [Architecture Deep Dive](../../architecture-deep-dive.md#postgresql-handler-pipeline).

```bash
$ dbwarden generate-models -d primary --tables users,orders,items
$ dbwarden make-migrations
# -> "No changes detected"
```

## Feature Matrix

| Category | Features |
|----------|----------|
| Identity Columns | `GENERATED ALWAYS AS IDENTITY`, `GENERATED BY DEFAULT AS IDENTITY`, sequence options |
| Collation | Per-column `COLLATE` via `pg.field(collation=...)` |
| Storage | Per-column `STORAGE` (`PLAIN`, `MAIN`, `EXTERNAL`, `EXTENDED`) |
| Compression | Per-column `COMPRESSION` (`pglz`, `zstd`) via `pg.field(compression=...)` (PG 14+) |
| Generated Columns | `GENERATED ALWAYS AS (...) STORED` |
| Table Properties | Fillfactor, storage params, tablespace, unlogged, partitioning, inheritance |
| Renames | Table rename, column rename |
| Constraints | FK (`MATCH FULL/PARTIAL/SIMPLE`, `ON DELETE/UPDATE`, `DEFERRABLE`), unique (`NULLS NOT DISTINCT`, `INCLUDE`, `DEFERRABLE`), check (`NO INHERIT`, `NOT VALID`), exclude |
| Indexes | B-tree, hash, GiST, GIN, BRIN, SP-GiST; partial, expression, `INCLUDE`, `WHERE`, opclasses, `NULLS NOT DISTINCT`, column sorting, `CONCURRENTLY` |
| RLS & Policies | `ENABLE`/`DISABLE`/`FORCE`/`NO FORCE` row-level security; permissive/restrictive, role-scoped policies |
| Enums | `CREATE TYPE ... AS ENUM`, `ALTER TYPE ... ADD VALUE ... AFTER` |
| Domains | `CREATE DOMAIN` with base type, default, NOT NULL, CHECK |
| Composite Types | `CREATE TYPE ... AS (col1 type1, col2 type2, ...)` |
| Sequences | `CREATE SEQUENCE` with all options |
| Functions | `CREATE FUNCTION` with language, arguments, body |
| Triggers | `CREATE TRIGGER` with timing, events, FOR EACH ROW/STATEMENT |
| Roles | `CREATE ROLE` with login, password, privileges |
| Default Privileges | `ALTER DEFAULT PRIVILEGES` per schema/role/object-type |
| Extended Statistics | `CREATE STATISTICS` with ndistinct, dependencies, MCV, expressions (PG 14+) |
| Event Triggers | `CREATE EVENT TRIGGER` for DDL events |
| Views | Regular `CREATE OR REPLACE VIEW`, materialized views with auto-refresh |
| Schema-level Grants | `GRANT USAGE ON SCHEMA`, `GRANT ALL ON SCHEMA` |
| Table Grants | `GRANT SELECT/INSERT/UPDATE/DELETE` |
| Type Mapping | SQLAlchemy type → PostgreSQL native type normalization |
| Storage Parameters | Table-level and index-level `WITH` options, autovacuum tuning |

## Documentation Sections

- [Config Keys](config-keys.md) : All 12 `pg_*` configuration keys
- [Declaring Metadata](declaring-metadata.md) : Table-level, column-level, JSONB, FK options
- [Tables & Columns](tables-and-columns.md) : Column handler, type changes, auto-increment lifecycle
- [Registry Architecture](../../architecture-deep-dive.md#postgresql-handler-pipeline) : Handler map, phases, online and offline diff flow
- [Constraints](constraints.md) : FK (MATCH FULL, CASCADE), unique, check, exclude
- [Indexes](indexes.md) : B-tree, partial, expression indexes, operator classes, NULLS NOT DISTINCT
- [Types](types.md) : Enums, domains, composite types
- [Functions & Triggers](functions-and-triggers.md) : Function and trigger lifecycle
- [RLS & Policies](rls-and-policies.md) : Row-level security, policy lifecycle, FORCE
- [Grants & Roles](grants-and-roles.md) : Table grants, schema grants, roles, default privileges
- [Partitioning](partitioning.md) : RANGE/LIST/HASH partition strategies, attach/detach
- [Views](views.md) : Regular and materialized views, auto-refresh
- [Sequences](sequences.md) : Sequence creation and ownership
- [Extended Statistics](extended-statistics.md) : ndistinct, dependencies, MCV, expressions
- [Event Triggers](event-triggers.md) : DDL event trigger lifecycle
- [Schemas](schemas.md) : Config-level and model-level schemas, search path
- [DDL Behavior](ddl-behavior.md) : Transactional DDL, CONCURRENTLY, type change strategies
- [Type Mapping](type-mapping.md) : SQLAlchemy type → PostgreSQL type normalization
- [Storage Parameters](storage-params.md) : Table and index storage parameters, autovacuum tuning
- [Migration Safety](migration-safety.md) : Safety classification table
