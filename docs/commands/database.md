---
seo:
  title: database - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/database
  robots: index,follow
  og:
    type: website
    title: database - DBWarden Documentation
    description: Display configured databases. Config is defined in Python code via
      databaseconfig, so database list is a read-only command for viewing what's registered.
    url: https://dbwarden.emiliano-go.com/commands/database
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: database - DBWarden Documentation
    description: Display configured databases. Config is defined in Python code via
      databaseconfig, so database list is a read-only command for viewing what's registered.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Display configured databases. Config is defined in Python code via
    databaseconfig, so database list is a read-only command for viewing what's registered.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: database - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/database
    description: Display configured databases. Config is defined in Python code via
      databaseconfig, so database list is a read-only command for viewing what's registered.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Commands
      item: https://dbwarden.emiliano-go.com/commands
    - '@type': ListItem
      position: 2
      name: database
      item: https://dbwarden.emiliano-go.com/commands/database
seo_html: "<title>database - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Display configured databases. Config is defined in Python code via databaseconfig,\
  \ so database list is a read-only command for viewing what&#x27;s registered.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/database\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"database - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Display configured databases. Config\
  \ is defined in Python code via databaseconfig, so database list is a read-only\
  \ command for viewing what&#x27;s registered.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/commands/database\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n<meta property=\"\
  og:image:width\" content=\"128\">\n<meta property=\"og:image:height\" content=\"\
  128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta\
  \ name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"database - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Display configured databases. Config is defined in Python code via databaseconfig,\
  \ so database list is a read-only command for viewing what&#x27;s registered.\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"database - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/database\",\n    \"\
  description\": \"Display configured databases. Config is defined in Python code\
  \ via databaseconfig, so database list is a read-only command for viewing what's\
  \ registered.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Commands\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/commands\"\n      },\n \
  \     {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"\
  name\": \"database\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/database\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
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

