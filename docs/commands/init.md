---
seo:
  title: '`init` - DBWarden Documentation'
  description: init Initialize DBWarden project scaffolding. Usage bash dbwarden init
    dbwarden init database primary What it does creates migrations/ and migrations/<database/
    if missing creates/updates config...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/init/
  robots: index,follow
  og:
    type: website
    title: '`init` - DBWarden Documentation'
    description: init Initialize DBWarden project scaffolding. Usage bash dbwarden
      init dbwarden init database primary What it does creates migrations/ and migrations/<database/
      if missing creates/updates config...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/init/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: '`init` - DBWarden Documentation'
    description: init Initialize DBWarden project scaffolding. Usage bash dbwarden
      init dbwarden init database primary What it does creates migrations/ and migrations/<database/
      if missing creates/updates config...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: '`init` - DBWarden Documentation'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/init/
    description: init Initialize DBWarden project scaffolding. Usage bash dbwarden
      init dbwarden init database primary What it does creates migrations/ and migrations/<database/
      if missing creates/updates config...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `init`

Initialize DBWarden project scaffolding.

## Usage

```bash
dbwarden init
dbwarden init --database primary
```

## What it does

- creates `migrations/` and `migrations/<database>/` if missing
- creates/updates config scaffold (`dbwarden.py`) if needed
- does not mutate your database schema

## Notes

- safe to run multiple times
- first command to run in a new project

See also: [Configuration](../configuration/index.md)
