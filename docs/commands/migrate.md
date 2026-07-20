---
seo:
  title: migrate - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/migrate
  robots: index,follow
  og:
    type: website
    title: migrate - DBWarden Documentation
    description: Apply pending migrations.
    url: https://dbwarden.emiliano-go.com/commands/migrate
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: migrate - DBWarden Documentation
    description: Apply pending migrations.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Apply pending migrations.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: migrate - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/migrate
    description: Apply pending migrations.
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
      name: migrate
      item: https://dbwarden.emiliano-go.com/commands/migrate
seo_html: "<title>migrate - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Apply pending migrations.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/commands/migrate\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"migrate - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Apply pending migrations.\">\n<meta\
  \ property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/commands/migrate\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"migrate - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Apply pending migrations.\">\n<meta\
  \ name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"migrate - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/migrate\"\
  ,\n    \"description\": \"Apply pending migrations.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"migrate\",\n    \
  \    \"item\": \"https://dbwarden.emiliano-go.com/commands/migrate\"\n      }\n\
  \    ]\n  }\n]\n</script>\n"
---

# `migrate`

Apply pending migrations.

## Usage

```bash
$ dbwarden migrate --database primary
$ dbwarden migrate --all
$ dbwarden migrate --database primary --to-version 0010
$ dbwarden migrate --database primary --count 2
$ dbwarden migrate --database primary --with-backup --backup-dir ./backups
$ dbwarden migrate --database primary --baseline --to-version 0005
```

## Options

- `--database`, `-d`
- `--all`, `-a`
- `--count`, `-c`
- `--to-version`, `-t`
- `--baseline`
- `--with-backup`, `-b`
- `--backup-dir`
- `--dry-run`: preview changes without applying
- `--sandbox`: apply in a temporary sandbox database
- `--apply-seeds`: apply pending seeds after migrations
- `--verbose`, `-v`

## Notes

- creates metadata/lock tables if needed
- executes versioned + repeatable migrations
- uses lock protection to prevent concurrent migration mutation

See also: [Your First Migration](../getting-started/first-migration.md)
