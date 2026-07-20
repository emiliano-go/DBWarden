---
seo:
  title: check - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/check
  robots: index,follow
  og:
    type: website
    title: check - DBWarden Documentation
    description: Analyze schema differences between your SQLAlchemy models and the
      live database.
    url: https://dbwarden.emiliano-go.com/commands/check
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: check - DBWarden Documentation
    description: Analyze schema differences between your SQLAlchemy models and the
      live database.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Analyze schema differences between your SQLAlchemy models and the live
    database.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: check - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/check
    description: Analyze schema differences between your SQLAlchemy models and the
      live database.
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
      name: check
      item: https://dbwarden.emiliano-go.com/commands/check
seo_html: "<title>check - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Analyze schema differences between your SQLAlchemy models and the live\
  \ database.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/check\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"check - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Analyze schema differences between\
  \ your SQLAlchemy models and the live database.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/commands/check\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"check - DBWarden Documentation\">\n<meta\
  \ name=\"twitter:description\" content=\"Analyze schema differences between your\
  \ SQLAlchemy models and the live database.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"check - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/check\",\n    \"description\"\
  : \"Analyze schema differences between your SQLAlchemy models and the live database.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"check\",\n      \
  \  \"item\": \"https://dbwarden.emiliano-go.com/commands/check\"\n      }\n    ]\n\
  \  }\n]\n</script>\n"
---

# `check`

Analyze schema differences between your SQLAlchemy models and the live database.

## Usage

```bash
$ dbwarden check --database primary
$ dbwarden check --database primary --force
$ dbwarden check --database primary --out json
```

## Options

- `--database`, `-d` - Target database
- `--out`, `-o` - Output format: `txt` or `json`
- `--force` - Allow warning-level changes to pass

## Severity model

- `INFO` - safe changes like adding a projection or adding a new object
- `WARNING` - risky changes that require `--force`
- `ERROR` - blocked changes such as partition/order key changes

## Current behavior

DBWarden runs generic safety checks for all backends, covering column type changes, nullability changes, default changes, and table operations. For ClickHouse specifically, additional checks classify changes for:

- added or removed columns
- type changes
- engine changes
- TTL changes
- `ORDER BY` changes
- `PARTITION BY` changes
- materialized view query changes
- projection additions/removals

## Notes

- warning-level changes exit non-zero unless `--force` is provided
- error-level changes remain blocking even with `--force`
- output is based on live database inspection plus current model metadata
