---
description: Extensions extend DBWarden with FastAPI integration, sandbox testing,
  and pluggable runtime features for production use.
seo:
  title: Extensions - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/extensions
  robots: index,follow
  og:
    type: website
    title: Extensions - DBWarden Documentation
    description: Extensions extend DBWarden with FastAPI integration, sandbox testing,
      and pluggable runtime features for production use.
    url: https://dbwarden.emiliano-go.com/extensions
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Extensions - DBWarden Documentation
    description: Extensions extend DBWarden with FastAPI integration, sandbox testing,
      and pluggable runtime features for production use.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Extensions extend DBWarden with FastAPI integration, sandbox testing,
    and pluggable runtime features for production use.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Extensions - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/extensions
    description: Extensions extend DBWarden with FastAPI integration, sandbox testing,
      and pluggable runtime features for production use.
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
      name: Extensions
      item: https://dbwarden.emiliano-go.com/extensions
seo_html: "<title>Extensions - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Extensions extend DBWarden with FastAPI integration, sandbox testing,\
  \ and pluggable runtime features for production use.\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/extensions\">\n<meta name=\"robots\" content=\"\
  index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta property=\"\
  og:title\" content=\"Extensions - DBWarden Documentation\">\n<meta property=\"og:description\"\
  \ content=\"Extensions extend DBWarden with FastAPI integration, sandbox testing,\
  \ and pluggable runtime features for production use.\">\n<meta property=\"og:url\"\
  \ content=\"https://dbwarden.emiliano-go.com/extensions\">\n<meta property=\"og:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Extensions - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Extensions extend DBWarden with\
  \ FastAPI integration, sandbox testing, and pluggable runtime features for production\
  \ use.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Extensions - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/extensions\"\
  ,\n    \"description\": \"Extensions extend DBWarden with FastAPI integration, sandbox\
  \ testing, and pluggable runtime features for production use.\",\n    \"image\"\
  : \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  ,\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Extensions\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/extensions\"\n      }\n    ]\n  }\n]\n</script>\n"
---

# Extensions

DBWarden ships with a set of optional extensions that integrate with common Python frameworks and workflows. Each extension is installed via an optional dependency group.

## Available Extensions

| Extension | Install | Purpose |
|-----------|---------|---------|
| [FastAPI](../fastapi/index.md) | `uv add "dbwarden[fastapi]"` | Async database sessions, health endpoints, migration lifecycle hooks |
| [Sandbox](sandbox.md) | built-in | Temporary database validation and config file security isolation |

## FastAPI Integration

First-class FastAPI integration for database sessions, health checks, and migration management. One configuration source for both migrations and runtime, with no more split configs.

See the [FastAPI Integration](../fastapi/index.md) guide for setup, tutorials, and reference.

## Sandbox

Two sandbox mechanisms protect your production data:

- **Migration sandbox** (`--sandbox` flag): applies pending migrations to a temporary database and reports results without modifying the real target.
- **Config security sandbox**: restricts imports when loading isolated config files, preventing path traversal and accidental code execution.

See the [Sandbox](sandbox.md) guide for usage, CI patterns, and configuration.
