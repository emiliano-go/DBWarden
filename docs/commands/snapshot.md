---
seo:
  title: snapshot - DBWarden Documentation
  description: Output the DDL schema of a specific database table.
  canonical: https://dbwarden.emiliano-go.com/commands/snapshot/
  robots: index,follow
  og:
    type: website
    title: snapshot - DBWarden Documentation
    description: Output the DDL schema of a specific database table.
    url: https://dbwarden.emiliano-go.com/commands/snapshot/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: snapshot - DBWarden Documentation
    description: Output the DDL schema of a specific database table.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: snapshot - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/snapshot/
    description: Output the DDL schema of a specific database table.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Commands
      item: https://emiliano-go.github.io/DBWarden/commands/
    - '@type': ListItem
      position: 2
      name: snapshot
      item: https://emiliano-go.github.io/DBWarden/commands/snapshot/
    - '@type': ListItem
      position: 3
      name: snapshot
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
