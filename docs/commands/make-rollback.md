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
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: make-rollback - DBWarden Documentation
    description: Generate a rollback SQL file for a given migration file.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Generate a rollback SQL file for a given migration file.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: make-rollback - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/make-rollback
    description: Generate a rollback SQL file for a given migration file.
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
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"make-rollback - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Generate a rollback SQL file for\
  \ a given migration file.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"make-rollback - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/make-rollback\"\
  ,\n    \"description\": \"Generate a rollback SQL file for a given migration file.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"make-rollback\",\n\
  \        \"item\": \"https://dbwarden.emiliano-go.com/commands/make-rollback\"\n\
  \      }\n    ]\n  }\n]\n</script>\n"
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
| Other patterns | Refused unless the migration is explicitly irreversible |

## Irreversible annotation

If the command cannot derive executable rollback SQL, it refuses to create a placeholder rollback file. To acknowledge that a migration cannot be rolled back automatically, add this comment to the migration file:

```sql
-- dbwarden: irreversible
```

With that annotation, `make-rollback` may create a rollback file that contains a clear comment instead of executable SQL. This is an intentional declaration, not a successful rollback.

## Notes

- Generated rollback is conservative and may not handle all edge cases.
- Always review the generated rollback before using it.
- For best results, write executable rollback SQL in the `-- rollback` section of the original migration.
- Do not commit placeholder rollback unless the migration is explicitly declared irreversible.
