---
seo:
  title: init - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/init
  robots: index,follow
  og:
    type: website
    title: init - DBWarden Documentation
    description: Initialize DBWarden project scaffolding.
    url: https://dbwarden.emiliano-go.com/commands/init
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: init - DBWarden Documentation
    description: Initialize DBWarden project scaffolding.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Initialize DBWarden project scaffolding.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: init - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/init
    description: Initialize DBWarden project scaffolding.
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
      name: init
      item: https://dbwarden.emiliano-go.com/commands/init
seo_html: "<title>init - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Initialize DBWarden project scaffolding.\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/commands/init\">\n<meta name=\"robots\"\
  \ content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta\
  \ property=\"og:title\" content=\"init - DBWarden Documentation\">\n<meta property=\"\
  og:description\" content=\"Initialize DBWarden project scaffolding.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/commands/init\">\n<meta property=\"\
  og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n<meta\
  \ property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"init - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Initialize DBWarden project scaffolding.\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n<script type=\"\
  application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"\
  @type\": \"WebPage\",\n    \"name\": \"init - DBWarden Documentation\",\n    \"\
  url\": \"https://dbwarden.emiliano-go.com/commands/init\",\n    \"description\"\
  : \"Initialize DBWarden project scaffolding.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Commands\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/commands\"\n      },\n \
  \     {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"\
  name\": \"init\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/init\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
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
