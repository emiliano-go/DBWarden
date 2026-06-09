---
seo:
  title: '`settings` - DBWarden Documentation'
  description: settings View DBWarden configuration. All database settings are defined
    in Python code via databaseconfig, so settings show is a readonly command for
    inspecting the current configuration. settings...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/settings/
  robots: index,follow
  og:
    type: website
    title: '`settings` - DBWarden Documentation'
    description: settings View DBWarden configuration. All database settings are defined
      in Python code via databaseconfig, so settings show is a readonly command for
      inspecting the current configuration. settings...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/settings/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: '`settings` - DBWarden Documentation'
    description: settings View DBWarden configuration. All database settings are defined
      in Python code via databaseconfig, so settings show is a readonly command for
      inspecting the current configuration. settings...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: '`settings` - DBWarden Documentation'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/settings/
    description: settings View DBWarden configuration. All database settings are defined
      in Python code via databaseconfig, so settings show is a readonly command for
      inspecting the current configuration. settings...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `settings`

View DBWarden configuration. All database settings are defined in Python code via
`database_config()`, so `settings show` is a read-only command for inspecting
the current configuration.

## `settings show`

### Usage

```bash
dbwarden settings show
dbwarden settings show primary
dbwarden settings show --all
```

### Options

- `--all`, `-a`: show all configured databases

### Example output

```
Database: PRIMARY (default)
  • Default: True
  • Type: SQLite
  • URL: sqlite:///./app.db
  • Migrations Directory: migrations/primary
  • Migration Table: _dbwarden_migrations
  • Seed Table: _dbwarden_seeds
  • Model Paths: ['app']
  • Dev Database Type: None
  • Dev Database URL: None
  • Overlap Models: False
```

## See also

- [`database list`](./database.md)
- [Configuration docs](../configuration/index.md)

