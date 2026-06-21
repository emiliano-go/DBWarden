---
seo:
  title: check-db - DBWarden Documentation
  description: Inspect live database schema.
  canonical: https://emiliano-go.github.io/DBWarden/commands/check-db/
  robots: index,follow
  og:
    type: website
    title: check-db - DBWarden Documentation
    description: Inspect live database schema.
    url: https://emiliano-go.github.io/DBWarden/commands/check-db/
    image: https://emiliano-go.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: check-db - DBWarden Documentation
    description: Inspect live database schema.
    image: https://emiliano-go.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: check-db - DBWarden Documentation
    url: https://emiliano-go.github.io/DBWarden/commands/check-db/
    description: Inspect live database schema.
    image: https://emiliano-go.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `check-db`

Inspect live database schema.

## Usage

```bash
$ dbwarden check-db --database primary
$ dbwarden check-db --database primary --out json
$ dbwarden check-db --database primary --out yaml
```

## Options

- `--database`, `-d`
- `--out`, `-o` (`txt`, `json`, `yaml`, `sql`)

## Notes

- useful for schema inspection and diagnostics
- complements `status` and `history`

See also: [Your First Migration](../getting-started/first-migration.md)
