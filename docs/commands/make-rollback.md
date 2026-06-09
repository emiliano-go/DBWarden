---
seo:
  title: '`make-rollback` - DBWarden Documentation'
  description: makerollback Generate a rollback SQL file for a given migration file.
    Usage bash dbwarden makerollback migrations/primary0005addtable.sql Arguments
    MIGRATIONFILE required Path to the migration SQL...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/make-rollback/
  robots: index,follow
  og:
    type: website
    title: '`make-rollback` - DBWarden Documentation'
    description: makerollback Generate a rollback SQL file for a given migration file.
      Usage bash dbwarden makerollback migrations/primary0005addtable.sql Arguments
      MIGRATIONFILE required Path to the migration SQL...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/make-rollback/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: '`make-rollback` - DBWarden Documentation'
    description: makerollback Generate a rollback SQL file for a given migration file.
      Usage bash dbwarden makerollback migrations/primary0005addtable.sql Arguments
      MIGRATIONFILE required Path to the migration SQL...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: '`make-rollback` - DBWarden Documentation'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/make-rollback/
    description: makerollback Generate a rollback SQL file for a given migration file.
      Usage bash dbwarden makerollback migrations/primary0005addtable.sql Arguments
      MIGRATIONFILE required Path to the migration SQL...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `make-rollback`

Generate a rollback SQL file for a given migration file.

## Usage

```bash
dbwarden make-rollback migrations/primary__0005_add_table.sql
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
