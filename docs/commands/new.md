---
seo:
  title: new - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/new
  robots: index,follow
  og:
    type: website
    title: new - DBWarden Documentation
    description: Create a manual migration file.
    url: https://dbwarden.emiliano-go.com/commands/new
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: new - DBWarden Documentation
    description: Create a manual migration file.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Create a manual migration file.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: new - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/new
    description: Create a manual migration file.
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
      name: new
      item: https://dbwarden.emiliano-go.com/commands/new
seo_html: "<title>new - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Create a manual migration file.\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/commands/new\">\n<meta name=\"robots\" content=\"\
  index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta property=\"\
  og:title\" content=\"new - DBWarden Documentation\">\n<meta property=\"og:description\"\
  \ content=\"Create a manual migration file.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/commands/new\">\n<meta property=\"og:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/icon.png\">\n<meta property=\"og:image:width\"\
  \ content=\"128\">\n<meta property=\"og:image:height\" content=\"128\">\n<meta property=\"\
  og:site_name\" content=\"DBWarden Documentation\">\n<meta name=\"twitter:card\"\
  \ content=\"summary_large_image\">\n<meta name=\"twitter:title\" content=\"new -\
  \ DBWarden Documentation\">\n<meta name=\"twitter:description\" content=\"Create\
  \ a manual migration file.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"new - DBWarden Documentation\",\n\
  \    \"url\": \"https://dbwarden.emiliano-go.com/commands/new\",\n    \"description\"\
  : \"Create a manual migration file.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Commands\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/commands\"\n      },\n \
  \     {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"\
  name\": \"new\",\n        \"item\": \"https://dbwarden.emiliano-go.com/commands/new\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# `new`

Create a manual migration file.

## Usage

```bash
$ dbwarden new "manual hotfix" --database primary
$ dbwarden new "backfill users" --database primary --version 0042
$ dbwarden new "seed data" --database primary --type ra
$ dbwarden new "update view" --database primary --type roc
```

## Options

- positional `description`
- `--database`, `-d`
- `--version`
- `--type`, `-t`: Migration type: `versioned` (default), `ra` / `runs_always`, or `roc` / `runs_on_change`

## Notes

- use when change is not model-driven
- file is scaffolded with `-- upgrade` and `-- rollback` sections

See also: [Your First Migration](../getting-started/first-migration.md)
