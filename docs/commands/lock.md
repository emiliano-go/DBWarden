---
seo:
  title: lock-status and unlock - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/lock
  robots: index,follow
  og:
    type: website
    title: lock-status and unlock - DBWarden Documentation
    description: Inspect and recover migration lock state.
    url: https://dbwarden.emiliano-go.com/commands/lock
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: lock-status and unlock - DBWarden Documentation
    description: Inspect and recover migration lock state.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Inspect and recover migration lock state.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: lock-status and unlock - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/lock
    description: Inspect and recover migration lock state.
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
      name: lock-status/unlock
      item: https://dbwarden.emiliano-go.com/commands/lock
seo_html: "<title>lock-status and unlock - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Inspect and recover migration lock state.\">\n<link rel=\"\
  canonical\" href=\"https://dbwarden.emiliano-go.com/commands/lock\">\n<meta name=\"\
  robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\"\
  >\n<meta property=\"og:title\" content=\"lock-status and unlock - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Inspect and recover migration lock\
  \ state.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/lock\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"lock-status and unlock - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Inspect and recover migration lock\
  \ state.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"lock-status and unlock - DBWarden Documentation\",\n    \"url\"\
  : \"https://dbwarden.emiliano-go.com/commands/lock\",\n    \"description\": \"Inspect\
  \ and recover migration lock state.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"lock-status/unlock\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/lock\"\n      }\n\
  \    ]\n  }\n]\n</script>\n"
---

# `lock-status` and `unlock`

Inspect and recover migration lock state.

## Usage

```bash
$ dbwarden lock-status --database primary
$ dbwarden unlock --database primary
```

## Options

- `--database`, `-d`

## Notes

- use `lock-status` to inspect lock state
- use `unlock` only when lock is stale and no migration is running

See also: [Migration Locking](../advanced/migration-locking.md)
