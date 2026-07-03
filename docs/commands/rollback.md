---
seo:
  title: rollback - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/rollback
  robots: index,follow
  og:
    type: website
    title: rollback - DBWarden Documentation
    description: Rollback applied migrations using -- rollback SQL sections.
    url: https://dbwarden.emiliano-go.com/commands/rollback
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: rollback - DBWarden Documentation
    description: Rollback applied migrations using -- rollback SQL sections.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Rollback applied migrations using -- rollback SQL sections.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: rollback - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/rollback
    description: Rollback applied migrations using -- rollback SQL sections.
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
      name: rollback
      item: https://dbwarden.emiliano-go.com/commands/rollback
seo_html: "<title>rollback - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Rollback applied migrations using -- rollback SQL sections.\">\n<link\
  \ rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/rollback\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"rollback - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Rollback applied migrations using\
  \ -- rollback SQL sections.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/rollback\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"rollback - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Rollback applied migrations using --\
  \ rollback SQL sections.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"rollback - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/rollback\"\
  ,\n    \"description\": \"Rollback applied migrations using -- rollback SQL sections.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"rollback\",\n   \
  \     \"item\": \"https://dbwarden.emiliano-go.com/commands/rollback\"\n      }\n\
  \    ]\n  }\n]\n</script>\n"
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
