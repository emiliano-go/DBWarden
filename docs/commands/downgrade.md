---
seo:
  title: downgrade - DBWarden Documentation
  description: Revert applied migrations to reach a specific target version.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/downgrade/
  robots: index,follow
  og:
    type: website
    title: downgrade - DBWarden Documentation
    description: Revert applied migrations to reach a specific target version.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/downgrade/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: downgrade - DBWarden Documentation
    description: Revert applied migrations to reach a specific target version.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: downgrade - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/downgrade/
    description: Revert applied migrations to reach a specific target version.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `downgrade`

Revert applied migrations to reach a specific target version.

## Usage

```bash
$ dbwarden downgrade --to 0005 --database primary
```

## Options

- `--to`, `-t` (required) - Target version to downgrade to
- `--database`, `-d`
- `--verbose`, `-v`

## Notes

- reads `-- rollback` sections from migration files and applies them in reverse order
- only reverts versions after the target version; versions at or before the target are preserved
- same lock discipline as `migrate` and `rollback`
- fails if the target version has not been applied

See also: [rollback](rollback.md)
