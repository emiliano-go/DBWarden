---
seo:
  title: 6. Safety & Impact Analysis - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/cookbook/06-safety-impact
  robots: index,follow
  og:
    type: website
    title: 6. Safety & Impact Analysis - DBWarden Documentation
    description: Schema changes are the highest-risk operation in most deployments.
      Dropping a column that application code still references causes runtime errors.
      Changing a...
    url: https://dbwarden.emiliano-go.com/cookbook/06-safety-impact
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: 6. Safety & Impact Analysis - DBWarden Documentation
    description: Schema changes are the highest-risk operation in most deployments.
      Dropping a column that application code still references causes runtime errors.
      Changing a...
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Schema changes are the highest-risk operation in most deployments.
    Dropping a column that application code still references causes runtime errors.
    Changing a...
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: 6. Safety & Impact Analysis - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/cookbook/06-safety-impact
    description: Schema changes are the highest-risk operation in most deployments.
      Dropping a column that application code still references causes runtime errors.
      Changing a...
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
      name: Cookbook & Examples
      item: https://dbwarden.emiliano-go.com/cookbook
    - '@type': ListItem
      position: 2
      name: 06 Safety Impact
      item: https://dbwarden.emiliano-go.com/cookbook/06-safety-impact
seo_html: "<title>6. Safety &amp; Impact Analysis - DBWarden Documentation</title>\n\
  <meta name=\"description\" content=\"Schema changes are the highest-risk operation\
  \ in most deployments. Dropping a column that application code still references\
  \ causes runtime errors. Changing a...\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/cookbook/06-safety-impact\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"6. Safety &amp; Impact Analysis\
  \ - DBWarden Documentation\">\n<meta property=\"og:description\" content=\"Schema\
  \ changes are the highest-risk operation in most deployments. Dropping a column\
  \ that application code still references causes runtime errors. Changing a...\"\
  >\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/cookbook/06-safety-impact\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"6. Safety &amp; Impact Analysis - DBWarden\
  \ Documentation\">\n<meta name=\"twitter:description\" content=\"Schema changes\
  \ are the highest-risk operation in most deployments. Dropping a column that application\
  \ code still references causes runtime errors. Changing a...\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"6. Safety & Impact Analysis - DBWarden Documentation\",\n   \
  \ \"url\": \"https://dbwarden.emiliano-go.com/cookbook/06-safety-impact\",\n   \
  \ \"description\": \"Schema changes are the highest-risk operation in most deployments.\
  \ Dropping a column that application code still references causes runtime errors.\
  \ Changing a...\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Cookbook & Examples\",\n      \
  \  \"item\": \"https://dbwarden.emiliano-go.com/cookbook\"\n      },\n      {\n\
  \        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"\
  06 Safety Impact\",\n        \"item\": \"https://dbwarden.emiliano-go.com/cookbook/06-safety-impact\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# 6. Safety & Impact Analysis

Schema changes are the highest-risk operation in most deployments. Dropping a column that application code still references causes runtime errors. Changing a column type can break queries. DBWarden provides two tools to detect these issues before deploy: `check` classifies every migration operation by danger level, and `check-impact` finds affected code references.

For complete documentation see the [`check`](../commands/check.md) and [`check-impact`](../cli-reference.md) command references.

## What You'll Learn

- How `dbwarden check` classifies operations by danger level
- How `dbwarden check-impact` finds code references affected by a migration
- How to detect destructive changes before they reach production

## Prerequisites

- Completed [Section 3](03-apply-and-inspect.md) (migrations applied)
- `examples/core/` project

## Step 1: Safety Check

```bash
cd examples/core
bash scripts/06-safety-impact.sh
```

The key command:

```bash
$ dbwarden check --database primary
```

This scans every migration file and classifies each SQL operation by safety level:

