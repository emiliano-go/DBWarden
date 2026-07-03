---
seo:
  title: history - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/history
  robots: index,follow
  og:
    type: website
    title: history - DBWarden Documentation
    description: Show migration execution history.
    url: https://dbwarden.emiliano-go.com/commands/history
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: history - DBWarden Documentation
    description: Show migration execution history.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Show migration execution history.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: history - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/history
    description: Show migration execution history.
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
      name: history
      item: https://dbwarden.emiliano-go.com/commands/history
seo_html: "<title>history - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Show migration execution history.\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/commands/history\">\n<meta name=\"robots\" content=\"\
  index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta property=\"\
  og:title\" content=\"history - DBWarden Documentation\">\n<meta property=\"og:description\"\
  \ content=\"Show migration execution history.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/commands/history\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n<meta property=\"\
  og:image:width\" content=\"128\">\n<meta property=\"og:image:height\" content=\"\
  128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta\
  \ name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"history - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Show migration execution history.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/icon.png\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"history - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/history\"\
  ,\n    \"description\": \"Show migration execution history.\",\n    \"image\": \"\
  https://dbwarden.emiliano-go.com/assets/icon.png\",\n    \"publisher\": {\n    \
  \  \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\n \
  \   }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"BreadcrumbList\"\
  ,\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\",\n     \
  \   \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands\"\
  \n      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n\
  \        \"name\": \"history\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/history\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# `history`

Show migration execution history.

## Usage

```bash
$ dbwarden history --database primary
```

## Options

- `--database`, `-d`

## Notes

- shows applied migrations, order, and timestamps
- useful for audit and incident analysis

See also: [Your First Migration](../getting-started/first-migration.md)
