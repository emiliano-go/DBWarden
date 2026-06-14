---
seo:
  title: database - DBWarden Documentation
  description: Display configured databases. Config is defined in Python code via
    databaseconfig, so database list is a read-only command for viewing what's registered.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/database/
  robots: index,follow
  og:
    type: website
    title: database - DBWarden Documentation
    description: Display configured databases. Config is defined in Python code via
      databaseconfig, so database list is a read-only command for viewing what's registered.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/database/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: database - DBWarden Documentation
    description: Display configured databases. Config is defined in Python code via
      databaseconfig, so database list is a read-only command for viewing what's registered.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: database - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/database/
    description: Display configured databases. Config is defined in Python code via
      databaseconfig, so database list is a read-only command for viewing what's registered.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `database`

Display configured databases. Config is defined in Python code via `database_config()`, so
`database list` is a read-only command for viewing what's registered.

## Usage

```bash
$ dbwarden database list
```

## See also

- [`settings show`](./settings.md): detailed view of all configuration
- [Configuration docs](../configuration/index.md)

