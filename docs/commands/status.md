---
seo:
  title: status - DBWarden Documentation
  description: Show migration status applied vs pending.
  canonical: https://dbwarden.emiliano-go.com/commands/status/
  robots: index,follow
  og:
    type: website
    title: status - DBWarden Documentation
    description: Show migration status applied vs pending.
    url: https://dbwarden.emiliano-go.com/commands/status/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: status - DBWarden Documentation
    description: Show migration status applied vs pending.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: status - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/status/
    description: Show migration status applied vs pending.
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
      name: status
      item: https://emiliano-go.github.io/DBWarden/commands/status/
    - '@type': ListItem
      position: 3
      name: status
---

# `status`

Show migration status (applied vs pending).

## Usage

```bash
$ dbwarden status --database primary
$ dbwarden status --all
```

## Options

- `--database`, `-d`
- `--all`, `-a`

## Notes

- run before and after migration execution
- supports multi-database status with `--all`

See also: [Your First Migration](../getting-started/first-migration.md)
