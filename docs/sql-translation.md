---
seo:
  title: SQL Translation - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/sql-translation
  robots: index,follow
  og:
    type: website
    title: SQL Translation - DBWarden Documentation
    description: DBWarden includes a SQL translation layer to support development
      workflows where your primary database differs from your development database.
    url: https://dbwarden.emiliano-go.com/sql-translation
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: SQL Translation - DBWarden Documentation
    description: DBWarden includes a SQL translation layer to support development
      workflows where your primary database differs from your development database.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: DBWarden includes a SQL translation layer to support development workflows
    where your primary database differs from your development database.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: SQL Translation - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/sql-translation
    description: DBWarden includes a SQL translation layer to support development
      workflows where your primary database differs from your development database.
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
      name: SQL Translation
      item: https://dbwarden.emiliano-go.com/sql-translation
seo_html: "<title>SQL Translation - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"DBWarden includes a SQL translation layer to support development\
  \ workflows where your primary database differs from your development database.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/sql-translation\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"SQL Translation - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"DBWarden includes a SQL translation\
  \ layer to support development workflows where your primary database differs from\
  \ your development database.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/sql-translation\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"SQL Translation - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"DBWarden includes a SQL translation\
  \ layer to support development workflows where your primary database differs from\
  \ your development database.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"SQL Translation - DBWarden Documentation\",\n    \"url\": \"\
  https://dbwarden.emiliano-go.com/sql-translation\",\n    \"description\": \"DBWarden\
  \ includes a SQL translation layer to support development workflows where your primary\
  \ database differs from your development database.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"SQL Translation\",\n        \"\
  item\": \"https://dbwarden.emiliano-go.com/sql-translation\"\n      }\n    ]\n \
  \ }\n]\n</script>\n"
---

# SQL Translation

DBWarden includes a SQL translation layer to support development workflows where your primary database differs from your development database.

The most common case is:

- Primary database: PostgreSQL/MySQL/MariaDB/ClickHouse
- Development database: SQLite (`--dev` mode)

This keeps local development fast while still allowing production-targeted schemas.

## Why SQL Translation Exists

SQLite does not support all backend-specific SQL types and default expressions used by other databases.

Without translation, generated migrations can fail in local development when they contain backend-specific types like `UUID`, `JSONB`, or default expressions like `now()`.

DBWarden translation solves this by adapting generated SQL for SQLite compatibility.

## When translation is active

Translation is applied when all are true:

- command runs with `--dev`
- selected database resolves to a SQLite `dev_database_url`
- command path generates SQL from models (`make-migrations`)

It is not a runtime SQL proxy for arbitrary manual SQL.

## How It Works

When you run commands in development mode and target a SQLite dev database:

```bash
$ dbwarden --dev make-migrations "sync models" -d primary
```

DBWarden uses this flow:

1. Loads the selected database config and resolves `dev_database_url`.
2. Detects that the active target backend is SQLite.
3. Extracts model metadata from SQLAlchemy models.
4. Translates backend-specific types/defaults to SQLite-compatible SQL.
5. Generates migration SQL with translated definitions.

Translation is applied during migration generation, not as a post-processing regex pass.

## Type conversion behavior

Common conversions:

| Source type | SQLite output |
|-------------|---------------|
| `UUID` | `TEXT` |
| `JSON` / `JSONB` | `TEXT` |
| `TIMESTAMPTZ` | `DATETIME` |
| `SERIAL` / `BIGSERIAL` | `INTEGER` |
| ClickHouse nullable numeric forms | `INTEGER`/`REAL` depending on source |

If a type cannot be translated safely:

- non-strict mode: fallback to `TEXT` + warning
- strict mode: fail migration generation

## Default expression handling

Backend expressions such as `now()` or `gen_random_uuid()` may not have direct SQLite equivalents.

In non-strict mode, unsupported defaults are dropped with warning.

In strict mode, unsupported defaults fail generation.

## Strict Translation Mode

If you want hard failures instead of fallback behavior:

```bash
$ dbwarden --dev --strict-translation make-migrations "sync models" -d primary
```

In strict mode:

- Unknown/unsupported type conversions raise errors
- Unsupported default expression conversions raise errors

Use this when you want to catch every lossy conversion early.

## Recommended team workflow

1. iterate quickly with `--dev` (SQLite)
2. keep strict checks in CI (`--strict-translation`)
3. validate release candidate migrations against production-like database

This balances speed and correctness.

## Troubleshooting

`--dev mode is enabled, but database '<name>' has no dev_database_url configured`:

- add `dev_database_url` for that database entry

Unexpected type fallback to `TEXT`:

- inspect model type for backend-specific declaration
- re-run with `--strict-translation` to fail fast and fix explicitly

Generated SQL differs from production expectations:

- expected in SQLite compatibility mode; validate final release migrations on production-like backend

## Notes and Limitations

- Translation focuses on compatibility for local development.
- Some backend features cannot be represented exactly in SQLite.
- For production accuracy, always test migrations against your production-like database too.
