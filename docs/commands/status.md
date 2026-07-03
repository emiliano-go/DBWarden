---
seo:
  title: status - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/status
  robots: index,follow
  og:
    type: website
    title: status - DBWarden Documentation
    description: Show migration status applied vs pending.
    url: https://dbwarden.emiliano-go.com/commands/status
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: status - DBWarden Documentation
    description: Show migration status applied vs pending.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Show migration status applied vs pending.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: status - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/status
    description: Show migration status applied vs pending.
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
      name: status
      item: https://dbwarden.emiliano-go.com/commands/status
seo_html: "<title>status - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Show migration status applied vs pending.\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/commands/status\">\n<meta name=\"robots\"\
  \ content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta\
  \ property=\"og:title\" content=\"status - DBWarden Documentation\">\n<meta property=\"\
  og:description\" content=\"Show migration status applied vs pending.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/commands/status\">\n<meta property=\"\
  og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"status - DBWarden Documentation\">\n<meta\
  \ name=\"twitter:description\" content=\"Show migration status applied vs pending.\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"status - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/status\"\
  ,\n    \"description\": \"Show migration status applied vs pending.\",\n    \"image\"\
  : \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  ,\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"status\",\n     \
  \   \"item\": \"https://dbwarden.emiliano-go.com/commands/status\"\n      }\n  \
  \  ]\n  }\n]\n</script>\n"
---

# `status`

Show migration status (applied vs pending).

## Usage

```bash
$ dbwarden status --database primary
$ dbwarden status --all
```

## Options

- `--database`, `-d`
- `--all`, `-a`

## Notes

- run before and after migration execution
- supports multi-database status with `--all`

See also: [Your First Migration](../getting-started/first-migration.md)
