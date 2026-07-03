---
seo:
  title: 4. Offline & CI Workflows - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/cookbook/04-offline-ci
  robots: index,follow
  og:
    type: website
    title: 4. Offline & CI Workflows - DBWarden Documentation
    description: What You'll Learn
    url: https://dbwarden.emiliano-go.com/cookbook/04-offline-ci
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: 4. Offline & CI Workflows - DBWarden Documentation
    description: What You'll Learn
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: What You'll Learn
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: 4. Offline & CI Workflows - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/cookbook/04-offline-ci
    description: What You'll Learn
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Cookbook & Examples
      item: https://dbwarden.emiliano-go.com/cookbook
    - '@type': ListItem
      position: 2
      name: 04 Offline Ci
      item: https://dbwarden.emiliano-go.com/cookbook/04-offline-ci
seo_html: "<title>4. Offline &amp; CI Workflows - DBWarden Documentation</title>\n\
  <meta name=\"description\" content=\"What You&#x27;ll Learn\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/cookbook/04-offline-ci\">\n<meta name=\"\
  robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\"\
  >\n<meta property=\"og:title\" content=\"4. Offline &amp; CI Workflows - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"What You&#x27;ll\
  \ Learn\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/cookbook/04-offline-ci\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"4. Offline &amp; CI Workflows - DBWarden Documentation\">\n<meta name=\"\
  twitter:description\" content=\"What You&#x27;ll Learn\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/icon.png\">\n<script type=\"\
  application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"\
  @type\": \"WebPage\",\n    \"name\": \"4. Offline & CI Workflows - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/cookbook/04-offline-ci\",\n \
  \   \"description\": \"What You'll Learn\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n   \
  \     \"@type\": \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Cookbook\
  \ & Examples\",\n        \"item\": \"https://dbwarden.emiliano-go.com/cookbook\"\
  \n      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 2,\n\
  \        \"name\": \"04 Offline Ci\",\n        \"item\": \"https://dbwarden.emiliano-go.com/cookbook/04-offline-ci\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# 4. Offline & CI Workflows

## What You'll Learn

- How to export model state to JSON for offline use
- How to generate migrations without a live database
- How to integrate this into CI/CD pipelines

## Prerequisites

- Completed [Section 3](03-apply-and-inspect.md) (migrations applied, models in sync)
- `examples/core/` project

## The Problem

In CI/CD pipelines, you often need to generate migrations as part of your build, but your CI runner may not have a database connection. DBWarden's offline mode solves this by serializing model state to a JSON file.

## Step 1: Export Model State

```bash
cd examples/core
bash scripts/04-offline-ci.sh
```

The key command:

```bash
$ dbwarden export-models --database primary
```

This connects to the live database, introspects the current schema, and writes a JSON file to `.dbwarden/model_state.json`:

```json
{
  "version": "1.0",
  "exported_at": "2025-01-15T10:30:00",
  "database": "primary",
  "tables": {
    "users": {
      "columns": {
        "id": {"type": "INTEGER", "nullable": false, "primary_key": true},
        "email": {"type": "VARCHAR(255)", "nullable": false, "unique": true},
        "username": {"type": "VARCHAR(100)", "nullable": false, "unique": true},
        "full_name": {"type": "VARCHAR(200)", "nullable": true},
        "is_active": {"type": "BOOLEAN", "nullable": true, "default": "1"},
        "created_at": {"type": "DATETIME", "nullable": true, "default": "CURRENT_TIMESTAMP"}
      },
      "indexes": [
        {"name": "ix_users_created_at", "columns": ["created_at"]}
      ],
      "checks": [],
      "comment": "Core user accounts"
    }
  }
}
```

This file becomes your source of truth for future diffs; no database required.

## Step 2: Commit the State File

```bash
git add .dbwarden/model_state.json
git commit -m "Update model state snapshot"
```

## Step 3: Generate Migrations Offline

On any machine (including CI without a database):

```bash
$ dbwarden make-migrations "offline schema change" --offline --database primary
```

The `--offline` flag tells DBWarden to:

1. Read the model state from `.dbwarden/model_state.json` instead of querying a live database
2. Introspect the current model definitions in your Python code
3. Diff the two and generate migration SQL
4. Write the migration file AND update the snapshot file

This means the snapshot is always in sync after each generation.

## CI/CD Integration

In a GitHub Actions workflow:

```yaml
jobs:
  generate-migrations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: uv add dbwarden sqlalchemy

      # Generate migrations using the committed state file
      - name: Check for new migrations
        run: dbwarden make-migrations "ci change" --offline --database primary

      # Commit any newly generated migrations
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Auto-generate migration"
```

The full CI pipeline can then `dbwarden migrate` against staging/production using the generated SQL files.

## Key Takeaways

- `export-models` serializes the current database schema to JSON
- `make-migrations --offline` generates migrations using the snapshot instead of a live database
- Offline mode enables migration generation in CI without database access
- The snapshot file should be committed and kept in sync

## Related Documentation

- [CI/CD Patterns](../advanced/ci-cd-patterns.md)
- [`export-models` command](../cli-reference.md) (see CLI reference)

## Next

[Section 5: Schema Inspection](05-schema-inspection.md)
