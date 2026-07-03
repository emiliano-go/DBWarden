---
seo:
  title: settings - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/settings
  robots: index,follow
  og:
    type: website
    title: settings - DBWarden Documentation
    description: View DBWarden configuration. All database settings are defined in
      Python code via databaseconfig, so settings show is a read-only command for
      inspecting the...
    url: https://dbwarden.emiliano-go.com/commands/settings
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: settings - DBWarden Documentation
    description: View DBWarden configuration. All database settings are defined in
      Python code via databaseconfig, so settings show is a read-only command for
      inspecting the...
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: View DBWarden configuration. All database settings are defined in Python
    code via databaseconfig, so settings show is a read-only command for inspecting
    the...
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: settings - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/settings
    description: View DBWarden configuration. All database settings are defined in
      Python code via databaseconfig, so settings show is a read-only command for
      inspecting the...
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
      logo: https://dbwarden.emiliano-go.com/assets/images/og-image.png
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Commands
      item: https://dbwarden.emiliano-go.com/commands
    - '@type': ListItem
      position: 2
      name: settings
      item: https://dbwarden.emiliano-go.com/commands/settings
seo_html: "<title>settings - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"View DBWarden configuration. All database settings are defined in Python\
  \ code via databaseconfig, so settings show is a read-only command for inspecting\
  \ the...\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/settings\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"settings - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"View DBWarden configuration. All\
  \ database settings are defined in Python code via databaseconfig, so settings show\
  \ is a read-only command for inspecting the...\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/commands/settings\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"settings - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"View DBWarden configuration. All database\
  \ settings are defined in Python code via databaseconfig, so settings show is a\
  \ read-only command for inspecting the...\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"settings - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/settings\",\n    \"\
  description\": \"View DBWarden configuration. All database settings are defined\
  \ in Python code via databaseconfig, so settings show is a read-only command for\
  \ inspecting the...\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"settings\",\n   \
  \     \"item\": \"https://dbwarden.emiliano-go.com/commands/settings\"\n      }\n\
  \    ]\n  }\n]\n</script>\n"
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

