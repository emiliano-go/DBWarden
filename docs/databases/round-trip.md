---
description: A round-trip backend is one where DBWarden can both read schema (via
  generate-models) and write schema (via make-migrations/migrate). Covers PostgreSQL,
  MySQL, ClickHouse, SQLite, and MariaDB.
seo:
  title: Round Trip Support - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/round-trip
  robots: index,follow
  og:
    type: website
    title: Round Trip Support - DBWarden Documentation
    description: A round-trip backend is one where DBWarden can both read schema (via
      generate-models) and write schema (via make-migrations/migrate). Covers PostgreSQL,
      MySQL, ClickHouse, SQLite, and MariaDB.
    url: https://dbwarden.emiliano-go.com/databases/round-trip
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Round Trip Support - DBWarden Documentation
    description: A round-trip backend is one where DBWarden can both read schema (via
      generate-models) and write schema (via make-migrations/migrate). Covers PostgreSQL,
      MySQL, ClickHouse, SQLite, and MariaDB.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: A round-trip backend is one where DBWarden can both read schema (via
    generate-models) and write schema (via make-migrations/migrate). Covers PostgreSQL,
    MySQL, ClickHouse, SQLite, and MariaDB.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Round Trip Support - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/round-trip
    description: A round-trip backend is one where DBWarden can both read schema (via
      generate-models) and write schema (via make-migrations/migrate). Covers PostgreSQL,
      MySQL, ClickHouse, SQLite, and MariaDB.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Databases
      item: https://dbwarden.emiliano-go.com/databases
    - '@type': ListItem
      position: 2
      name: Round Trip Support
      item: https://dbwarden.emiliano-go.com/databases/round-trip
seo_html: "<title>Round Trip Support - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"A round-trip backend is one where DBWarden can both read\
  \ schema (via generate-models) and write schema (via make-migrations/migrate). Covers\
  \ PostgreSQL, MySQL, ClickHouse, SQLite, and MariaDB.\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/databases/round-trip\">\n<meta name=\"\
  robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\"\
  >\n<meta property=\"og:title\" content=\"Round Trip Support - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"A round-trip backend is one where\
  \ DBWarden can both read schema (via generate-models) and write schema (via make-migrations/migrate).\
  \ Covers PostgreSQL, MySQL, ClickHouse, SQLite, and MariaDB.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/databases/round-trip\">\n<meta\
  \ property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"Round Trip Support - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"A round-trip backend is one where DBWarden can both read schema (via\
  \ generate-models) and write schema (via make-migrations/migrate). Covers PostgreSQL,\
  \ MySQL, ClickHouse, SQLite, and MariaDB.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/icon.png\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Round Trip Support - DBWarden Documentation\",\n    \"url\":\
  \ \"https://dbwarden.emiliano-go.com/databases/round-trip\",\n    \"description\"\
  : \"A round-trip backend is one where DBWarden can both read schema (via generate-models)\
  \ and write schema (via make-migrations/migrate). Covers PostgreSQL, MySQL, ClickHouse,\
  \ SQLite, and MariaDB.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Databases\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases\"\n      },\n\
  \      {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"\
  name\": \"Round Trip Support\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/round-trip\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Round Trip Support

A **round-trip** backend is one where DBWarden can both read schema (via `generate-models`) and write schema (via `make-migrations` / `migrate`).

## Supported Backends

| Backend | `database_type` | Round-Trip |
|---------|------------------|------------|
| PostgreSQL | `postgresql` | Yes |
| MySQL | `mysql` | Yes |
| ClickHouse | `clickhouse` | Yes |
| SQLite | `sqlite` | Dev only |
| MariaDB | `mariadb` | No |

## How Round-Trip Verification Works

"First-class" means the round-trip is verified: reverse-engineer a live database with `generate-models`, feed the output back into `make-migrations`, and get **zero diff**.

## Per-Backend Details

### PostgreSQL

PostgreSQL is a **first-class backend** with full round-trip support. All metadata (identity columns, collation, storage, compression, generated columns, fillfactor, tablespace, inheritance, exclude constraints, deferrable foreign keys, and advanced index options) is captured by the snapshot, diffed correctly, and emitted as valid DDL.

See [PostgreSQL Deep Dive](postgresql.md) for the complete list of supported features.

### MySQL

MySQL is a **first-class backend** with full round-trip support. All metadata (engine, charset, collation, row format, auto_increment, unsigned columns, `ON UPDATE`, and column comments) is captured by the snapshot, diffed correctly, and emitted as valid DDL.

See [MySQL Deep Dive](mysql.md) for the complete list of supported features.

### ClickHouse

ClickHouse has full round-trip support: `generate-models` reads schema from a live ClickHouse server, and `make-migrations` / `migrate` auto-generates DDL for table operations.

See [ClickHouse Deep Dive](clickhouse.md) for the complete list of supported features.

### SQLite

SQLite is supported for **development workflows only** (`--dev` flag). It uses the same snapshot format as PostgreSQL but with SQLite-compatible DDL. SQLite is ideal for local iteration before running migrations against production.

### MariaDB

MariaDB is supported as a separate `database_type` (`mariadb`), but it does **not** have round-trip support. You can use MariaDB as a target database for migrations, but `generate-models` and full schema introspection are not available. Use `make-migrations` to write migrations manually.
