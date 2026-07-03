---
seo:
  title: snapshot - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/snapshot
  robots: index,follow
  og:
    type: website
    title: snapshot - DBWarden Documentation
    description: Output the DDL schema of a specific database table.
    url: https://dbwarden.emiliano-go.com/commands/snapshot
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: snapshot - DBWarden Documentation
    description: Output the DDL schema of a specific database table.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Output the DDL schema of a specific database table.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: snapshot - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/snapshot
    description: Output the DDL schema of a specific database table.
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
      name: snapshot
      item: https://dbwarden.emiliano-go.com/commands/snapshot
seo_html: "<title>snapshot - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Output the DDL schema of a specific database table.\">\n<link rel=\"\
  canonical\" href=\"https://dbwarden.emiliano-go.com/commands/snapshot\">\n<meta\
  \ name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"snapshot - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Output the DDL schema of a specific\
  \ database table.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/snapshot\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"snapshot - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Output the DDL schema of a specific database table.\">\n<meta name=\"\
  twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n\
  <script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"snapshot - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/snapshot\",\n    \"\
  description\": \"Output the DDL schema of a specific database table.\",\n    \"\
  image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"snapshot\",\n   \
  \     \"item\": \"https://dbwarden.emiliano-go.com/commands/snapshot\"\n      }\n\
  \    ]\n  }\n]\n</script>\n"
---

# `snapshot`

Output the DDL schema of a specific database table.

## Usage

```bash
$ dbwarden snapshot users --database primary
```

## Options

- `TABLE` (required) - Name of the table to snapshot
- `--database`, `-d`

## Output

For standard SQL databases (SQLite, PostgreSQL, MySQL, MariaDB):

- `CREATE TABLE` statement with column types, nullability, and defaults
- `CREATE INDEX` statements
- Foreign key constraints

For ClickHouse:

- The raw `CREATE TABLE` query from `system.tables`

## Notes

- output is printed to stdout
- useful for debugging schema differences or documenting table structure
- internally uses `sqlalchemy.inspect()` for generic databases
