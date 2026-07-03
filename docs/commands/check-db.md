---
seo:
  title: check-db - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/check-db
  robots: index,follow
  og:
    type: website
    title: check-db - DBWarden Documentation
    description: Inspect live database schema.
    url: https://dbwarden.emiliano-go.com/commands/check-db
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: check-db - DBWarden Documentation
    description: Inspect live database schema.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Inspect live database schema.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: check-db - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/check-db
    description: Inspect live database schema.
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
      name: check-db
      item: https://dbwarden.emiliano-go.com/commands/check-db
seo_html: "<title>check-db - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Inspect live database schema.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/check-db\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"check-db - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Inspect live database schema.\">\n\
  <meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/check-db\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"check-db - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Inspect live database schema.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/icon.png\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"check-db - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/check-db\"\
  ,\n    \"description\": \"Inspect live database schema.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Commands\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/commands\"\n      },\n \
  \     {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"\
  name\": \"check-db\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/check-db\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# `check-db`

Inspect live database schema.

## Usage

```bash
$ dbwarden check-db --database primary
$ dbwarden check-db --database primary --out json
$ dbwarden check-db --database primary --out yaml
```

## Options

- `--database`, `-d`
- `--out`, `-o` (`txt`, `json`, `yaml`, `sql`)

## Notes

- useful for schema inspection and diagnostics
- complements `status` and `history`

See also: [Your First Migration](../getting-started/first-migration.md)
