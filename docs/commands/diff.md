---
seo:
  title: diff - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/diff
  robots: index,follow
  og:
    type: website
    title: diff - DBWarden Documentation
    description: 'Show structural differences between SQLAlchemy models and a live
      database. Read-only: no files are written.'
    url: https://dbwarden.emiliano-go.com/commands/diff
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: diff - DBWarden Documentation
    description: 'Show structural differences between SQLAlchemy models and a live
      database. Read-only: no files are written.'
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: 'Show structural differences between SQLAlchemy models and a live database.
    Read-only: no files are written.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: diff - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/diff
    description: 'Show structural differences between SQLAlchemy models and a live
      database. Read-only: no files are written.'
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Commands
      item: https://dbwarden.emiliano-go.com/commands
    - '@type': ListItem
      position: 2
      name: diff
      item: https://dbwarden.emiliano-go.com/commands/diff
seo_html: "<title>diff - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Show structural differences between SQLAlchemy models and a live database.\
  \ Read-only: no files are written.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/diff\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"diff - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Show structural differences between\
  \ SQLAlchemy models and a live database. Read-only: no files are written.\">\n<meta\
  \ property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/diff\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"diff - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Show structural differences between SQLAlchemy models and a live database.\
  \ Read-only: no files are written.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"diff - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/diff\",\n    \"description\"\
  : \"Show structural differences between SQLAlchemy models and a live database. Read-only:\
  \ no files are written.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Commands\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/commands\"\n      },\n \
  \     {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"\
  name\": \"diff\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/diff\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# `diff`

Show structural differences between SQLAlchemy models and a live database.
Read-only: no files are written.

## Usage

```bash
$ dbwarden diff --database primary
$ dbwarden diff --database primary --out json
$ dbwarden diff --database primary --out sql
$ dbwarden diff --database primary --offline
```

## Options

| Option | Description |
|--------|-------------|
| `--database`, `-d` | Target database name |
| `--out`, `-o` | Output format: `table` (default), `json`, `sql` |
| `--offline` | Use exported model state file instead of live DB snapshot |
| `--verbose`, `-v` | Enable verbose logging |

## Output formats

### `table` (default)

Displays a Rich table with columns: Operation, Table, Target, Severity.

```text
          Schema Diff           
┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━┓
┃ Operation    ┃ Table ┃ Target ┃ Severity┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━┩
│ add_column   │ users │ email  │ INFO    │
│ drop_column  │ users │ name   │ WARNING │
└──────────────┴───────┴────────┴─────────┘
```

### `json`

```json
[
  {"operation": "add_column", "table": "users", "target": "email", "severity": "INFO"},
  {"operation": "drop_column", "table": "users", "target": "name", "severity": "WARNING"}
]
```

### `sql`

Prints the raw migration SQL that would be generated.

## Offline mode

Requires a model state file created by `dbwarden export-models`:

```bash
$ dbwarden export-models --database primary
# Switch to offline machine
$ dbwarden diff --database primary --offline
```

## See also

- [`make-migrations`](./make-migrations.md): generates migration files from diffs
- [`check`](./check.md): safety analyzer for schema changes
- [`check-db`](./check-db.md): inspect live database schema
