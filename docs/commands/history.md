---
seo:
  title: history - DBWarden Documentation
  description: Show migration execution history.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/history/
  robots: index,follow
  og:
    type: website
    title: history - DBWarden Documentation
    description: Show migration execution history.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/history/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: history - DBWarden Documentation
    description: Show migration execution history.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: history - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/history/
    description: Show migration execution history.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `history`

Show migration execution history.

## Usage

```bash
$ dbwarden history --database primary
```

## Options

- `--database`, `-d`

## Notes

- shows applied migrations, order, and timestamps
- useful for audit and incident analysis

See also: [Your First Migration](../getting-started/first-migration.md)
