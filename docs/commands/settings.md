---
seo:
  title: settings - DBWarden Documentation
  description: View DBWarden configuration. All database settings are defined in Python
    code via databaseconfig, so settings show is a read-only command for inspecting
    the...
  canonical: https://dbwarden.emiliano-go.com/commands/settings/
  robots: index,follow
  og:
    type: website
    title: settings - DBWarden Documentation
    description: View DBWarden configuration. All database settings are defined in
      Python code via databaseconfig, so settings show is a read-only command for
      inspecting the...
    url: https://dbwarden.emiliano-go.com/commands/settings/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: settings - DBWarden Documentation
    description: View DBWarden configuration. All database settings are defined in
      Python code via databaseconfig, so settings show is a read-only command for
      inspecting the...
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: settings - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/settings/
    description: View DBWarden configuration. All database settings are defined in
      Python code via databaseconfig, so settings show is a read-only command for
      inspecting the...
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Commands
      item: https://emiliano-go.github.io/DBWarden/commands/
    - '@type': ListItem
      position: 2
      name: settings
      item: https://emiliano-go.github.io/DBWarden/commands/settings/
    - '@type': ListItem
      position: 3
      name: settings
---

# `settings`

View DBWarden configuration. All database settings are defined in Python code via
`database_config()`, so `settings show` is a read-only command for inspecting
the current configuration.

## `settings show`

### Usage

```bash
$ dbwarden settings show
$ dbwarden settings show primary
$ dbwarden settings show --all
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

