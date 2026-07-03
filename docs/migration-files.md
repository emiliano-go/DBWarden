---
seo:
  title: Migration File Format - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/migration-files
  robots: index,follow
  og:
    type: website
    title: Migration File Format - DBWarden Documentation
    description: Migration files are the execution contract in DBWarden.
    url: https://dbwarden.emiliano-go.com/migration-files
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Migration File Format - DBWarden Documentation
    description: Migration files are the execution contract in DBWarden.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Migration files are the execution contract in DBWarden.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Migration File Format - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/migration-files
    description: Migration files are the execution contract in DBWarden.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Migration File Format
      item: https://dbwarden.emiliano-go.com/migration-files
seo_html: "<title>Migration File Format - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Migration files are the execution contract in DBWarden.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/migration-files\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Migration File Format - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Migration files\
  \ are the execution contract in DBWarden.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/migration-files\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n<meta property=\"\
  og:image:width\" content=\"128\">\n<meta property=\"og:image:height\" content=\"\
  128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta\
  \ name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"Migration File Format - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Migration files are the execution contract in DBWarden.\">\n<meta name=\"\
  twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n\
  <script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Migration File Format - DBWarden\
  \ Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/migration-files\"\
  ,\n    \"description\": \"Migration files are the execution contract in DBWarden.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\",\n    \"\
  publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini\
  \ Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"\
  @type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Migration File Format\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/migration-files\"\n    \
  \  }\n    ]\n  }\n]\n</script>\n"
---

# Migration File Format

Migration files are the execution contract in DBWarden.

Everything that changes your database should be represented in explicit SQL files that can be reviewed, tested, and rolled back.

## File naming and location

Versioned migrations are stored under each database migrations directory (default: `migrations/<database_name>`).

Canonical filename pattern:

```text
{database_name}__{version}_{description}.sql
```

A legacy format without the `{database_name}__` prefix (e.g. `0001_create_users_table.sql`) is also accepted for backward compatibility.

Examples:

```text
primary__0001_initial_schema.sql
primary__0002_add_users_table.sql
analytics__0001_create_events.sql
```

When a migration is auto-generated with `make-migrations`, DBWarden also writes a companion plan file:

```text
primary__0001_initial_schema.plan.json
```

That file captures machine-readable metadata for CI and debugging and is not executed by `migrate`.

## Required sections

Each migration file must define both:

```sql
-- upgrade

-- rollback
```

- `-- upgrade`: statements applied during `migrate`
- `-- rollback`: statements applied during `rollback`

If rollback is weak or incomplete, production recovery is weak or incomplete.

## Migration classes

DBWarden supports three execution classes:

| Prefix | Class | Behavior |
|--------|-------|----------|
| `NNNN_` | Versioned | Runs once in ordered version sequence |
| `RA__` | Runs always | Runs on every `migrate` execution |
| `ROC__` | Runs on change | Runs when checksum changed |

### When to use each

- `NNNN_`: schema evolution (tables, columns, indexes, constraints)
- `RA__`: objects that should always be refreshed (views, grants)
- `ROC__`: routines/policies that should apply only when content changes

## Execution model

At runtime, DBWarden builds an execution plan from file discovery + migration metadata:

1. read versioned files and filter already-applied versions
2. include `RA__` files
3. include changed `ROC__` files
4. execute with lock protection
5. record metadata and checksums

Conceptual plan:

```python
def build_plan(directory, applied_versions):
    versioned = parse_versioned_files(directory)
    repeatable = parse_repeatable_files(directory)
    pending_versioned = [m for m in versioned if m.version not in applied_versions]
    pending_ra = repeatable.runs_always
    pending_roc = changed_only(repeatable.runs_on_change)
    return pending_versioned + pending_ra + pending_roc
```

## Examples

### Versioned migration

```sql
-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME
);

-- rollback

DROP TABLE users;
```

### Runs-always migration (`RA__`)

Filename example: `primary__RA__refresh_active_users_view.sql`

```sql
-- upgrade

CREATE OR REPLACE VIEW active_users AS
SELECT id, email FROM users WHERE is_active = TRUE;

-- rollback

DROP VIEW IF EXISTS active_users;
```

### Runs-on-change migration (`ROC__`)

Filename example: `primary__ROC__update_timestamp_trigger.sql`

```sql
-- upgrade

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- rollback

DROP FUNCTION IF EXISTS update_updated_at();
```

## Metadata headers

Headers are parsed from migration file comments. The `-- seed` marker is recognised
by tools; `-- depends_on` parsing is implemented but **not yet enforced** during
migration execution (migrations run in filesystem-sort order by version).

Dependency header (parsed but not enforced):

```sql
-- depends_on: ["0004", "0005"]
```

Seed marker:

```sql
-- seed
```

## Authoring guidelines

- One logical change per migration file
- Keep DDL explicit; avoid hidden application-side schema effects
- Keep rollback idempotent when possible (`IF EXISTS`, safe predicates)
- For data migrations, use bounded, reversible operations
- Prefer small migrations over large monolithic SQL scripts

## Review checklist

Before merge:

- upgrade section matches intended schema change
- rollback section restores prior valid state
- indexes/constraints/defaults are explicit
- no environment-specific literals accidentally committed

Before release:

```bash
$ dbwarden status --database primary
$ dbwarden migrate --database primary
$ dbwarden rollback --database primary --count 1
$ dbwarden migrate --database primary
```


