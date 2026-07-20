---
seo:
  title: downgrade - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/downgrade
  robots: index,follow
  og:
    type: website
    title: downgrade - DBWarden Documentation
    description: Revert applied migrations to reach a specific target version.
    url: https://dbwarden.emiliano-go.com/commands/downgrade
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: downgrade - DBWarden Documentation
    description: Revert applied migrations to reach a specific target version.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Revert applied migrations to reach a specific target version.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: downgrade - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/downgrade
    description: Revert applied migrations to reach a specific target version.
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
      name: downgrade
      item: https://dbwarden.emiliano-go.com/commands/downgrade
seo_html: "<title>downgrade - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Revert applied migrations to reach a specific target version.\">\n<link\
  \ rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/downgrade\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"downgrade - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Revert applied migrations to reach\
  \ a specific target version.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/downgrade\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"downgrade - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Revert applied migrations to reach\
  \ a specific target version.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"downgrade - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/downgrade\"\
  ,\n    \"description\": \"Revert applied migrations to reach a specific target version.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"downgrade\",\n  \
  \      \"item\": \"https://dbwarden.emiliano-go.com/commands/downgrade\"\n     \
  \ }\n    ]\n  }\n]\n</script>\n"
---

# `downgrade`

Revert applied migrations to reach a specific target version.

## Usage

```bash
$ dbwarden downgrade --to 0005 --database primary
```

## Options

- `--to`, `-t` (required) - Target version to downgrade to
- `--database`, `-d`
- `--verbose`, `-v`

## Notes

- reads `-- rollback` sections from migration files and applies them in reverse order
- only reverts versions after the target version; versions at or before the target are preserved
- same lock discipline as `migrate` and `rollback`
- fails if the target version has not been applied

See also: [rollback](rollback.md)
