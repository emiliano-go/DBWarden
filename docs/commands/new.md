---
seo:
  title: new - DBWarden Documentation
  description: Create a manual migration file.
  canonical: https://dbwarden.emiliano-go.com/commands/new/
  robots: index,follow
  og:
    type: website
    title: new - DBWarden Documentation
    description: Create a manual migration file.
    url: https://dbwarden.emiliano-go.com/commands/new/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: new - DBWarden Documentation
    description: Create a manual migration file.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: new - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/new/
    description: Create a manual migration file.
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
      name: new
      item: https://emiliano-go.github.io/DBWarden/commands/new/
    - '@type': ListItem
      position: 3
      name: new
---

# `new`

Create a manual migration file.

## Usage

```bash
$ dbwarden new "manual hotfix" --database primary
$ dbwarden new "backfill users" --database primary --version 0042
$ dbwarden new "seed data" --database primary --type ra
$ dbwarden new "update view" --database primary --type roc
```

## Options

- positional `description`
- `--database`, `-d`
- `--version`
- `--type`, `-t`: Migration type: `versioned` (default), `ra` / `runs_always`, or `roc` / `runs_on_change`

## Notes

- use when change is not model-driven
- file is scaffolded with `-- upgrade` and `-- rollback` sections

See also: [Your First Migration](../getting-started/first-migration.md)
