---
seo:
  title: '`migrate` - DBWarden Documentation'
  description: migrate Apply pending migrations. Usage bash dbwarden migrate database
    primary dbwarden migrate all dbwarden migrate database primary toversion 0010
    dbwarden migrate database primary count 2 dbwarden...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/migrate/
  robots: index,follow
  og:
    type: website
    title: '`migrate` - DBWarden Documentation'
    description: migrate Apply pending migrations. Usage bash dbwarden migrate database
      primary dbwarden migrate all dbwarden migrate database primary toversion 0010
      dbwarden migrate database primary count 2 dbwarden...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/migrate/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: '`migrate` - DBWarden Documentation'
    description: migrate Apply pending migrations. Usage bash dbwarden migrate database
      primary dbwarden migrate all dbwarden migrate database primary toversion 0010
      dbwarden migrate database primary count 2 dbwarden...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: '`migrate` - DBWarden Documentation'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/migrate/
    description: migrate Apply pending migrations. Usage bash dbwarden migrate database
      primary dbwarden migrate all dbwarden migrate database primary toversion 0010
      dbwarden migrate database primary count 2 dbwarden...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `migrate`

Apply pending migrations.

## Usage

```bash
dbwarden migrate --database primary
dbwarden migrate --all
dbwarden migrate --database primary --to-version 0010
dbwarden migrate --database primary --count 2
dbwarden migrate --database primary --with-backup --backup-dir ./backups
dbwarden migrate --database primary --baseline --to-version 0005
```

## Options

- `--database`, `-d`
- `--all`, `-a`
- `--count`, `-c`
- `--to-version`, `-t`
- `--baseline`
- `--with-backup`, `-b`
- `--backup-dir`
- `--verbose`, `-v`

## Notes

- creates metadata/lock tables if needed
- executes versioned + repeatable migrations
- uses lock protection to prevent concurrent migration mutation

See also: [Applying Migrations](../tutorial/applying-migrations.md)
