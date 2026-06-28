---
seo:
  title: init - DBWarden Documentation
  description: Initialize DBWarden project scaffolding.
  canonical: https://dbwarden.emiliano-go.com/commands/init/
  robots: index,follow
  og:
    type: website
    title: init - DBWarden Documentation
    description: Initialize DBWarden project scaffolding.
    url: https://dbwarden.emiliano-go.com/commands/init/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: init - DBWarden Documentation
    description: Initialize DBWarden project scaffolding.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: init - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/init/
    description: Initialize DBWarden project scaffolding.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `init`

Initialize DBWarden project scaffolding.

## Usage

```bash
$ dbwarden init
$ dbwarden init --database primary
```

## What it does

- creates `migrations/` and `migrations/<database>/` if missing
- creates/updates config scaffold (`dbwarden.py`) if needed
- does not mutate your database schema

## Notes

- safe to run multiple times
- first command to run in a new project

See also: [Configuration](../configuration/index.md)
