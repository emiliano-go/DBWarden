---
seo:
  title: check - DBWarden Documentation
  description: Analyze schema differences between your SQLAlchemy models and the live
    database.
  canonical: https://dbwarden.emiliano-go.com/commands/check/
  robots: index,follow
  og:
    type: website
    title: check - DBWarden Documentation
    description: Analyze schema differences between your SQLAlchemy models and the
      live database.
    url: https://dbwarden.emiliano-go.com/commands/check/
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: check - DBWarden Documentation
    description: Analyze schema differences between your SQLAlchemy models and the
      live database.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: check - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/commands/check/
    description: Analyze schema differences between your SQLAlchemy models and the
      live database.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Commands
      item: https://emiliano-go.github.io/DBWarden/commands/
    - '@type': ListItem
      position: 2
      name: check
      item: https://emiliano-go.github.io/DBWarden/commands/check/
    - '@type': ListItem
      position: 3
      name: check
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
