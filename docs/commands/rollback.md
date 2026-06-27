---
seo:
  title: rollback - DBWarden Documentation
  description: Rollback applied migrations using -- rollback SQL sections.
  canonical: https://dbwarden.emiliano-go.com/commands/rollback/
  robots: index,follow
  og:
    type: website
    title: rollback - DBWarden Documentation
    description: Rollback applied migrations using -- rollback SQL sections.
    url: https://dbwarden.emiliano-go.com/commands/rollback/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: rollback - DBWarden Documentation
    description: Rollback applied migrations using -- rollback SQL sections.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: rollback - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/rollback/
    description: Rollback applied migrations using -- rollback SQL sections.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `rollback`

Rollback applied migrations using `-- rollback` SQL sections.

## Usage

```bash
$ dbwarden rollback --database primary
$ dbwarden rollback --database primary --count 2
$ dbwarden rollback --database primary --to-version 0007
```

## Options

- `--database`, `-d`
- `--count`, `-c`
- `--to-version`, `-t`
- `--verbose`, `-v`

## Notes

- rollback runs in reverse order
- same lock discipline as migrate

See also: [Your First Migration](../getting-started/first-migration.md)
