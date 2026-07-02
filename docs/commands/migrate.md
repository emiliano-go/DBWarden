---
seo:
  title: migrate - DBWarden Documentation
  description: Apply pending migrations.
  canonical: https://dbwarden.emiliano-go.com/commands/migrate/
  robots: index,follow
  og:
    type: website
    title: migrate - DBWarden Documentation
    description: Apply pending migrations.
    url: https://dbwarden.emiliano-go.com/commands/migrate/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: migrate - DBWarden Documentation
    description: Apply pending migrations.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: migrate - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/migrate/
    description: Apply pending migrations.
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
      name: migrate
      item: https://emiliano-go.github.io/DBWarden/commands/migrate/
    - '@type': ListItem
      position: 3
      name: migrate
---

# `migrate`

Apply pending migrations.

## Usage

```bash
$ dbwarden migrate --database primary
$ dbwarden migrate --all
$ dbwarden migrate --database primary --to-version 0010
$ dbwarden migrate --database primary --count 2
$ dbwarden migrate --database primary --with-backup --backup-dir ./backups
$ dbwarden migrate --database primary --baseline --to-version 0005
```

## Options

- `--database`, `-d`
- `--all`, `-a`
- `--count`, `-c`
- `--to-version`, `-t`
- `--baseline`
- `--with-backup`, `-b`
- `--backup-dir`
- `--dry-run`: preview changes without applying
- `--sandbox`: apply in a temporary sandbox database
- `--apply-seeds`: apply pending seeds after migrations
- `--verbose`, `-v`

## Notes

- creates metadata/lock tables if needed
- executes versioned + repeatable migrations
- uses lock protection to prevent concurrent migration mutation

See also: [Your First Migration](../getting-started/first-migration.md)
