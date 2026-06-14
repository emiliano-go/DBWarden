---
seo:
  title: new - DBWarden Documentation
  description: Create a manual migration file.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/new/
  robots: index,follow
  og:
    type: website
    title: new - DBWarden Documentation
    description: Create a manual migration file.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/new/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: new - DBWarden Documentation
    description: Create a manual migration file.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: new - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/new/
    description: Create a manual migration file.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
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