| Level | Meaning |
|-------|---------|
| **SAFE** | No data loss risk (add table, add nullable column, create index) |
| **INFO** | Metadata changes (comments, renames) |
| **WARN** | Potential impact (change column type, drop default) |
| **CRITICAL** | Destructive (drop table, drop column, remove NOT NULL) |

Output for our baseline migrations:

```
Safety Check - primary
┌──────────┬──────────────┬──────────┬────────┬─────────┬───────────────┐
│ Severity │ Change       │ Table    │ Column │ Message │ Required Flag │
├──────────┼──────────────┼──────────┼────────┼─────────┼───────────────┤
│ SAFE     │ create_table │ users    │        │         │               │
│ SAFE     │ create_table │ posts    │        │         │               │
│ SAFE     │ create_table │ products │        │         │               │
│ SAFE     │ create_table │ tags     │        │         │               │
│ SAFE     │ create_index │          │        │         │               │
│ INFO     │ comment_on   │ users    │        │         │               │
└──────────┴──────────────┴──────────┴────────┴─────────┴───────────────┘
```

A migration with a destructive change would show:

```
┌──────────┬──────────────┬───────┬──────────┬─────────┬───────────────┐
│ Severity │ Change       │ Table │ Column   │ Message │ Required Flag │
├──────────┼──────────────┼───────┼──────────┼─────────┼───────────────┤
│ CRITICAL │ drop_column  │ users │ username │         │               │
└──────────┴──────────────┴───────┴──────────┴─────────┴───────────────┘
```

This gives you a quick visual signal during code review: if a migration contains CRITICAL operations, it needs extra scrutiny.

## Step 2: Code Impact Analysis

```bash
$ dbwarden check-impact 0001 --database primary
```

`check-impact` scans your application code (not just migration files) for references that would be affected by a migration. It uses AST analysis with a grep fallback:

```
No impact detected
Scanned: .
```

A more realistic scenario with a destructive change:

```
Migration: 0002_drop_username
Impact detected: 1 operation(s) affect code

drop_column on users.username
  References: 2
    app/routes/users.py:34  attribute_access
      .username
    app/templates/profile.jinja2:12  grep
      user.username
```

The scan finds each reference, identifies the access pattern (attribute access in Python, grep match in templates), and reports the file and line number.

### How It Works

1. Reads the migration's plan file and parses the schema changes
2. Identifies schema changes (DROP COLUMN, ALTER COLUMN TYPE, etc.)
3. Scans `.py` files using Python's `ast` module for attribute access patterns
4. Falls back to grep for non-Python files (templates, configs, etc.)
5. Reports all references grouped by change type

### Flags

- `--scan-path app/`: limit scanning to a specific directory (default: project root)
- `--deep`: also scan dependencies (imported packages)
- `--out json`: output as JSON for CI processing
- `--verbose`: show scan progress

## Pre-Deploy Workflow

Combine both tools for a safe deploy sequence:

```bash
# 1. Check migration safety
$ dbwarden check --database primary

# 2. Check code impact
$ dbwarden check-impact 0042 --database primary

# 3. Only proceed if no unexpected CRITICAL or WARN items
$ dbwarden migrate --database primary
```

In CI:

```yaml
- name: Safety check
  run: dbwarden check --database primary
- name: Impact analysis
  run: dbwarden check-impact 0042 --database primary
- name: Apply (only if previous steps succeeded)
  run: dbwarden migrate --database primary
```

## Key Takeaways

- `check` classifies every migration operation by safety level using a severity table
- `check-impact` finds code references affected by a migration using AST + grep
- Together they catch breaking changes before deploy
- CRITICAL operations aren't blocked; they're flagged for human review
- Use `--out json` for CI integration

## Related Documentation

- [`check` command](../commands/check.md)
- [`check-impact` command](../cli-reference.md) (see CLI reference)
- [Safe Deployment](../advanced/safe-deployment.md)

## Next

[Section 7: Seeds](07-seeds.md)
