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
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: init - DBWarden Documentation
    description: Initialize DBWarden project scaffolding.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Initialize DBWarden project scaffolding.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: init - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/init
    description: Initialize DBWarden project scaffolding.
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
      name: init
      item: https://dbwarden.emiliano-go.com/commands/init
seo_html: "<title>init - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Initialize DBWarden project scaffolding.\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/commands/init\">\n<meta name=\"robots\"\
  \ content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta\
  \ property=\"og:title\" content=\"init - DBWarden Documentation\">\n<meta property=\"\
  og:description\" content=\"Initialize DBWarden project scaffolding.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/commands/init\">\n<meta property=\"\
  og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"init - DBWarden Documentation\">\n<meta\
  \ name=\"twitter:description\" content=\"Initialize DBWarden project scaffolding.\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"init - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/init\"\
  ,\n    \"description\": \"Initialize DBWarden project scaffolding.\",\n    \"image\"\
  : \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  ,\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"init\",\n       \
  \ \"item\": \"https://dbwarden.emiliano-go.com/commands/init\"\n      }\n    ]\n\
  \  }\n]\n</script>\n"
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
