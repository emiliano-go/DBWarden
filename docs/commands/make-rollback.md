---
seo:
  title: make-rollback - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/make-rollback
  robots: index,follow
  og:
    type: website
    title: make-rollback - DBWarden Documentation
    description: Generate a rollback SQL file for a given migration file.
    url: https://dbwarden.emiliano-go.com/commands/make-rollback
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: make-rollback - DBWarden Documentation
    description: Generate a rollback SQL file for a given migration file.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Generate a rollback SQL file for a given migration file.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: make-rollback - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/make-rollback
    description: Generate a rollback SQL file for a given migration file.
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
      name: make-rollback
      item: https://dbwarden.emiliano-go.com/commands/make-rollback
seo_html: "<title>make-rollback - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Generate a rollback SQL file for a given migration file.\">\n<link rel=\"\
  canonical\" href=\"https://dbwarden.emiliano-go.com/commands/make-rollback\">\n\
  <meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"make-rollback - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Generate a rollback SQL file for\
  \ a given migration file.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/make-rollback\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"make-rollback - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Generate a rollback SQL file for a given migration file.\">\n<meta name=\"\
  twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n\
  <script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"make-rollback - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/make-rollback\",\n \
  \   \"description\": \"Generate a rollback SQL file for a given migration file.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\",\n    \"\
  publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini\
  \ Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"\
  @type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Commands\",\n   \
  \     \"item\": \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n\
  \        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"\
  make-rollback\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/make-rollback\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# `make-rollback`

Generate a rollback SQL file for a given migration file.

## Usage

```bash
$ dbwarden make-rollback migrations/primary__0005_add_table.sql
```

## Arguments

- `MIGRATION_FILE` (required) - Path to the migration SQL file

## Output

Creates a `.rollback.sql` file next to the given migration file with auto-generated rollback statements.

## Supported reverse transformations

| Upgrade Pattern | Generated Rollback |
|----------------|-------------------|
| `CREATE TABLE t (...)` | `DROP TABLE IF EXISTS t;` |
| `CREATE MATERIALIZED VIEW v AS ...` | `DROP VIEW IF EXISTS v;` |
| `CREATE DICTIONARY d (...)` | `DROP DICTIONARY IF EXISTS d;` |
| `ALTER TABLE t ADD COLUMN c ...` | `ALTER TABLE t DROP COLUMN c;` |
| `CREATE INDEX i ON t (...)` | `DROP INDEX IF EXISTS i;` |
| `CREATE UNIQUE INDEX i ON t (...)` | `DROP INDEX IF EXISTS i;` |
| Other patterns | Comment-only placeholder |

## Notes

- generated rollback is conservative: it may not handle all edge cases
- always review the generated rollback before using it
- for best results, write manual rollback SQL in the `-- rollback` section of the original migration
