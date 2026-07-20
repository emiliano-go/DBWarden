---
description: Organize larger DBWarden workflows, including multi-database projects,
  CI patterns, sandbox validation, and command conventions across environments.
seo:
  title: Workflows - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/getting-started/workflows
  robots: index,follow
  og:
    type: website
    title: Workflows - DBWarden Documentation
    description: Organize larger DBWarden workflows, including multi-database projects,
      CI patterns, sandbox validation, and command conventions across environments.
    url: https://dbwarden.emiliano-go.com/getting-started/workflows
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Workflows - DBWarden Documentation
    description: Organize larger DBWarden workflows, including multi-database projects,
      CI patterns, sandbox validation, and command conventions across environments.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Organize larger DBWarden workflows, including multi-database projects,
    CI patterns, sandbox validation, and command conventions across environments.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Workflows - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/getting-started/workflows
    description: Organize larger DBWarden workflows, including multi-database projects,
      CI patterns, sandbox validation, and command conventions across environments.
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
      name: Get Started
      item: https://dbwarden.emiliano-go.com/getting-started
    - '@type': ListItem
      position: 2
      name: Workflows
      item: https://dbwarden.emiliano-go.com/getting-started/workflows
seo_html: "<title>Workflows - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Organize larger DBWarden workflows, including multi-database projects,\
  \ CI patterns, sandbox validation, and command conventions across environments.\"\
  >\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/getting-started/workflows\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Workflows - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Organize larger DBWarden workflows,\
  \ including multi-database projects, CI patterns, sandbox validation, and command\
  \ conventions across environments.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/getting-started/workflows\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Workflows - DBWarden Documentation\">\n\
  <meta name=\"twitter:description\" content=\"Organize larger DBWarden workflows,\
  \ including multi-database projects, CI patterns, sandbox validation, and command\
  \ conventions across environments.\">\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Workflows - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/getting-started/workflows\"\
  ,\n    \"description\": \"Organize larger DBWarden workflows, including multi-database\
  \ projects, CI patterns, sandbox validation, and command conventions across environments.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Get Started\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/getting-started\"\n      },\n      {\n    \
  \    \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"Workflows\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/getting-started/workflows\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Workflows

This guide covers larger day-to-day workflows once the basics are in place.

## Multi-Database Projects

DBWarden can manage more than one database from one config source.

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app.models"],
    model_tables=["users", "posts", "comments"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="clickhouse://default:@localhost:8123/analytics",
    model_paths=["app.analytics_models"],
    model_tables=["events", "page_views"],
)
```

Apply migrations per database:

```bash
$ dbwarden migrate --database primary
$ dbwarden migrate --database analytics
```

Show status across all configured databases:

```bash
$ dbwarden status --all
```

## Separate Model Sets

Each database should usually own a distinct model set through `model_paths`. When databases share the same models package, use `model_tables` to split ownership by table name. DBWarden validates overlapping paths unless `overlap_models=True` is set explicitly.

This prevents one model tree from being interpreted as belonging to multiple databases by accident.

## CI Workflows

A common CI pattern is:

```bash
$ dbwarden export-models --database primary
$ dbwarden make-migrations "ci validation" --offline --database primary
$ dbwarden check --database primary
```

This keeps schema generation deterministic and avoids depending on a live database in every pipeline step.

For a full example, see [Cookbook: Offline & CI](../cookbook/04-offline-ci.md).

## Sandbox Validation

Before applying migrations to a real environment, you can validate them in a temporary sandbox database.

```bash
$ dbwarden migrate --sandbox --database primary
```

This is especially useful for complex migrations, risky type changes, and CI gates.

See the [Architecture Deep Dive](../architecture-deep-dive.md) for a thorough explanation of sandbox validation.

## Baselines and Partial Applies

When integrating DBWarden into an existing environment, or when applying only part of a migration sequence, these patterns are common:

- `--baseline` marks the target migration as already applied without actually running it, useful for onboarding an existing database.
- `--partial` (via `--count` or `--to-version`) applies a subset of pending migrations instead of all of them.

```bash
$ dbwarden migrate --database primary --baseline --to-version 0005
$ dbwarden migrate --database primary --count 2
$ dbwarden rollback --database primary --to-version 0007
```

See the [CLI Reference](../cli-reference.md) for a full breakdown of these flags. Use these modes carefully. They are operational tools, not everyday authoring commands.

## Operational Command Pattern

A typical production-safe pattern is:

```bash
$ dbwarden check --database primary
$ dbwarden make-migrations "release change" --database primary
$ dbwarden migrate --database primary
$ dbwarden status --database primary
$ dbwarden history --database primary
```

This keeps planning, execution, and verification as separate visible steps.

## Rollback Command Pattern

When validating rollback quality, use a loop like this:

```bash
$ dbwarden migrate --database primary
$ dbwarden rollback --count 1 --database primary
$ dbwarden migrate --database primary
```

This verifies both directions of the migration before a release depends on them.

## Where to Go Next

- Use [Cookbook Overview](../cookbook/index.md) for full working flows
- Use [Configuration](../configuration/index.md) for deeper config behavior
- Use [CLI Reference](../cli-reference.md) for command details
