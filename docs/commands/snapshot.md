---
seo:
  title: snapshot - DBWarden Documentation
  description: Output the DDL schema of a specific database table.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/snapshot/
  robots: index,follow
  og:
    type: website
    title: snapshot - DBWarden Documentation
    description: Output the DDL schema of a specific database table.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/snapshot/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: snapshot - DBWarden Documentation
    description: Output the DDL schema of a specific database table.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: snapshot - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/snapshot/
    description: Output the DDL schema of a specific database table.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
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
