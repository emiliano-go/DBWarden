---
seo:
  title: seed - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/commands/seed
  robots: index,follow
  og:
    type: website
    title: seed - DBWarden Documentation
    description: Manage seed data for a database.
    url: https://dbwarden.emiliano-go.com/commands/seed
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: seed - DBWarden Documentation
    description: Manage seed data for a database.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Manage seed data for a database.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: seed - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/seed
    description: Manage seed data for a database.
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
      name: seed
      item: https://dbwarden.emiliano-go.com/commands/seed
seo_html: "<title>seed - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Manage seed data for a database.\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/commands/seed\">\n<meta name=\"robots\" content=\"\
  index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta property=\"\
  og:title\" content=\"seed - DBWarden Documentation\">\n<meta property=\"og:description\"\
  \ content=\"Manage seed data for a database.\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/commands/seed\">\n<meta property=\"og:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta property=\"\
  og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\" content=\"\
  768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\">\n<meta\
  \ property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"seed - DBWarden Documentation\">\n<meta\
  \ name=\"twitter:description\" content=\"Manage seed data for a database.\">\n<meta\
  \ name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"seed - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/commands/seed\"\
  ,\n    \"description\": \"Manage seed data for a database.\",\n    \"image\": \"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  ,\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Commands\",\n        \"item\":\
  \ \"https://dbwarden.emiliano-go.com/commands\"\n      },\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 2,\n        \"name\": \"seed\",\n       \
  \ \"item\": \"https://dbwarden.emiliano-go.com/commands/seed\"\n      }\n    ]\n\
  \  }\n]\n</script>\n"
---

# `seed`

Manage seed data for a database.

## Subcommands

- `seed create`: create a new file seed (legacy)
- `seed apply`: apply pending seeds (file + code seeds)
- `seed list`: list seeds and their status
- `seed rollback`: roll back applied seeds
- `seed export`: export code seeds to ROC SQL files for stateless production application

---

## `seed create`

Create a new file-based seed file (SQL or Python). For new projects, prefer [code seeds](../seeds.md#code-seeds-recommended) instead.

### Usage

```bash
$ dbwarden seed create "seed initial data" --database primary
$ dbwarden seed create "populate lookup tables" --database primary --type python
```

### Options

- `--database`, `-d`: target database handle
- `--type`: `sql` (default) or `python`
- `--verbose`, `-v`

---

## `seed apply`

Apply pending seeds. Both file seeds and [code seeds](../seeds.md#code-seeds-recommended) are discovered and applied.

### Usage

```bash
$ dbwarden seed apply --database primary
$ dbwarden seed apply --database primary --version 0003
$ dbwarden seed apply --database primary --dry-run
$ dbwarden seed apply --all
```

### Options

- `--database`, `-d`
- `--all`, `-a`: apply across all configured databases
- `--version`: apply up to this seed version
- `--dry-run`: preview without executing
- `--verbose`, `-v`

---

## `seed list`

List seeds and their applied status. Includes both file seeds and code seeds.

### Usage

```bash
$ dbwarden seed list --database primary
$ dbwarden seed list --all
$ dbwarden seed list --prune              # clean up orphaned tracking records
```

### Options

- `--database`, `-d`
- `--all`, `-a`
- `--prune`: remove tracking records for seed files that no longer exist on disk
- `--verbose`, `-v`

---

## `seed rollback`

Roll back applied seeds. Removes the tracking record, allowing the seed to be re-applied. Does **not** reverse data changes.

### Usage

```bash
$ dbwarden seed rollback --database primary
$ dbwarden seed rollback --database primary --count 2
$ dbwarden seed rollback --database primary --to-version 0003
```

### Options

- `--database`, `-d`
- `--all`, `-a`: rollback on all databases
- `--count`, `-c`: number of seeds to roll back (default: 1)
- `--to-version`, `-t`: roll back to this seed version
- `--verbose`, `-v`

See also: [Seed Management](../seeds.md)

---

## `seed export`

Export code seeds to ROC (runs-on-change) SQL files for stateless application. The generated file contains `INSERT ... ON CONFLICT` statements rendered in the target database dialect. ROC files are re-applied when their content checksum changes.

### Usage

```bash
$ dbwarden seed export --database primary
$ dbwarden seed export --all
$ dbwarden seed export --database clickhouse --output-dir ./seeds
```

### Options

- `--database`, `-d`: target database handle
- `--all`, `-a`: export seeds for all configured databases
- `--output-dir`, `-o`: output directory (default: `seeds/`)

### Behavior

- **Row-based seeds** (`rows = [...]`): each row is rendered as an `INSERT` statement with `ON CONFLICT` matching the seed's `__seed_on_conflict__`
- **Logic-based seeds** (`generate(session)`): executed in a temporary SQLite database with FK-closure tables created and preceding row-based seeds pre-loaded. The resulting rows are exported as INSERT statements
- Seeds are ordered by FK dependency (topological sort) so foreign-key-safe insert order is preserved

### Dialect requirement

Exporting requires the same dialect packages as connecting to that database. For ClickHouse, install `clickhouse-sqlalchemy`. Missing packages produce a clear error at export time.

### Non-handled problems

- Removed rows are not deleted (no purge on re-export)
- Logic seeds that depend on other logic seeds' output are unsupported
- Non-deterministic `generate()` methods produce a new checksum every export
