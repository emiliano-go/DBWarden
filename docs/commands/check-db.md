---
seo:
  title: check-db - DBWarden Documentation
  description: Inspect live database schema.
  canonical: https://dbwarden.emiliano-go.com/commands/check-db/
  robots: index,follow
  og:
    type: website
    title: check-db - DBWarden Documentation
    description: Inspect live database schema.
    url: https://dbwarden.emiliano-go.com/commands/check-db/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: check-db - DBWarden Documentation
    description: Inspect live database schema.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: check-db - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/check-db/
    description: Inspect live database schema.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
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
